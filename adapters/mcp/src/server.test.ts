import { describe, expect, it, vi } from "vitest";

import { StigmemAuthError } from "@eidetic-labs/stigmem-ts";

import { TOOLS, handleToolCall } from "./server.js";

describe("TOOLS", () => {
  it("exposes the expected MCP tool names", () => {
    expect(TOOLS.map((tool) => tool.name)).toEqual([
      "assert_fact",
      "query_facts",
      "resolve_contradiction",
      "subscribe_scope",
      "lint_scope",
    ]);
  });

  it("describes assert_fact with typed FactValue variants", () => {
    const assertTool = TOOLS.find((tool) => tool.name === "assert_fact");
    expect(assertTool).toBeDefined();
    const schema = assertTool!.inputSchema as {
      properties: { value: { oneOf: Array<{ properties: { type: { type: string } } }> } };
      required: string[];
    };
    expect(schema.required).toContain("entity");
    expect(schema.required).toContain("value");
    expect(schema.properties.value.oneOf).toHaveLength(7);
  });
});

describe("handleToolCall", () => {
  const client = {
    assertFact: vi.fn(),
    query: vi.fn(),
    resolveConflict: vi.fn(),
    lint: vi.fn(),
  };

  it("coerces JSON-string FactValue arguments for assert_fact", async () => {
    client.assertFact.mockResolvedValueOnce({ id: "fact-001" });

    const result = await handleToolCall(client, "assert_fact", {
      entity: "user:alice",
      relation: "memory:role",
      value: "{\"type\":\"string\",\"v\":\"CEO\"}",
      source: "agent:cto",
    });

    expect(client.assertFact).toHaveBeenCalledWith(
      "user:alice",
      "memory:role",
      { type: "string", v: "CEO" },
      "agent:cto",
      { confidence: 1, scope: "company", valid_until: undefined },
    );
    expect(JSON.parse(result.content[0].text)).toEqual({ id: "fact-001" });
  });

  it("maps subscribe_scope onto query pagination and emits has_more", async () => {
    client.query.mockResolvedValueOnce({
      facts: [{ id: "fact-001" }],
      cursor: "next-cursor",
      total: 1,
    });

    const result = await handleToolCall(client, "subscribe_scope", {
      scope: "company",
      cursor: "cursor-1",
      limit: 25,
    });

    expect(client.query).toHaveBeenCalledWith({
      scope: "company",
      cursor: "cursor-1",
      limit: 25,
    });
    expect(JSON.parse(result.content[0].text)).toEqual({
      facts: [{ id: "fact-001" }],
      cursor: "next-cursor",
      has_more: true,
    });
  });

  it("passes lint_scope filters through to the SDK client", async () => {
    client.lint.mockResolvedValueOnce({ findings: [], summary: { total: 0 } });

    const result = await handleToolCall(client, "lint_scope", {
      scope: "public",
      checks: ["broken_ref"],
      entity: "project:loom",
      relation: "references",
      stale_lookahead_s: 60,
    });

    expect(client.lint).toHaveBeenCalledWith("public", {
      checks: ["broken_ref"],
      entity: "project:loom",
      relation: "references",
      stale_lookahead_s: 60,
    });
    expect(JSON.parse(result.content[0].text)).toEqual({
      findings: [],
      summary: { total: 0 },
    });
  });

  it("returns MCP-friendly error text for SDK exceptions", async () => {
    client.query.mockRejectedValueOnce(new StigmemAuthError(401, "forbidden"));

    const result = await handleToolCall(client, "query_facts", { entity: "user:alice" });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Error: HTTP 401: forbidden");
  });

  it("returns an explicit error for unknown tools", async () => {
    const result = await handleToolCall(client, "unknown_tool", {});

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Unknown tool: unknown_tool");
  });
});
