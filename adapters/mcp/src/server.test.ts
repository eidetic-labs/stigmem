import { describe, expect, it, vi } from "vitest";

import { StigmemAuthError } from "@eidetic-labs/stigmem-ts";

import { MCP_SERVER_VERSION, SYSTEM_PROMPT_DIRECTIVE, TOOLS, handleToolCall } from "./server.js";

describe("TOOLS", () => {
  it("exposes the expected MCP tool names", () => {
    expect(TOOLS.map((tool) => tool.name)).toEqual([
      "assert_fact",
      "query_facts",
      "recall",
      "resolve_contradiction",
      "subscribe_scope",
      "lint_scope",
    ]);
  });

  it("reports the package-aligned MCP server version", () => {
    expect(MCP_SERVER_VERSION).toBe("0.9.0-alpha.8");
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
    recall: vi.fn(),
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
      expect.objectContaining({
        confidence: 1,
        scope: "company",
        valid_until: undefined,
        write_mode: "assert",
        derived_from: [],
        session_id: expect.stringMatching(/^mcp:/),
      }),
    );
    expect(JSON.parse(result.content[0].text)).toEqual({ id: "fact-001" });
  });

  it("passes explicit session and provenance options for assert_fact", async () => {
    client.assertFact.mockResolvedValueOnce({ id: "fact-002" });

    await handleToolCall(client, "assert_fact", {
      entity: "thread:handoff",
      relation: "memory:summary",
      value: "{\"type\":\"text\",\"v\":\"summary\"}",
      source: "agent:cto",
      write_mode: "summarize_with_provenance",
      derived_from: "[{\"fact_id\":\"fact-source\"}]",
      session_id: "session-mcp-001",
    });

    expect(client.assertFact).toHaveBeenCalledWith(
      "thread:handoff",
      "memory:summary",
      { type: "text", v: "summary" },
      "agent:cto",
      expect.objectContaining({
        write_mode: "summarize_with_provenance",
        derived_from: [{ fact_id: "fact-source" }],
        session_id: "session-mcp-001",
      }),
    );
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
      session_id: expect.stringMatching(/^mcp:/),
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

  it("returns recall content and instructions as separate channels", async () => {
    const contentFact = { fact: { id: "content-1" }, score: 0.9 };
    const instructionFact = { fact: { id: "instruction-1" }, score: 0.8 };
    client.recall.mockResolvedValueOnce({
      recall_id: "recall-001",
      query_hash: "hash-001",
      facts: [contentFact],
      content: [contentFact],
      instructions: [instructionFact],
      total_scored: 2,
      token_budget: 1000,
      tokens_used: 25,
      truncated: false,
    });

    const result = await handleToolCall(client, "recall", {
      query: "project status",
      scope: "local",
      token_budget: 1000,
      depth: 1,
      include_neighbors: false,
      limit: 10,
      weights: "{\"lexical\":1}",
    });

    expect(client.recall).toHaveBeenCalledWith("project status", {
      scope: "local",
      token_budget: 1000,
      depth: 1,
      weights: { lexical: 1 },
      min_confidence: undefined,
      include_neighbors: false,
      limit: 10,
      session_id: expect.stringMatching(/^mcp:/),
    });
    const payload = JSON.parse(result.content[0].text);
    expect(payload.content).toEqual([contentFact]);
    expect(payload.instructions).toEqual([instructionFact]);
    expect(payload.system_prompt_directive).toBe(SYSTEM_PROMPT_DIRECTIVE);
  });

  it("falls back to facts as content for legacy recall responses", async () => {
    const fact = { fact: { id: "legacy-content" }, score: 0.7 };
    client.recall.mockResolvedValueOnce({
      recall_id: "recall-legacy",
      query_hash: "hash-legacy",
      facts: [fact],
      total_scored: 1,
      token_budget: 1000,
      tokens_used: 12,
      truncated: false,
    });

    const result = await handleToolCall(client, "recall", {
      query: "legacy server",
    });

    const payload = JSON.parse(result.content[0].text);
    expect(payload.content).toEqual([fact]);
    expect(payload.instructions).toEqual([]);
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
