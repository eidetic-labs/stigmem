---
id: index
title: API Reference
sidebar_label: API Reference
audience: Integrator
---

# API Reference

<p className="stigmem-meta"><span>8 min read</span><span>Integrator · SDK author</span><span>OpenAPI</span></p>

<div className="stigmem-lead">

**What this page covers**

The Stigmem reference node exposes a REST API owned by
`Spec-03-HTTP-API`, with endpoint semantics split across the
component specs listed below. The interactive API reference is
auto-generated from the OpenAPI schema served at
`http://localhost:8000/openapi.json`.

</div>

## Endpoint groups

<div className="stigmem-fields">

<div>
<dt>Group · Base path</dt>
<dt><span className="stigmem-fields__type">Auth</span></dt>
<dd>Spec</dd>
</div>

<div>
<dt><strong>Facts</strong> · <code>/v1/facts</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-01-Fact-Model, Spec-03-HTTP-API, Spec-15-Fact-Semantics.</dd>
</div>

<div>
<dt><strong>Federation</strong> · <code>/v1/federation/&#42;</code></dt>
<dt><span className="stigmem-fields__type">API key + peer token</span></dt>
<dd>Spec-03-HTTP-API, Spec-05-Federation-Trust.</dd>
</div>

<div>
<dt><strong>Conflicts</strong> · <code>/v1/conflicts</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-03-HTTP-API, Spec-15-Fact-Semantics.</dd>
</div>

<div>
<dt><strong>Gardens</strong> · <code>/v1/gardens/&#42;</code></dt>
<dt><span className="stigmem-fields__type">API key (role-gated)</span></dt>
<dd>Spec-02-Scopes-and-ACL, Spec-08-Quarantine-Garden.</dd>
</div>

<div>
<dt><strong>Lint</strong> · <code>/v1/lint</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-20-Lint-Semantics.</dd>
</div>

<div>
<dt><strong>Decay</strong> · <code>/v1/decay/sweep</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X9-Decay-Semantics.</dd>
</div>

<div>
<dt><strong>Synthesis</strong> · <code>/v1/synthesis</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X10-Synthesis.</dd>
</div>

<div>
<dt><strong>Auth / Keys</strong> · <code>/v1/auth/keys/&#42;</code></dt>
<dt><span className="stigmem-fields__type">Admin API key</span></dt>
<dd>Spec-06-Capability-Tokens.</dd>
</div>

<div>
<dt><strong>Auth / Audit</strong> · <code>/v1/auth/audit</code></dt>
<dt><span className="stigmem-fields__type">Admin API key</span></dt>
<dd>Spec-X6-Source-Attestation.</dd>
</div>

<div>
<dt><strong>Admin / Billing</strong> · <code>/v1/admin/billing/events</code></dt>
<dt><span className="stigmem-fields__type">Admin API key</span></dt>
<dd>—</dd>
</div>

<div>
<dt><strong>Async Jobs</strong> · <code>/v1/jobs/:id</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-20, Spec-X9.</dd>
</div>

<div>
<dt><strong>Identity</strong> · <code>/v1/me</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>—</dd>
</div>

<div>
<dt><strong>Node Metadata</strong> · <code>/.well-known/stigmem</code></dt>
<dt><span className="stigmem-fields__type">none</span></dt>
<dd>Spec-03-HTTP-API, Spec-04-Manifests.</dd>
</div>

<div>
<dt><strong>Health</strong> · <code>/healthz</code></dt>
<dt><span className="stigmem-fields__type">none</span></dt>
<dd>—</dd>
</div>

<div>
<dt><strong>Recall</strong> · <code>/v1/recall</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-07-Recall-Pipeline, Spec-X11-Recall-Graph.</dd>
</div>

<div>
<dt><strong>Cards</strong> · <code>/v1/cards/&#42;</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X11-Recall-Graph.</dd>
</div>

<div>
<dt><strong>Graph</strong> · <code>/v1/graph/&#42;</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X11-Recall-Graph.</dd>
</div>

<div>
<dt><strong>Subscriptions</strong> · <code>/v1/subscriptions</code></dt>
<dt><span className="stigmem-fields__type">API key + capability token</span></dt>
<dd>Spec-X7-Subscriptions.</dd>
</div>

<div>
<dt><strong>Provenance</strong> · <code>/v1/facts/:id/provenance</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X11-Recall-Graph.</dd>
</div>

<div>
<dt><strong>Instructions</strong> · <code>/v1/agents/:id/instruction-manifest</code></dt>
<dt><span className="stigmem-fields__type">API key</span></dt>
<dd>Spec-X1-Lazy-Instruction-Discovery.</dd>
</div>

</div>

---

## Graph and recall endpoints

### `GET /v1/recall` · `POST /v1/recall`

Returns a token-budget-bounded, salience-ranked slice of the fact store relevant to a natural-language or structured query. Uses a three-stage hybrid pipeline: lexical (FTS5/BM25), dense vector (ANN via sqlite-vec), and graph expansion (BFS on `entity_edges`). Results are packed with Maximal Marginal Relevance (MMR).

POST is preferred when `query` exceeds 1000 characters.

**Key parameters:**

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>query</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Natural-language or structured query.</dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Max response tokens.</dd>
</div>

<div>
<dt><code>depth</code></dt>
<dt><span className="stigmem-fields__type">1 (max 2)</span></dt>
<dd>Graph expansion depth.</dd>
</div>

<div>
<dt><code>weights</code></dt>
<dt><span className="stigmem-fields__type">&#123;lex:0.30, vec:0.50, graph:0.20&#125;</span></dt>
<dd>Stage weights; must sum to 1.0 ±0.001.</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Entity URI; enables entity-centric (card-first) recall.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Relation filter; skips memory card lookup.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">global</span></dt>
<dd>Garden or global scope.</dd>
</div>

<div>
<dt><code>lambda_mmr</code></dt>
<dt><span className="stigmem-fields__type">0.7</span></dt>
<dd>MMR diversity tradeoff; 1.0 = greedy.</dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">0.1</span></dt>
<dd>Minimum effective confidence.</dd>
</div>

<div>
<dt><code>force_refresh</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Block on synchronous memory card refresh.</dd>
</div>

<div>
<dt><code>include_contradicted</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Include unresolved contradictions.</dd>
</div>

</div>

**Example — open-ended query:**

```bash
curl -s -X POST http://localhost:8000/v1/recall \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "what is the current project status for phase 9?",
    "token_budget": 2000,
    "depth": 1
  }'
```

**Example — entity-centric query (card-first):**

```bash
curl -s "http://localhost:8000/v1/recall?entity=stigmem%3A%2F%2Fcompany.example%2Fagent%2Fcto&token_budget=1500" \
  -H 'Authorization: Bearer <api-key>'
```

---

### `GET /v1/cards/{entity_uri}`

Fetch (and optionally force-refresh) the synthesized memory card for a specific entity. Returns `404` when the entity has no live facts.

<div className="stigmem-keypoint">

**Memory cards are pre-aggregated summaries.**

Marked stale on every `assert_fact` call and refreshed on the next
read. When a fresh card is available during `POST /v1/recall`, the
recall pipeline uses it as a single synthetic fact instead of
re-ranking all raw facts for that entity.

</div>

**Path parameter:** `entity_uri` — URL-encoded entity URI.

**Query parameters:**

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">local</span></dt>
<dd>Scope the card was materialised from.</dd>
</div>

<div>
<dt><code>refresh</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Force a server-side refresh even if the card is already fresh.</dd>
</div>

</div>

**Auth:** read permission required.

```bash
# Fetch card (auto-refreshes if stale)
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local" \
  -H 'Authorization: Bearer <api-key>'

# Force refresh
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local&refresh=true" \
  -H 'Authorization: Bearer <api-key>'
```

**Error responses:**

<div className="stigmem-fields">

<div>
<dt>Status</dt>
<dt><span className="stigmem-fields__type">Code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type">validation</span></dt>
<dd>Invalid <code>scope</code> value or malformed <code>entity_uri</code>.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type">authorization</span></dt>
<dd>API key lacks read permission.</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type">lookup</span></dt>
<dd>No live facts exist for the entity.</dd>
</div>

</div>

---

### `GET /v1/graph/neighbors`

Returns the graph neighbors of one or more seed entities by traversing the materialized `entity_edges` adjacency index.

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Seed entity URI (repeat for multiple seeds).</dd>
</div>

<div>
<dt><code>depth</code></dt>
<dt><span className="stigmem-fields__type">1 (max 2)</span></dt>
<dd>Traversal depth.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Filter edges by relation label.</dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">0.1</span></dt>
<dd>Minimum edge confidence.</dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">50</span></dt>
<dd>Max edges returned per page.</dd>
</div>

<div>
<dt><code>cursor</code></dt>
<dt><span className="stigmem-fields__type">opaque</span></dt>
<dd>Pagination cursor (TTL <code>STIGMEM_CURSOR_TTL_S</code>, default 300s).</dd>
</div>

</div>

---

### `POST /v1/subscriptions`

Register a push subscription to receive events when facts matching a scope or entity change. Requires a capability token covering the `subscribe` verb on the target.

```bash
curl -s -X POST http://localhost:8000/v1/subscriptions \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "target": "stigmem://company.example/project/phase9",
    "target_type": "entity",
    "on_change": "webhook",
    "webhook_url": "https://your-agent.example/hook",
    "idempotency_key": "sub-phase9-agent-assistant"
  }'
```

Events are delivered with `subscription_id`, `event_type` (`fact_asserted` | `fact_retracted` | `conflict_opened` | `conflict_resolved`), `fact_id`, and `hlc`.

<div className="stigmem-keypoint">

**Delivery security: garden ACL + capability revocation re-checked on every event.**

Event content is not populated until the ACL check passes —
preventing cross-garden fact leakage via standing event streams. If
access has been revoked since subscription creation, delivery is
silently dropped and the subscription is cancelled with event type
`subscription_cancelled_access_revoked`.

</div>

---

### `GET /v1/facts/:id/provenance`

Walks the `derived_from` DAG for a given fact and returns the full derivation graph.

<div className="stigmem-keypoint">

**Cross-scope inference protection.**

Caller must have read access to the root fact's scope and
`garden_id`. Unauthorized root facts return HTTP 403. When resolving
`derived_from` references, facts in unauthorized scopes or gardens
are represented as `{"hash": "...", "exists": false}` — identical to
genuinely absent facts. The endpoint does not confirm or deny the
existence of facts the caller cannot access.

</div>

```bash
curl -s http://localhost:8000/v1/facts/abc123/provenance \
  -H 'Authorization: Bearer <api-key>'
```

---

## Lazy instruction discovery endpoints

### `PUT /v1/agents/{agent_id}/instruction-manifest`

Publish or replace the instruction manifest for an agent. The manifest is written with a versioned identifier so old manifests are superseded rather than overwritten in place.

**Auth:** `write` scope required.

```json
{
  "version": "v1-1746393600",
  "entries": [
    {
      "name": "deployment-checklist",
      "description": "Deployment Checklist",
      "fact_uri": "instruction:default/agent/{agent_id}/deployment-checklist/v1",
      "load_triggers": {
        "intents": ["deployment checklist"],
        "keywords": ["deploy", "checklist", "release"],
        "task_types": []
      },
      "token_estimate": 340
    }
  ],
  "skip_coverage_gate": false
}
```

---

### `POST /v1/agents/{agent_id}/recall-instruction`

Retrieve the most relevant instruction units for a given agent intent.

**Three-phase retrieval strategy:**

<ol className="stigmem-steps">
<li><strong>Hint resolution</strong> — explicit <code>manifest_hint</code> names are loaded first (highest priority).</li>
<li><strong>Ranked retrieval</strong> — remaining slots filled by BM25 scoring of <code>intent</code> against each unit's <code>description</code>, <code>load_triggers.intents</code>, and <code>keywords</code>.</li>
<li><strong>Guaranteed units</strong> — units with <code>guarantee_load: true</code> are always appended regardless of score; at most 5 per manifest.</li>
</ol>

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>intent</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Natural-language description of what the agent is about to do.</dd>
</div>

<div>
<dt><code>max_chunks</code></dt>
<dt><span className="stigmem-fields__type">3</span></dt>
<dd>Maximum instruction units to load (1–20).</dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">2000</span></dt>
<dd>Token limit across all returned chunks (1–100 000).</dd>
</div>

<div>
<dt><code>manifest_hint</code></dt>
<dt><span className="stigmem-fields__type">[]</span></dt>
<dd>Explicit unit names to prioritize by name.</dd>
</div>

</div>

```bash
curl -s -X POST \
  http://localhost:8000/v1/agents/a1b2c3d4-0000-0000-0000-000000000001/recall-instruction \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "how do I handle a production incident?",
    "max_chunks": 3,
    "token_budget": 2000
  }'
```

Response includes `chunks`, `total_tokens`, `truncated`, `missed_hints`, and an `audit_token` to submit to `POST /v1/instruction/audit`.

---

### CLI reference — `stigmem instruction migrate`

The `stigmem instruction migrate` command is the primary tool for publishing instruction files to a node.

```
stigmem instruction migrate PATH --role ROLE --agent-id UUID [options]
stigmem instruction migrate PATH --skill SKILL --agent-id UUID [options]
```

<div className="stigmem-fields">

<div>
<dt>Flag</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>PATH</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Markdown file or directory.</dd>
</div>

<div>
<dt><code>--role ROLE</code> / <code>--skill SKILL</code></dt>
<dt><span className="stigmem-fields__type">mutually exclusive</span></dt>
<dd>Scope selector.</dd>
</div>

<div>
<dt><code>--agent-id UUID</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Agent UUID owning the manifest.</dd>
</div>

<div>
<dt><code>--deployment NAME</code></dt>
<dt><span className="stigmem-fields__type">default</span></dt>
<dd>Deployment namespace.</dd>
</div>

<div>
<dt><code>--version VER</code></dt>
<dt><span className="stigmem-fields__type">v1</span></dt>
<dd>Fact version string.</dd>
</div>

<div>
<dt><code>--node-url URL</code></dt>
<dt><span className="stigmem-fields__type">localhost:8000</span></dt>
<dd>Node base URL.</dd>
</div>

<div>
<dt><code>--api-key KEY</code></dt>
<dt><span className="stigmem-fields__type">$STIGMEM_API_KEY</span></dt>
<dd>API key for writes.</dd>
</div>

<div>
<dt><code>--dry-run</code></dt>
<dt><span className="stigmem-fields__type">off</span></dt>
<dd>Print diff, exit without writing.</dd>
</div>

<div>
<dt><code>-y</code> / <code>--yes</code></dt>
<dt><span className="stigmem-fields__type">off</span></dt>
<dd>Skip confirmation prompt.</dd>
</div>

</div>

## Authentication

All endpoints except `/.well-known/stigmem` and `/healthz` require an API key. Pass it as a Bearer token:

```bash
curl -H 'Authorization: Bearer <your-key>' http://localhost:8000/v1/facts
```

Set `STIGMEM_AUTH_REQUIRED=false` to disable auth in development.

### OIDC / SSO

Human principals can obtain an API key via OIDC. Configure `STIGMEM_OIDC_*` env vars; the node validates the JWT and maps role claims to `admin|writer|reader`.

### Multi-tenant requests

Default installs resolve all API keys into the single `default` tenant. To use non-default tenants, install and enable `stigmem-plugin-multi-tenant`, then provision API keys with the target `tenant_id`.

Multi-tenant scoping is experimental in v0.9.0a10. It does not yet provide shared-node readiness, per-tenant quota/resource controls, or tenant-aware non-default federation.

### Federation peer tokens

Federation endpoints additionally require an Ed25519-signed JWT peer token exchanged during the federation handshake (`Spec-05-Federation-Trust`).

## Generating interactive docs

```bash
# Terminal 1 — start the reference node
cd stigmem/node
uv run python -m stigmem_node

# Terminal 2 — regenerate and serve docs
cd stigmem/docs
npm run gen-api-docs
npm run start
```

:::info
The API reference sidebar is populated by `npm run gen-api-docs`. Until that command has run, only this overview page appears.
:::
