#!/usr/bin/env node
/**
 * Stigmem MCP Server — exposes Stigmem as MCP tools.
 *
 * Tools:
 *   assert_fact          — write a typed fact to the stigmem node
 *   query_facts          — query facts by entity / relation / scope
 *   resolve_contradiction — resolve a detected conflict between two facts
 *   subscribe_scope      — poll for recent facts in a scope (one shot, not streaming)
 *
 * Configuration via environment variables:
 *   STIGMEM_URL          — required; e.g. http://localhost:8765
 *   STIGMEM_API_KEY      — optional; API key if node requires auth
 *   STIGMEM_POLL_LIMIT   — facts per subscribe_scope call (default: 50)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import { StigmemClient, StigmemError } from "stigmem-ts";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const STIGMEM_URL = process.env["STIGMEM_URL"];
if (!STIGMEM_URL) {
  console.error("STIGMEM_URL is required");
  process.exit(1);
}

const client = new StigmemClient({
  url: STIGMEM_URL,
  apiKey: process.env["STIGMEM_API_KEY"],
});

const POLL_LIMIT = Number(process.env["STIGMEM_POLL_LIMIT"] ?? "50");

// ---------------------------------------------------------------------------
// Tool input schemas (Zod, serialised to JSON Schema for MCP)
// ---------------------------------------------------------------------------

const FactValueSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("string"),   v: z.string() }),
  z.object({ type: z.literal("text"),     v: z.string() }),
  z.object({ type: z.literal("number"),   v: z.number() }),
  z.object({ type: z.literal("boolean"),  v: z.boolean() }),
  z.object({ type: z.literal("datetime"), v: z.string() }),
  z.object({ type: z.literal("ref"),      v: z.string() }),
  z.object({ type: z.literal("null") }),
]);

const FactScopeSchema = z.enum(["local", "team", "company", "public"]);

const AssertFactSchema = z.object({
  entity:      z.string().describe("Entity URI or opaque ID, e.g. 'user:alice'"),
  relation:    z.string().describe("Namespaced predicate, e.g. 'memory:role'"),
  value:       FactValueSchema.describe("Typed fact value"),
  source:      z.string().describe("Asserting agent/user URI, e.g. 'agent:cto'"),
  confidence:  z.number().min(0).max(1).default(1.0).describe("Confidence in [0.0, 1.0]"),
  scope:       FactScopeSchema.default("company").describe("Visibility scope"),
  valid_until: z.string().optional().describe("ISO 8601 expiry; null = never expires"),
});

const QueryFactsSchema = z.object({
  entity:               z.string().optional().describe("Filter by entity URI"),
  relation:             z.string().optional().describe("Filter by relation"),
  source:               z.string().optional().describe("Filter by source agent"),
  scope:                FactScopeSchema.optional().describe("Filter by scope"),
  min_confidence:       z.number().min(0).max(1).optional().describe("Minimum confidence threshold"),
  include_contradicted: z.boolean().default(false).describe("Include contradicted facts"),
  include_expired:      z.boolean().default(false).describe("Include expired facts"),
  limit:                z.number().int().min(1).max(500).default(50),
  cursor:               z.string().optional().describe("Pagination cursor"),
});

const ResolveContradictionSchema = z.object({
  conflict_id:     z.string().describe("conflict_id from GET /v1/conflicts, e.g. 'stigmem:conflict:<uuid>'"),
  winning_fact_id: z.string().optional().describe("ID of the fact that should win; omit to assert a fresh value"),
  resolution_note: z.string().default("").describe("Human-readable rationale stored as a fact"),
  new_value:       FactValueSchema.optional().describe("Optional fresh reconciliation value to assert"),
});

const SubscribeScopeSchema = z.object({
  scope:  FactScopeSchema.describe("Scope to poll for new facts"),
  cursor: z.string().optional().describe("Cursor from previous call; null = from beginning"),
  limit:  z.number().int().min(1).max(500).default(POLL_LIMIT),
});

// ---------------------------------------------------------------------------
// MCP tool definitions
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: "assert_fact",
    description:
      "Write a typed fact to the Stigmem knowledge node. " +
      "Facts are immutable once written; to update, assert a new fact for the same (entity, relation, scope). " +
      "To retract, set confidence=0.0.",
    inputSchema: zodToJsonSchema(AssertFactSchema),
  },
  {
    name: "query_facts",
    description:
      "Query facts from the Stigmem node. " +
      "At least one of entity or relation should be provided for useful results. " +
      "Returns a page of matching facts with pagination cursor.",
    inputSchema: zodToJsonSchema(QueryFactsSchema),
  },
  {
    name: "resolve_contradiction",
    description:
      "Resolve a detected contradiction between two facts. " +
      "Specify winning_fact_id to prefer one of the two conflicting facts, " +
      "or new_value to assert a fresh reconciliation value. " +
      "Use query_facts with include_contradicted=true to find contradictions.",
    inputSchema: zodToJsonSchema(ResolveContradictionSchema),
  },
  {
    name: "subscribe_scope",
    description:
      "Poll for recent facts in a scope. " +
      "Returns up to `limit` facts and a cursor for the next call. " +
      "This is a single-shot poll — call repeatedly with the returned cursor to follow new facts.",
    inputSchema: zodToJsonSchema(SubscribeScopeSchema),
  },
] as const;

// ---------------------------------------------------------------------------
// Minimal Zod → JSON Schema (subset sufficient for our schemas)
// ---------------------------------------------------------------------------

function zodToJsonSchema(schema: z.ZodTypeAny): Record<string, unknown> {
  // We emit a minimal JSON Schema by introspecting the Zod shape.
  // A full zod-to-json-schema library is the right call in production;
  // this covers our needs without adding a dependency.
  return {
    type: "object",
    description: (schema as z.AnyZodObject).description,
    properties: buildProperties((schema as z.AnyZodObject).shape ?? {}),
    required: getRequired((schema as z.AnyZodObject).shape ?? {}),
  };
}

function buildProperties(shape: Record<string, z.ZodTypeAny>): Record<string, unknown> {
  const props: Record<string, unknown> = {};
  for (const [key, field] of Object.entries(shape)) {
    props[key] = zodFieldToSchema(field);
  }
  return props;
}

function zodFieldToSchema(field: z.ZodTypeAny): Record<string, unknown> {
  const def = field._def;
  const desc = (field as z.ZodString).description;
  const base: Record<string, unknown> = desc ? { description: desc } : {};

  if (field instanceof z.ZodString) return { ...base, type: "string" };
  if (field instanceof z.ZodNumber) return { ...base, type: "number" };
  if (field instanceof z.ZodBoolean) return { ...base, type: "boolean" };
  if (field instanceof z.ZodOptional) return { ...base, ...zodFieldToSchema(def.innerType as z.ZodTypeAny) };
  if (field instanceof z.ZodDefault) return { ...base, ...zodFieldToSchema(def.innerType as z.ZodTypeAny) };
  if (field instanceof z.ZodEnum) return { ...base, type: "string", enum: def.values };
  if (field instanceof z.ZodObject) return { ...base, type: "object", properties: buildProperties(field.shape as Record<string, z.ZodTypeAny>) };
  if (field instanceof z.ZodDiscriminatedUnion) {
    return {
      ...base,
      oneOf: [...(def.optionsMap as Map<string, z.ZodObject<z.ZodRawShape>>).values()].map(
        (opt) => ({ type: "object", properties: buildProperties(opt.shape) }),
      ),
    };
  }
  return { ...base, type: "string" };
}

function getRequired(shape: Record<string, z.ZodTypeAny>): string[] {
  return Object.entries(shape)
    .filter(([, v]) => !(v instanceof z.ZodOptional) && !(v instanceof z.ZodDefault))
    .map(([k]) => k);
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

const server = new Server(
  { name: "stigmem-mcp", version: "0.4.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [...TOOLS] }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "assert_fact": {
        const input = AssertFactSchema.parse(args);
        const fact = await client.assertFact(
          input.entity,
          input.relation,
          input.value,
          input.source,
          {
            confidence: input.confidence,
            scope: input.scope,
            valid_until: input.valid_until,
          },
        );
        return {
          content: [{ type: "text", text: JSON.stringify(fact, null, 2) }],
        };
      }

      case "query_facts": {
        const input = QueryFactsSchema.parse(args);
        const page = await client.query({
          entity:               input.entity,
          relation:             input.relation,
          source:               input.source,
          scope:                input.scope,
          min_confidence:       input.min_confidence,
          include_contradicted: input.include_contradicted,
          include_expired:      input.include_expired,
          limit:                input.limit,
          cursor:               input.cursor,
        });
        return {
          content: [{ type: "text", text: JSON.stringify(page, null, 2) }],
        };
      }

      case "resolve_contradiction": {
        const input = ResolveContradictionSchema.parse(args);
        const result = await client.resolveConflict(input.conflict_id, {
          winning_fact_id: input.winning_fact_id,
          resolution_note: input.resolution_note,
          new_value:       input.new_value,
        });
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "subscribe_scope": {
        const input = SubscribeScopeSchema.parse(args);
        const page = await client.query({
          scope:  input.scope,
          cursor: input.cursor,
          limit:  input.limit,
        });
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              facts:    page.facts,
              cursor:   page.cursor,
              has_more: (page.cursor !== null && page.cursor !== undefined),
            }, null, 2),
          }],
        };
      }

      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (err) {
    const msg = err instanceof StigmemError
      ? err.message
      : err instanceof Error
        ? err.message
        : String(err);
    return {
      content: [{ type: "text", text: `Error: ${msg}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
