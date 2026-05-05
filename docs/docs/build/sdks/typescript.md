---
title: TypeScript SDK Reference
sidebar_label: TypeScript SDK
description: API reference for stigmem-ts — StigmemClient, types, value constructors, and error classes.
audience: Integrator
---

# TypeScript SDK Reference

**Audience:** TypeScript / Node.js developers integrating with a Stigmem node.

`stigmem-ts` is the official TypeScript client for the Stigmem REST API. It covers facts, conflicts, federation, lint, recall, memory cards, and subscriptions. It targets Node 20+ and is bundler-compatible (esbuild, Rollup, Webpack, Vite).

## Installation

```bash
npm install stigmem-ts
# or
pnpm add stigmem-ts
```

## Quick start

```ts
import { StigmemClient, sv, tv } from "stigmem-ts";

const client = new StigmemClient({
  url: "http://localhost:8000",
  apiKey: process.env.STIGMEM_API_KEY,
});

// Assert a fact
const fact = await client.assertFact(
  "user:alice",
  "memory:role",
  sv("engineer"),
  "agent:assistant",
  { scope: "local" },
);
console.log(fact.id); // UUID

// Hybrid recall
const recall = await client.recall("Alice's current role", { token_budget: 500 });
for (const sf of recall.facts) {
  console.log(`[${sf.score.toFixed(3)}] ${sf.fact.relation}`);
}

// Entity memory card
const card = await client.getCard("user:alice");
console.log(card.summary);
```

## `StigmemClient`

```ts
new StigmemClient(opts: {
  url:       string;
  apiKey?:   string;
  timeoutMs?: number;
  fetch?:    typeof fetch;  // inject a custom fetch (e.g. undici, node-fetch, test mocks)
})
```

All methods return promises and throw `StigmemHTTPError` subclasses on non-2xx responses.

### Facts

#### `assertFact`

```ts
client.assertFact(
  entity:   string,
  relation: string,
  value:    FactValue,
  source:   string,
  opts?:    AssertOptions,
): Promise<Fact>
```

Assert a new fact. `AssertOptions`:

| Field | Type | Default |
|-------|------|---------|
| `confidence` | `number` | `1.0` |
| `scope` | `FactScope` | `"company"` |
| `valid_until` | `string` | — |

#### `retract`

```ts
client.retract(
  entity:   string,
  relation: string,
  scope:    FactScope,
  source:   string,
  value?:   FactValue,
): Promise<Fact>
```

Assert a retraction (confidence=0.0). Convenience wrapper around `assertFact`.

#### `getFact`

```ts
client.getFact(factId: string): Promise<Fact>
```

Fetch a single fact by UUID. Raises `StigmemNotFoundError` (404) when absent.

#### `query`

```ts
client.query(opts?: QueryOptions): Promise<FactPage>
```

Paginated fact query. `QueryOptions`:

| Field | Type | Default |
|-------|------|---------|
| `entity` | `string` | — |
| `relation` | `string` | — |
| `source` | `string` | — |
| `scope` | `FactScope` | — |
| `min_confidence` | `number` | — |
| `include_contradicted` | `boolean` | `false` |
| `include_expired` | `boolean` | `false` |
| `cursor` | `string` | — |
| `after` | `string` | — |
| `limit` | `number` | `50` |

Use `page.cursor` from the response for cursor-based pagination.

### Recall (Phase 9 — §20.3)

#### `recall`

```ts
client.recall(query: string, opts?: RecallOptions): Promise<RecallResponse>
```

Hybrid recall — return the most salient facts for `query` within `token_budget`. Combines lexical (FTS5/BM25), dense-vector (ANN), and graph-traversal signals.

`RecallOptions`:

| Field | Type | Default |
|-------|------|---------|
| `scope` | `FactScope` | `"local"` |
| `token_budget` | `number` | `4000` |
| `depth` | `number` | `2` |
| `weights` | `RecallWeights` | server defaults |
| `min_confidence` | `number` | `0.1` |
| `include_neighbors` | `boolean` | `true` |
| `limit` | `number` | `100` |

`RecallResponse` fields:

| Field | Type | Description |
|-------|------|-------------|
| `recall_id` | `string` | UUID for this recall call |
| `query_hash` | `string` | SHA-256 of the query string |
| `facts` | `ScoredFact[]` | Ranked, token-budget-packed facts |
| `total_scored` | `number` | Candidates scored before packing |
| `token_budget` | `number` | Requested budget |
| `tokens_used` | `number` | Tokens actually used |
| `truncated` | `boolean` | True when budget was exhausted |

`ScoredFact` fields: `fact`, `score`, `score_breakdown`, `hop_distance`, `token_estimate`, `from_card`.

`RecallWeights` defaults: `{ lexical: 0.35, semantic: 0.35, graph: 0.15, source_trust: 0.10, recency: 0.05 }`.

### Memory cards (Phase 9 — §20.4)

#### `getCard`

```ts
client.getCard(entityUri: string, opts?: CardOptions): Promise<MemoryCard>
```

Fetch the synthesized memory card for `entityUri`. `CardOptions`:

| Field | Type | Default |
|-------|------|---------|
| `scope` | `FactScope` | `"local"` |
| `refresh` | `boolean` | `false` |

Raises `StigmemNotFoundError` when the entity has no live facts.

`MemoryCard` fields:

| Field | Type | Description |
|-------|------|-------------|
| `entity_uri` | `string` | Entity the card describes |
| `scope` | `string` | Scope the card was materialised from |
| `summary` | `string` | Structured text summary of live facts |
| `fact_hashes` | `string[]` | SHA-256(fact_id) for each contributing fact |
| `avg_confidence` | `number` | Source-trust-weighted mean confidence |
| `refreshed_at` | `string?` | ISO 8601 UTC timestamp of last refresh |
| `is_stale` | `boolean` | New fact asserted since last refresh |
| `has_contradictions` | `boolean` | Any two live facts share the same relation |

```ts
import { StigmemNotFoundError } from "stigmem-ts";

try {
  const card = await client.getCard("user:alice", { scope: "local" });
  console.log(card.summary);
} catch (err) {
  if (err instanceof StigmemNotFoundError) {
    console.log("Entity has no live facts");
  }
}
```

### Conflicts

#### `listConflicts`

```ts
client.listConflicts(opts?: ConflictListOptions): Promise<ConflictPage>
```

#### `resolveConflict`

```ts
client.resolveConflict(conflictId: string, opts?: ResolveOptions): Promise<ConflictResolution>
```

`ResolveOptions`: `winning_fact_id?`, `resolution_note?`, `new_value?`.

### Lint (§14)

#### `lint`

```ts
client.lint(scope: FactScope, opts?: LintOptions): Promise<LintResult>
```

`LintOptions`: `checks?` (`LintCheck[]`), `entity?`, `relation?`, `stale_lookahead_s?`.

### Federation

#### `federationStatus`

```ts
client.federationStatus(): Promise<Peer[]>
```

### Subscribe (polling, async generator)

#### `subscribeScope`

```ts
client.subscribeScope(
  scope:  FactScope,
  opts?:  SubscribeOptions,
): AsyncGenerator<Fact[]>
```

Yields batches of new facts on each poll interval. `SubscribeOptions`:

| Field | Type | Default |
|-------|------|---------|
| `intervalMs` | `number` | `30000` |
| `signal` | `AbortSignal` | — |

```ts
const ac = new AbortController();
setTimeout(() => ac.abort(), 60_000);

for await (const batch of client.subscribeScope("local", { intervalMs: 5_000, signal: ac.signal })) {
  console.log(`${batch.length} new fact(s)`);
}
```

The generator tracks a cursor internally so each batch contains only facts newer than the previous poll.

### Node info

```ts
client.nodeInfo(): Promise<NodeInfo>
```

Fetches `/.well-known/stigmem`. No authentication required.

---

## Value constructors

```ts
import { sv, tv, nv, bv, dtv, rv, nullv } from "stigmem-ts";

sv("hello")                        // StringValue   { type: "string",   v: "hello" }
tv("long text...")                 // TextValue     { type: "text",     v: "..." }
nv(3.14)                           // NumberValue   { type: "number",   v: 3.14 }
bv(true)                           // BooleanValue  { type: "boolean",  v: true }
dtv("2026-05-04T00:00:00Z")        // DatetimeValue { type: "datetime", v: "..." }
rv("stigmem://company.example/x") // RefValue      { type: "ref",      v: "..." }
nullv()                            // NullValue     { type: "null" }
```

---

## Errors

| Class | HTTP status | When raised |
|-------|-------------|-------------|
| `StigmemHTTPError` | any non-2xx | Base class |
| `StigmemAuthError` | 401 / 403 | Invalid or missing API key |
| `StigmemNotFoundError` | 404 | Resource does not exist |
| `StigmemConflictError` | 409 | Conflicting resource state |

```ts
import {
  StigmemAuthError,
  StigmemNotFoundError,
  StigmemConflictError,
  StigmemHTTPError,
} from "stigmem-ts";

try {
  await client.getFact("unknown-id");
} catch (err) {
  if (err instanceof StigmemNotFoundError) {
    console.log("not found");
  } else if (err instanceof StigmemAuthError) {
    console.log("auth failed — check STIGMEM_API_KEY");
  } else if (err instanceof StigmemHTTPError) {
    console.log(`HTTP ${err.statusCode}: ${err.detail}`);
  }
}
```

---

## Custom fetch

Inject any fetch-compatible implementation — useful for tests and environments without a global `fetch`:

```ts
import { StigmemClient } from "stigmem-ts";
import { fetch } from "undici";

const client = new StigmemClient({
  url: "http://localhost:8000",
  fetch: fetch as unknown as typeof globalThis.fetch,
});
```

---

## Bundler smoke (esbuild)

The SDK ships a `smoke` script that verifies esbuild can tree-shake and bundle it:

```bash
cd sdks/stigmem-ts
pnpm smoke
```

---

## Regenerating types from the OpenAPI spec

Types in `src/generated.ts` are auto-generated from `docs/openapi/stigmem.json`:

```bash
make sdk-ts-generate   # just generation
make sdk-ts            # full pipeline: generate → build → test → pack
```

The ergonomic types in `src/types.ts` (tagged-union `FactValue`, value constructors, etc.) are hand-authored on top of the generated layer to match the Stigmem wire format described in spec §2.1.

---

## Phase 13 features

### Content-addressed fact IDs (§25)

Every fact returned by the node includes a `cid` field — a SHA-256 content hash that uniquely identifies the fact's canonical body. You can fetch a fact by either UUID or CID:

```ts
const factByUuid = await client.getFact("550e8400-e29b-41d4-a716-446655440000");
const factByCid  = await client.getFact("sha256:a3f2b8c901d4...");
```

Asserting the same (entity, relation, value, source, scope) tuple twice returns the existing fact — CID-based deduplication is automatic. See the [Content Addressing guide](../guides/content-addressing.md).

### Time-travel queries (§24)

The `as_of` parameter is available on the fact query and recall endpoints via the REST API. Use the HTTP client directly for time-travel queries:

```ts
const res = await fetch(
  `${url}/v1/facts?entity=user:alice&as_of=2026-04-15T00:00:00Z`,
  { headers: { Authorization: `Bearer ${apiKey}` } },
);
const { facts } = await res.json();
```

See the [Time-Travel Queries guide](../guides/time-travel.md).

---

## See also

- [Tutorial: SDK Quickstart](../tutorials/sdk-quickstart.md) — assert, recall, and subscribe in Python / TS / Go
- [Recall guide](../guides/recall.md) — hybrid recall, weight tuning, fast-path
- [Memory Cards guide](../guides/memory-cards.md) — card lifecycle and divergence policy
- [Asserting facts](../guides/asserting-facts.md) — detailed fact write patterns
- [Querying facts](../guides/querying-facts.md) — structured predicate queries
- [Python SDK Reference](/docs/build/sdks/python) — equivalent Python client
- [Go SDK Reference](./go.md) — Go client
