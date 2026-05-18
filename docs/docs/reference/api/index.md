---
id: index
title: API Reference
sidebar_label: API Reference
audience: Integrator
---

# API Reference

The Stigmem reference node exposes a REST API owned by `Spec-03-HTTP-API`, with endpoint semantics split across the component specs listed below. The interactive API reference below is auto-generated from the OpenAPI schema served at `http://localhost:8000/openapi.json`.

## Endpoint groups

| Group | Base path | Auth | Spec |
|-------|-----------|------|------|
| **Facts** | `/v1/facts` | API key | `Spec-01-Fact-Model`, `Spec-03-HTTP-API`, `Spec-15-Fact-Semantics` |
| **Federation** | `/v1/federation/*` | API key + peer token | `Spec-03-HTTP-API`, `Spec-05-Federation-Trust` |
| **Conflicts** | `/v1/conflicts` | API key | `Spec-03-HTTP-API`, `Spec-15-Fact-Semantics` |
| **Gardens** | `/v1/gardens/*` | API key (role-gated) | `Spec-02-Scopes-and-ACL`, `Spec-08-Quarantine-Garden` |
| **Lint** | `/v1/lint` | API key | `Spec-20-Lint-Semantics` |
| **Decay** | `/v1/decay/sweep` | API key | `Spec-X9-Decay-Semantics` |
| **Synthesis** | `/v1/synthesis` | API key | `Spec-X10-Synthesis` |
| **Auth / Keys** | `/v1/auth/keys/*` | Admin API key | `Spec-06-Capability-Tokens` |
| **Auth / Audit** | `/v1/auth/audit` | Admin API key | `Spec-X6-Source-Attestation` |
| **Admin / Billing** | `/v1/admin/billing/events` | Admin API key | — |
| **Async Jobs** | `/v1/jobs/:id` | API key | `Spec-20-Lint-Semantics`, `Spec-X9-Decay-Semantics` |
| **Identity** | `/v1/me` | API key | — |
| **Node Metadata** | `/.well-known/stigmem` | None | `Spec-03-HTTP-API`, `Spec-04-Manifests` |
| **Health** | `/healthz` | None | — |
| **Recall** | `/v1/recall` | API key | `Spec-07-Recall-Pipeline`, `Spec-X11-Recall-Graph` |
| **Cards** | `/v1/cards/*` | API key | `Spec-X11-Recall-Graph` |
| **Graph** | `/v1/graph/*` | API key | `Spec-X11-Recall-Graph` |
| **Subscriptions** | `/v1/subscriptions` | API key + capability token | `Spec-X7-Subscriptions` |
| **Provenance** | `/v1/facts/:id/provenance` | API key | `Spec-X11-Recall-Graph` |
| **Instructions** | `/v1/agents/:id/instruction-manifest` · `/v1/agents/:id/recall-instruction` | API key | `Spec-X1-Lazy-Instruction-Discovery` |

---

## Graph And Recall Design Endpoints (`Spec-07-Recall-Pipeline`, `Spec-X11-Recall-Graph`)

### `GET /v1/recall` · `POST /v1/recall`

Returns a token-budget-bounded, salience-ranked slice of the fact store relevant to a natural-language or structured query. Uses a three-stage hybrid pipeline: lexical (FTS5/BM25), dense vector (ANN via sqlite-vec), and graph expansion (BFS on `entity_edges`). Results are packed with Maximal Marginal Relevance (MMR) to avoid duplicates within the budget.

POST is preferred when `query` exceeds 1000 characters (avoids URI length limits). Both forms accept identical parameters.

**Key parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | — | Natural-language or structured query |
| `token_budget` | integer | Yes | — | Max response tokens (field labels excluded) |
| `depth` | integer | No | 1 | Graph expansion depth; max 2 |
| `weights` | object | No | `{lexical:0.30, vector:0.50, graph:0.20}` | Stage weights; must sum to 1.0 ±0.001 |
| `entity` | string | No | — | Entity URI; enables entity-centric (card-first) recall |
| `relation` | string | No | — | Relation filter; skips memory card lookup |
| `scope` | string | No | global | Garden or global scope |
| `lambda_mmr` | float | No | 0.7 | MMR diversity tradeoff; 1.0 = greedy by score |
| `min_confidence` | float | No | 0.1 | Minimum effective confidence for inclusion |
| `force_refresh` | boolean | No | false | Block on synchronous memory card refresh |
| `include_contradicted` | boolean | No | false | Include facts with unresolved contradictions |

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

**Response shape:**

```json
{
  "results": [
    {
      "id": "...",
      "entity": "stigmem://company.example/agent/cto",
      "relation": "memory:role",
      "value": { "type": "text", "v": "CTO" },
      "score": 0.92,
      "source_trust": 0.95,
      "contradicted": false,
      "derived_from": [],
      "provenance_of": null
    }
  ],
  "memory_card": {
    "entity": "stigmem://company.example/agent/cto",
    "value": "## CTO\n\n| Relation | Value | ... |\n...",
    "card_stale": false,
    "contradicted_count": 0
  },
  "token_budget_used": 312,
  "truncated": false
}
```

---

### `GET /v1/cards/{entity_uri}` {#get-v1cardsentity_uri}

Fetch (and optionally force-refresh) the synthesized memory card for a specific entity (`Spec-X11-Recall-Graph`). Returns `404` when the entity has no live facts.

Memory cards are pre-aggregated summaries stored in the `memory_cards` table. They are marked stale on every `assert_fact` call and refreshed on the next read. When a fresh card is available during `POST /v1/recall`, the recall pipeline uses it as a single synthetic fact instead of re-ranking all raw facts for that entity.

**Path parameter:**
- `entity_uri` — URL-encoded entity URI (e.g. `stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice`)

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | string | `"local"` | Scope the card was materialised from (`local`, `team`, `company`, `public`) |
| `refresh` | boolean | `false` | Force a server-side refresh even if the card is already fresh |

**Auth:** read permission required (`read` scope on the API key).

**Example:**

```bash
# Fetch card (auto-refreshes if stale)
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local" \
  -H 'Authorization: Bearer <api-key>'

# Force refresh
curl -s "http://localhost:8000/v1/cards/stigmem%3A%2F%2Fcompany.example%2Fuser%2Falice?scope=local&refresh=true" \
  -H 'Authorization: Bearer <api-key>'
```

**Response:**

```json
{
  "entity_uri": "stigmem://company.example/user/alice",
  "scope": "local",
  "summary": "Entity: stigmem://company.example/user/alice\nFacts:\n  memory:role: engineer (conf=1.00)\n  memory:team: platform (conf=0.95)",
  "fact_hashes": ["a1b2c3d4...", "e5f6a7b8..."],
  "avg_confidence": 0.975,
  "refreshed_at": "2026-05-04T11:30:00+00:00",
  "is_stale": false,
  "has_contradictions": false
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Invalid `scope` value or malformed `entity_uri` |
| 403 | API key lacks read permission |
| 404 | No live facts exist for the entity |

See the [Memory Cards guide](https://github.com/eidetic-labs/stigmem/tree/main/experimental/recall-graph) for the full lifecycle, schema, and Python SDK usage.

---

### `GET /v1/graph/neighbors`

Returns the graph neighbors of one or more seed entities by traversing the materialized `entity_edges` adjacency index.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity` | string | Yes | — | Seed entity URI (repeat for multiple seeds) |
| `depth` | integer | No | 1 | Traversal depth; max 2 |
| `relation` | string | No | — | Filter edges by relation label |
| `min_confidence` | float | No | 0.1 | Minimum edge confidence |
| `limit` | integer | No | 50 | Max edges returned per page |
| `cursor` | string | No | — | Opaque pagination cursor (TTL: `STIGMEM_CURSOR_TTL_S`, default 300s) |

**Example:**

```bash
curl -s "http://localhost:8000/v1/graph/neighbors?entity=stigmem%3A%2F%2Fcompany.example%2Fagent%2Fcto&depth=2" \
  -H 'Authorization: Bearer <api-key>'
```

---

### `POST /v1/subscriptions`

Register a push subscription to receive events when facts matching a scope or entity change. Requires a capability token (`Spec-06-Capability-Tokens`) covering the `subscribe` verb on the target.

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

**Delivery security:** the node re-evaluates the caller's garden ACL **and** capability token revocation status on every event delivery. Event content is not populated until the ACL check passes — preventing cross-garden fact leakage via standing event streams. If access has been revoked since subscription creation, delivery is silently dropped and the subscription is cancelled with event type `subscription_cancelled_access_revoked`.

---

### `GET /v1/facts/:id/provenance`

Walks the `derived_from` DAG for a given fact and returns the full derivation graph.

**Auth requirement:** the caller must have read access to the root fact's scope and `garden_id`. Unauthorized root facts return HTTP 403. When resolving `derived_from` references, facts in unauthorized scopes or gardens are represented as `{"hash": "...", "exists": false}` — identical to genuinely absent facts. The endpoint does not confirm or deny the existence of facts the caller cannot access.

```bash
curl -s http://localhost:8000/v1/facts/abc123/provenance \
  -H 'Authorization: Bearer <api-key>'
```

**Response:** array of `FactRecord` objects in topological order (root antecedents first), each annotated with `depth`, `is_root`, and `exists` fields. Unauthorized cross-scope references appear as `{"hash": "...", "exists": false}` entries.

---

## Lazy Instruction Discovery Endpoints (`Spec-X1-Lazy-Instruction-Discovery`)

### `PUT /v1/agents/{agent_id}/instruction-manifest`

Publish or replace the instruction manifest for an agent. The manifest is the index Stigmem uses to answer lazy `recall-instruction` requests — it lists each instruction unit with its load triggers, token estimate, and fact URI.

The manifest is written with a versioned identifier (`{version}-{timestamp}`) so old manifests are superseded rather than overwritten in place.

**Auth:** `write` scope required.

**Path parameter:**
- `agent_id` — UUID of the agent that owns the manifest.

**Request body:**

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

**Response:** `200 OK` on success; the stored manifest body with `created_at` and `superseded_at` timestamps.

Typically published automatically by `stigmem instruction migrate`. See the [Instruction Migration guide](https://github.com/eidetic-labs/stigmem/tree/main/experimental/lazy-instruction-discovery) for the full workflow.

---

### `POST /v1/agents/{agent_id}/recall-instruction`

Retrieve the most relevant instruction units for a given agent intent. Uses a three-phase retrieval strategy:

1. **Hint resolution** — explicit `manifest_hint` names are loaded first (highest priority).
2. **Ranked retrieval** — remaining slots are filled by BM25 scoring of `intent` against each unit's `description`, `load_triggers.intents`, and `keywords`.
3. **Guaranteed units** — units with `guarantee_load: true` are always appended regardless of score; at most 5 per manifest.

**Auth:** `read` scope required.

**Path parameter:**
- `agent_id` — UUID of the agent whose manifest to query.

**Request body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `intent` | string | Yes | — | Natural-language description of what the agent is about to do |
| `max_chunks` | integer | No | 3 | Maximum instruction units to load (1–20) |
| `token_budget` | integer | No | 2000 | Token limit across all returned chunks (1–100 000) |
| `manifest_hint` | array of strings | No | `[]` | Explicit unit names to prioritize by name |

**Example:**

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

**Response:**

```json
{
  "chunks": [
    {
      "name": "incident-response",
      "fact_uri": "instruction:default/agent/.../incident-response/v1",
      "content": "## Incident Response\n\nWhen a production incident...",
      "tokens": 210,
      "valid_until": null,
      "version": "v1",
      "score": 0.91,
      "source": "stigmem"
    }
  ],
  "total_tokens": 210,
  "truncated": false,
  "missed_hints": [],
  "audit_token": "aud_abc123"
}
```

| Field | Description |
|-------|-------------|
| `chunks` | Ranked instruction units within the token budget |
| `total_tokens` | Sum of token estimates across returned chunks |
| `truncated` | `true` if guaranteed units exceeded the token budget |
| `missed_hints` | `manifest_hint` names that were not found in the manifest |
| `audit_token` | Submit to `POST /v1/instruction/audit` to log which chunks were used |

See the [Instruction Migration guide](https://github.com/eidetic-labs/stigmem/tree/main/experimental/lazy-instruction-discovery) for the full dry-run → migrate → recall-instruction workflow.

---

### CLI reference — `stigmem instruction migrate`

The `stigmem instruction migrate` command is the primary tool for publishing instruction files to a node. It is a wrapper around the two endpoints above.

```
stigmem instruction migrate PATH --role ROLE --agent-id UUID [options]
stigmem instruction migrate PATH --skill SKILL --agent-id UUID [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `PATH` | — | Markdown file or directory |
| `--role ROLE` / `--skill SKILL` | — | Scope selector (mutually exclusive) |
| `--agent-id UUID` | — | Agent UUID owning the manifest |
| `--deployment NAME` | `default` | Deployment namespace |
| `--version VER` | `v1` | Fact version string |
| `--node-url URL` | `http://127.0.0.1:8000` | Node base URL |
| `--api-key KEY` | `$STIGMEM_API_KEY` | API key for writes |
| `--db PATH` | — | Local SQLite file for fast idempotency checks |
| `--dry-run` | — | Print diff, exit without writing |
| `-y` / `--yes` | — | Skip confirmation prompt |

Full documentation, idempotency semantics, and the tombstone lifecycle are in the [Instruction Migration guide](https://github.com/eidetic-labs/stigmem/tree/main/experimental/lazy-instruction-discovery).

## Authentication

All endpoints except `/.well-known/stigmem` and `/healthz` require an API key. Pass it as a Bearer token:

```bash
curl -H 'Authorization: Bearer <your-key>' http://localhost:8000/v1/facts
```

Set `STIGMEM_AUTH_REQUIRED=false` to disable auth in development.

### OIDC / SSO

Human principals can obtain an API key via OIDC. Configure `STIGMEM_OIDC_*` env vars; the node validates the JWT and maps role claims to `admin|writer|reader`. See [OIDC / SSO Integration](https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso).

### Multi-tenant requests

Default installs resolve all API keys into the single `default` tenant. To use
non-default tenants, install and enable `stigmem-plugin-multi-tenant`, then
provision API keys with the target `tenant_id`. Requests are scoped by the
resolved key identity:

```bash
curl -H 'Authorization: Bearer <your-key>' \
     http://localhost:8000/v1/facts
```

See [Multi-Tenant Scoping](https://github.com/eidetic-labs/stigmem/tree/main/experimental/multi-tenant).

### Federation peer tokens

Federation endpoints (`/v1/federation/facts`, `/v1/federation/facts/push`) additionally require a peer token:

```
Authorization: Bearer <peer-token>
```

Peer tokens are Ed25519-signed JWTs exchanged during the federation handshake (`Spec-05-Federation-Trust`).

## Generating interactive docs

The interactive try-it-out panels are generated from the live OpenAPI schema:

```bash
# Terminal 1 — start the reference node
cd stigmem/node
uv run python -m stigmem_node

# Terminal 2 — regenerate and serve docs
cd stigmem/docs
npm run gen-api-docs
npm run start
```

After regenerating, the sidebar shows individual endpoint pages with live request panels.

:::info
The API reference sidebar is populated by `npm run gen-api-docs`. Until that command has run, only this overview page appears.
:::
