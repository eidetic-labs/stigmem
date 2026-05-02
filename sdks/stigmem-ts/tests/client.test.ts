import { describe, it, expect, vi, beforeEach } from "vitest";
import { StigmemClient, StigmemAuthError, StigmemNotFoundError, sv, tv, rv } from "../src/index.js";

const BASE = "http://test-node";
const KEY = "sk-test";

const SAMPLE_FACT = {
  id: "fact-001",
  entity: "user:alice",
  relation: "memory:role",
  value: { type: "string", v: "CEO" },
  source: "agent:test",
  timestamp: "2026-05-02T00:00:00Z",
  hlc: "1746230400000.001",
  confidence: 1.0,
  scope: "company",
  contradicted: false,
};

const SAMPLE_NODE_INFO = {
  version: "0.5",
  node_id: "stigmem://node.acme",
  node_url: BASE,
  auth: "required",
  federation: "disabled",
  namespaces: ["memory:", "intent:"],
};

function mockFetch(responses: Map<string, { status: number; body: unknown }>) {
  return vi.fn(async (url: string, _opts?: RequestInit) => {
    const key = url.replace(BASE, "").split("?")[0];
    const resp = responses.get(key);
    if (!resp) throw new Error(`Unmocked URL: ${url}`);
    return {
      ok: resp.status >= 200 && resp.status < 300,
      status: resp.status,
      statusText: resp.status === 200 ? "OK" : "Error",
      json: async () => resp.body,
    } as Response;
  });
}

// ---------------------------------------------------------------------------
// nodeInfo
// ---------------------------------------------------------------------------

describe("nodeInfo", () => {
  it("returns parsed NodeInfo", async () => {
    const fetchMock = mockFetch(new Map([
      ["/.well-known/stigmem", { status: 200, body: SAMPLE_NODE_INFO }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const info = await client.nodeInfo();
    expect(info.version).toBe("0.5");
    expect(info.node_id).toBe("stigmem://node.acme");
    expect(info.auth).toBe("required");
  });

  it("throws StigmemAuthError on 401", async () => {
    const fetchMock = mockFetch(new Map([
      ["/.well-known/stigmem", { status: 401, body: { detail: "unauthorized" } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: "bad", fetch: fetchMock as unknown as typeof fetch });
    await expect(client.nodeInfo()).rejects.toThrow(StigmemAuthError);
  });
});

// ---------------------------------------------------------------------------
// assertFact
// ---------------------------------------------------------------------------

describe("assertFact", () => {
  it("asserts a string fact", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/facts", { status: 201, body: SAMPLE_FACT }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const fact = await client.assertFact("user:alice", "memory:role", sv("CEO"), "agent:test");
    expect(fact.id).toBe("fact-001");
    expect(fact.value.type).toBe("string");
  });

  it("asserts a text fact", async () => {
    const sample = { ...SAMPLE_FACT, id: "fact-002", value: { type: "text", v: "long summary" } };
    const fetchMock = mockFetch(new Map([
      ["/v1/facts", { status: 201, body: sample }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const fact = await client.assertFact("project:acme", "roadmap:summary", tv("long summary"), "agent:cto");
    expect(fact.value.type).toBe("text");
  });
});

// ---------------------------------------------------------------------------
// retract
// ---------------------------------------------------------------------------

describe("retract", () => {
  it("asserts with confidence=0.0", async () => {
    const retracted = { ...SAMPLE_FACT, id: "fact-003", confidence: 0.0 };
    let capturedBody: unknown;
    const fetchMock = vi.fn(async (_url: string, opts?: RequestInit) => {
      capturedBody = opts?.body ? JSON.parse(opts.body as string) : null;
      return { ok: true, status: 201, json: async () => retracted } as Response;
    });
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const fact = await client.retract("user:alice", "memory:role", "company", "agent:test");
    expect(fact.confidence).toBe(0.0);
    expect((capturedBody as Record<string, unknown>)["confidence"]).toBe(0.0);
  });
});

// ---------------------------------------------------------------------------
// getFact
// ---------------------------------------------------------------------------

describe("getFact", () => {
  it("fetches by ID", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/facts/fact-001", { status: 200, body: SAMPLE_FACT }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const fact = await client.getFact("fact-001");
    expect(fact.entity).toBe("user:alice");
  });

  it("throws StigmemNotFoundError on 404", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/facts/missing", { status: 404, body: { detail: "not found" } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    await expect(client.getFact("missing")).rejects.toThrow(StigmemNotFoundError);
  });
});

// ---------------------------------------------------------------------------
// query
// ---------------------------------------------------------------------------

describe("query", () => {
  it("returns a FactPage", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/facts", { status: 200, body: { facts: [SAMPLE_FACT], total: 1, cursor: null } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const page = await client.query({ entity: "user:alice" });
    expect(page.facts).toHaveLength(1);
    expect(page.facts[0]?.entity).toBe("user:alice");
  });
});

// ---------------------------------------------------------------------------
// conflicts
// ---------------------------------------------------------------------------

describe("listConflicts / resolveConflict", () => {
  it("returns empty ConflictPage", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/conflicts", { status: 200, body: { conflicts: [], cursor: null, has_more: false } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const page = await client.listConflicts();
    expect(page.conflicts).toHaveLength(0);
    expect(page.has_more).toBe(false);
  });

  it("resolves a conflict", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/conflicts/c-001/resolve", { status: 200, body: { resolution_fact_id: "fact-999", conflict_status: "resolved" } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const result = await client.resolveConflict("c-001", { winning_fact_id: "fact-001", resolution_note: "prefer a" });
    expect(result.conflict_status).toBe("resolved");
    expect(result.resolution_fact_id).toBe("fact-999");
  });
});

// ---------------------------------------------------------------------------
// federationStatus
// ---------------------------------------------------------------------------

describe("federationStatus", () => {
  it("returns empty peer list", async () => {
    const fetchMock = mockFetch(new Map([
      ["/v1/federation/peers", { status: 200, body: { peers: [] } }],
    ]));
    const client = new StigmemClient({ url: BASE, apiKey: KEY, fetch: fetchMock as unknown as typeof fetch });
    const peers = await client.federationStatus();
    expect(peers).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Conformance: value constructor round-trips
// ---------------------------------------------------------------------------

describe("value constructors", () => {
  it("sv produces StringValue", () => {
    const v = sv("hello");
    expect(v).toEqual({ type: "string", v: "hello" });
  });

  it("rv produces RefValue", () => {
    const v = rv("stigmem://node.acme/facts/123");
    expect(v).toEqual({ type: "ref", v: "stigmem://node.acme/facts/123" });
  });

  it("tv produces TextValue", () => {
    const v = tv("paragraph body");
    expect(v).toEqual({ type: "text", v: "paragraph body" });
  });
});
