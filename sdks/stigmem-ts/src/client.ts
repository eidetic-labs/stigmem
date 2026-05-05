/**
 * Stigmem TypeScript client SDK — spec v1.0.
 */

import type {
  AssertOptions,
  CardOptions,
  Conflict,
  ConflictListOptions,
  ConflictPage,
  ConflictResolution,
  Fact,
  FactPage,
  FactScope,
  FactValue,
  LintOptions,
  LintResult,
  MemoryCard,
  NodeInfo,
  Peer,
  QueryOptions,
  RecallOptions,
  RecallResponse,
  ResolveOptions,
  SubscribeOptions,
} from "./types.js";
import { sv } from "./types.js";

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class StigmemError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StigmemError";
  }
}

export class StigmemHTTPError extends StigmemError {
  constructor(
    public readonly statusCode: number,
    public readonly detail: string,
  ) {
    super(`HTTP ${statusCode}: ${detail}`);
    this.name = "StigmemHTTPError";
  }
}

export class StigmemAuthError extends StigmemHTTPError {
  constructor(statusCode: number, detail: string) {
    super(statusCode, detail);
    this.name = "StigmemAuthError";
  }
}

export class StigmemNotFoundError extends StigmemHTTPError {
  constructor(detail: string) {
    super(404, detail);
    this.name = "StigmemNotFoundError";
  }
}

export class StigmemConflictError extends StigmemHTTPError {
  constructor(detail: string) {
    super(409, detail);
    this.name = "StigmemConflictError";
  }
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

interface ClientOptions {
  url: string;
  apiKey?: string;
  timeoutMs?: number;
  fetch?: typeof fetch;
}

async function raiseForStatus(res: Response): Promise<void> {
  if (res.ok) return;
  let detail: string;
  try {
    const body = await res.json() as { detail?: string };
    detail = body.detail ?? res.statusText;
  } catch {
    detail = res.statusText;
  }
  if (res.status === 401 || res.status === 403) {
    throw new StigmemAuthError(res.status, detail);
  }
  if (res.status === 404) {
    throw new StigmemNotFoundError(detail);
  }
  if (res.status === 409) {
    throw new StigmemConflictError(detail);
  }
  throw new StigmemHTTPError(res.status, detail);
}

// ---------------------------------------------------------------------------
// StigmemClient
// ---------------------------------------------------------------------------

export class StigmemClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly fetchFn: typeof fetch;

  constructor(opts: ClientOptions) {
    this.baseUrl = opts.url.replace(/\/$/, "");
    this.headers = { "Accept": "application/json", "Content-Type": "application/json" };
    if (opts.apiKey) {
      this.headers["Authorization"] = `Bearer ${opts.apiKey}`;
    }
    this.fetchFn = opts.fetch ?? globalThis.fetch;
  }

  private async req<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string | number | boolean | undefined>,
  ): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (params) {
      const qs = Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join("&");
      if (qs) url += `?${qs}`;
    }
    const res = await this.fetchFn(url, {
      method,
      headers: this.headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    await raiseForStatus(res);
    return res.json() as Promise<T>;
  }

  // ------------------------------------------------------------------
  // Node info
  // ------------------------------------------------------------------

  async nodeInfo(): Promise<NodeInfo> {
    return this.req<NodeInfo>("GET", "/.well-known/stigmem");
  }

  // ------------------------------------------------------------------
  // Facts
  // ------------------------------------------------------------------

  async assertFact(
    entity: string,
    relation: string,
    value: FactValue,
    source: string,
    opts: AssertOptions = {},
  ): Promise<Fact> {
    const body = {
      entity,
      relation,
      value,
      source,
      confidence: opts.confidence ?? 1.0,
      scope: opts.scope ?? "company",
      ...(opts.valid_until ? { valid_until: opts.valid_until } : {}),
    };
    return this.req<Fact>("POST", "/v1/facts", body);
  }

  async retract(
    entity: string,
    relation: string,
    scope: FactScope,
    source: string,
    value?: FactValue,
  ): Promise<Fact> {
    return this.assertFact(
      entity,
      relation,
      value ?? sv("retracted"),
      source,
      { confidence: 0.0, scope },
    );
  }

  async getFact(factId: string): Promise<Fact> {
    return this.req<Fact>("GET", `/v1/facts/${factId}`);
  }

  async query(opts: QueryOptions = {}): Promise<FactPage> {
    return this.req<FactPage>("GET", "/v1/facts", undefined, {
      entity:               opts.entity,
      relation:             opts.relation,
      source:               opts.source,
      scope:                opts.scope,
      min_confidence:       opts.min_confidence,
      include_contradicted: opts.include_contradicted,
      include_expired:      opts.include_expired,
      cursor:               opts.cursor,
      after:                opts.after,
      limit:                opts.limit ?? 50,
    });
  }

  // ------------------------------------------------------------------
  // Conflicts
  // ------------------------------------------------------------------

  async listConflicts(opts: ConflictListOptions = {}): Promise<ConflictPage> {
    return this.req<ConflictPage>("GET", "/v1/conflicts", undefined, {
      status: opts.status ?? "unresolved",
      cursor: opts.cursor,
      limit:  opts.limit ?? 50,
    });
  }

  async resolveConflict(
    conflictId: string,
    opts: ResolveOptions = {},
  ): Promise<ConflictResolution> {
    const body: Record<string, unknown> = {
      resolution_note: opts.resolution_note ?? "",
    };
    if (opts.winning_fact_id !== undefined) {
      body["winning_fact_id"] = opts.winning_fact_id;
    }
    if (opts.new_value !== undefined) {
      body["new_value"] = opts.new_value;
    }
    return this.req<ConflictResolution>("POST", `/v1/conflicts/${conflictId}/resolve`, body);
  }

  // ------------------------------------------------------------------
  // Lint — v0.7 (spec §14)
  // ------------------------------------------------------------------

  async lint(scope: FactScope, opts: LintOptions = {}): Promise<LintResult> {
    const body: Record<string, unknown> = { scope };
    if (opts.checks?.length) body["checks"] = opts.checks;
    if (opts.entity !== undefined) body["entity"] = opts.entity;
    if (opts.relation !== undefined) body["relation"] = opts.relation;
    if (opts.stale_lookahead_s !== undefined) body["stale_lookahead_s"] = opts.stale_lookahead_s;
    return this.req<LintResult>("POST", "/v1/lint", body);
  }

  // ------------------------------------------------------------------
  // Federation
  // ------------------------------------------------------------------

  async federationStatus(): Promise<Peer[]> {
    const page = await this.req<{ peers: Peer[] }>("GET", "/v1/federation/peers");
    return page.peers;
  }

  // ------------------------------------------------------------------
  // Recall (Phase 9 — spec §20)
  // ------------------------------------------------------------------

  async recall(query: string, opts: RecallOptions = {}): Promise<RecallResponse> {
    const body: Record<string, unknown> = {
      query,
      scope:             opts.scope             ?? "local",
      token_budget:      opts.token_budget      ?? 4000,
      depth:             opts.depth             ?? 2,
      min_confidence:    opts.min_confidence    ?? 0.1,
      include_neighbors: opts.include_neighbors ?? true,
      limit:             opts.limit             ?? 100,
    };
    if (opts.weights) body["weights"] = opts.weights;
    return this.req<RecallResponse>("POST", "/v1/recall", body);
  }

  // ------------------------------------------------------------------
  // Memory cards (Phase 9 — spec §20)
  // ------------------------------------------------------------------

  async getCard(entityUri: string, opts: CardOptions = {}): Promise<MemoryCard> {
    return this.req<MemoryCard>("GET", `/v1/cards/${entityUri}`, undefined, {
      scope:   opts.scope   ?? "local",
      refresh: opts.refresh ? true : undefined,
    });
  }

  // ------------------------------------------------------------------
  // Subscribe (async generator, polling)
  // ------------------------------------------------------------------

  async *subscribeScope(
    scope: FactScope,
    opts: SubscribeOptions = {},
  ): AsyncGenerator<Fact[]> {
    const intervalMs = opts.intervalMs ?? 30_000;
    let cursor: string | undefined;

    while (true) {
      if (opts.signal?.aborted) return;

      const page = await this.query({ scope, limit: 100, ...(cursor !== undefined ? { cursor } : {}) });
      if (page.facts.length > 0) {
        yield page.facts;
      }
      cursor = page.cursor ?? undefined;

      if (opts.signal?.aborted) return;
      await new Promise<void>((resolve, reject) => {
        const t = setTimeout(resolve, intervalMs);
        opts.signal?.addEventListener("abort", () => { clearTimeout(t); reject(new Error("aborted")); });
      }).catch(() => { /* aborted */ });
      if (opts.signal?.aborted) return;
    }
  }
}
