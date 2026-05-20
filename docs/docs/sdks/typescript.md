---
title: TypeScript SDK Reference
sidebar_label: TypeScript SDK
description: API reference for stigmem-ts — StigmemClient, types, value constructors, and error classes.
audience: Integrator
---

# TypeScript SDK Reference

<p className="stigmem-meta"><span>5 min read</span><span>TypeScript / Node integrator</span><span>stigmem-ts</span></p>

<div className="stigmem-lead">

**What this page covers**

`stigmem-ts` is the official TypeScript client for the Stigmem REST
API. It covers facts, conflicts, federation, lint, recall, memory
cards, and subscriptions. Targets Node 20+ and is bundler-compatible
(esbuild, Rollup, Webpack, Vite).

</div>

**Audience:** TypeScript / Node.js developers integrating with a Stigmem node.

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

<div className="stigmem-keypoint">

**All methods return promises and throw `StigmemHTTPError` subclasses on non-2xx responses.**

</div>

### Facts

```ts
client.assertFact(entity, relation, value, source, opts?: AssertOptions): Promise<Fact>
client.retract(entity, relation, scope, source, value?): Promise<Fact>
client.getFact(factId: string): Promise<Fact>
client.query(opts?: QueryOptions): Promise<FactPage>
```

**`AssertOptions`:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Type</dd>
</div>

<div>
<dt><code>confidence</code></dt>
<dt><span className="stigmem-fields__type">1.0</span></dt>
<dd><code>number</code></dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">"company"</span></dt>
<dd><code>FactScope</code></dd>
</div>

<div>
<dt><code>valid_until</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd><code>string</code></dd>
</div>

</div>

**`QueryOptions`:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Type</dd>
</div>

<div>
<dt><code>entity</code> / <code>relation</code> / <code>source</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd><code>string</code></dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd><code>FactScope</code></dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd><code>number</code></dd>
</div>

<div>
<dt><code>include_contradicted</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd><code>boolean</code></dd>
</div>

<div>
<dt><code>include_expired</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd><code>boolean</code></dd>
</div>

<div>
<dt><code>cursor</code> / <code>after</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd><code>string</code></dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">50</span></dt>
<dd><code>number</code></dd>
</div>

</div>

Use `page.cursor` from the response for cursor-based pagination.

### Recall

```ts
client.recall(query: string, opts?: RecallOptions): Promise<RecallResponse>
```

**`RecallOptions`:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Type</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">"local"</span></dt>
<dd><code>FactScope</code></dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">4000</span></dt>
<dd><code>number</code></dd>
</div>

<div>
<dt><code>depth</code></dt>
<dt><span className="stigmem-fields__type">2</span></dt>
<dd><code>number</code></dd>
</div>

<div>
<dt><code>weights</code></dt>
<dt><span className="stigmem-fields__type">server defaults</span></dt>
<dd><code>RecallWeights</code></dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">0.1</span></dt>
<dd><code>number</code></dd>
</div>

<div>
<dt><code>include_neighbors</code></dt>
<dt><span className="stigmem-fields__type">true</span></dt>
<dd><code>boolean</code></dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">100</span></dt>
<dd><code>number</code></dd>
</div>

</div>

**`RecallResponse` fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>recall_id</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>UUID for this recall call.</dd>
</div>

<div>
<dt><code>query_hash</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>SHA-256 of the query string.</dd>
</div>

<div>
<dt><code>facts</code></dt>
<dt><span className="stigmem-fields__type">ScoredFact[]</span></dt>
<dd>Ranked, token-budget-packed facts.</dd>
</div>

<div>
<dt><code>total_scored</code></dt>
<dt><span className="stigmem-fields__type">number</span></dt>
<dd>Candidates scored before packing.</dd>
</div>

<div>
<dt><code>token_budget</code> / <code>tokens_used</code></dt>
<dt><span className="stigmem-fields__type">number</span></dt>
<dd>Requested vs actual budget.</dd>
</div>

<div>
<dt><code>truncated</code></dt>
<dt><span className="stigmem-fields__type">boolean</span></dt>
<dd>True when budget was exhausted.</dd>
</div>

</div>

`RecallWeights` defaults: `{ lexical: 0.35, semantic: 0.35, graph: 0.15, source_trust: 0.10, recency: 0.05 }`.

### Memory cards

```ts
client.getCard(entityUri: string, opts?: CardOptions): Promise<MemoryCard>
```

**`CardOptions`:** `scope` (default `"local"`), `refresh` (default `false`).

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

**`MemoryCard` fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>entity_uri</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Entity the card describes.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Scope materialised from.</dd>
</div>

<div>
<dt><code>summary</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Structured text summary.</dd>
</div>

<div>
<dt><code>fact_hashes</code></dt>
<dt><span className="stigmem-fields__type">string[]</span></dt>
<dd>SHA-256(fact_id) for each contributing fact.</dd>
</div>

<div>
<dt><code>avg_confidence</code></dt>
<dt><span className="stigmem-fields__type">number</span></dt>
<dd>Source-trust-weighted mean confidence.</dd>
</div>

<div>
<dt><code>refreshed_at</code></dt>
<dt><span className="stigmem-fields__type">string?</span></dt>
<dd>ISO 8601 UTC timestamp.</dd>
</div>

<div>
<dt><code>is_stale</code></dt>
<dt><span className="stigmem-fields__type">boolean</span></dt>
<dd>New fact asserted since last refresh.</dd>
</div>

<div>
<dt><code>has_contradictions</code></dt>
<dt><span className="stigmem-fields__type">boolean</span></dt>
<dd>Two live facts share the same relation.</dd>
</div>

</div>

### Conflicts · Lint · Federation · Node info

```ts
client.listConflicts(opts?: ConflictListOptions): Promise<ConflictPage>
client.resolveConflict(conflictId: string, opts?: ResolveOptions): Promise<ConflictResolution>

client.lint(scope: FactScope, opts?: LintOptions): Promise<LintResult>

client.federationStatus(): Promise<Peer[]>
client.nodeInfo(): Promise<NodeInfo>   // GET /.well-known/stigmem (no auth)
```

### Subscribe (polling, async generator)

```ts
client.subscribeScope(
  scope:  FactScope,
  opts?:  SubscribeOptions,
): AsyncGenerator<Fact[]>
```

**`SubscribeOptions`:** `intervalMs` (default `30000`), `signal` (`AbortSignal`).

```ts
const ac = new AbortController();
setTimeout(() => ac.abort(), 60_000);

for await (const batch of client.subscribeScope("local", { intervalMs: 5_000, signal: ac.signal })) {
  console.log(`${batch.length} new fact(s)`);
}
```

<div className="stigmem-keypoint">

**The generator tracks a cursor internally.**

Each batch contains only facts newer than the previous poll.

</div>

## Value constructors

```ts
import { sv, tv, nv, bv, dtv, rv, nullv } from "stigmem-ts";

sv("hello")                        // StringValue   { type: "string",   v: "hello" }
tv("long text...")                 // TextValue     { type: "text",     v: "..." }
nv(3.14)                           // NumberValue   { type: "number",   v: 3.14 }
bv(true)                           // BooleanValue  { type: "boolean",  v: true }
dtv("2026-05-04T00:00:00Z")        // DatetimeValue { type: "datetime", v: "..." }
rv("stigmem://company.example/x")  // RefValue      { type: "ref",      v: "..." }
nullv()                            // NullValue     { type: "null" }
```

## Errors

<div className="stigmem-fields">

<div>
<dt>Class</dt>
<dt><span className="stigmem-fields__type">HTTP</span></dt>
<dd>When raised</dd>
</div>

<div>
<dt><code>StigmemHTTPError</code></dt>
<dt><span className="stigmem-fields__type">any non-2xx</span></dt>
<dd>Base class.</dd>
</div>

<div>
<dt><code>StigmemAuthError</code></dt>
<dt><span className="stigmem-fields__type">401 / 403</span></dt>
<dd>Invalid or missing API key.</dd>
</div>

<div>
<dt><code>StigmemNotFoundError</code></dt>
<dt><span className="stigmem-fields__type">404</span></dt>
<dd>Resource does not exist.</dd>
</div>

<div>
<dt><code>StigmemConflictError</code></dt>
<dt><span className="stigmem-fields__type">409</span></dt>
<dd>Conflicting resource state.</dd>
</div>

</div>

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

## Custom fetch

```ts
import { StigmemClient } from "stigmem-ts";
import { fetch } from "undici";

const client = new StigmemClient({
  url: "http://localhost:8000",
  fetch: fetch as unknown as typeof globalThis.fetch,
});
```

## Bundler smoke (esbuild)

```bash
cd sdks/stigmem-ts
pnpm smoke
```

## Regenerating types from the OpenAPI spec

```bash
make sdk-ts-generate   # just generation
make sdk-ts            # full pipeline: generate → build → test → pack
```

The ergonomic types in `src/types.ts` (tagged-union `FactValue`, value constructors) are hand-authored on top of the generated layer to match the Stigmem wire format described in spec §2.1.

## Advanced features

### Content-addressed fact IDs (§25)

```ts
const factByUuid = await client.getFact("550e8400-e29b-41d4-a716-446655440000");
const factByCid  = await client.getFact("sha256:a3f2b8c901d4...");
```

<div className="stigmem-keypoint">

**Asserting the same (entity, relation, value, source, scope) tuple twice returns the existing fact.**

CID-based deduplication is automatic.

</div>

### Time-travel queries (§24)

The `as_of` parameter is available on the fact query and recall endpoints via the REST API. Use the HTTP client directly:

```ts
const res = await fetch(
  `${url}/v1/facts?entity=user:alice&as_of=2026-04-15T00:00:00Z`,
  { headers: { Authorization: `Bearer ${apiKey}` } },
);
const { facts } = await res.json();
```

## See also

<div className="stigmem-grid">

<div><h4><a href="../get-started/sdk-quickstart.md">Tutorial: SDK Quickstart</a></h4><p>Assert, recall, and subscribe in Python / TS / Go.</p></div>
<div><h4><a href="../concepts/recall/">Recall guide</a></h4><p>Hybrid recall, weight tuning, fast-path.</p></div>
<div><h4><a href="./python">Python SDK Reference</a></h4><p>Equivalent Python client.</p></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/sdk-go">Go SDK Reference</a></h4><p>Go client.</p></div>

</div>
