---
id: index
title: Architecture
sidebar_label: Overview
description: Engineer-facing architecture reference — fact model, provenance, scope, federation, and repo map.
---

# Architecture

*Audience: engineers contributing to the node, implementing an adapter, or reading the spec alongside the code.*

---

## System overview

A Stigmem deployment is one or more **nodes** — self-contained FastAPI+SQLite processes — connected by the federation protocol. Clients assert and query facts via HTTP/JSON. Nodes peer with each other via a signed PeerDeclaration handshake and replicate facts across scope boundaries.

```mermaid
graph TB
    Agent["Agent / Application"]
    MCP["MCP Adapter\n(TypeScript)"]
    Node["Stigmem Node\n(FastAPI + SQLite)"]
    Peer["Peer Stigmem Node"]

    Agent -- "stigmem_assert / stigmem_query\n(MCP tools)" --> MCP
    MCP -- "POST /v1/facts\nGET /v1/facts" --> Node
    Agent -- "direct HTTP" --> Node

    subgraph internals["Node internals"]
        Auth["Auth layer\n(API key + scope, §3.5)"]
        HLC["Hybrid Logical Clock\n(§2.4)"]
        DB[("SQLite\nfacts + conflicts + peers")]
        Conflict["Conflict detector\n(§3.3)"]
        FedLoop["Federation pull loop\n(background, HLC cursor)"]
        Ingest["Idempotent ingest\n(§6.3)"]
    end

    Node --> Auth --> HLC --> DB --> Conflict
    Node --> FedLoop
    FedLoop -- "GET /v1/federation/facts\n(HLC cursor, scope filter)" --> Peer
    Peer -- "federation pull" --> Node
    FedLoop --> Ingest --> DB
```

---

## The fact model

Every piece of knowledge is an **atomic, immutable fact** (spec §2):

```
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

| Field | Type | Why it exists |
|-------|------|---------------|
| `entity` | URI (`stigmem://…` formal; informal deprecated in v0.6) | *What* the fact is about. Entity-scoped, not agent-scoped — the same entity URI is shared across all agents and nodes (spec §4.6 origin in `upstream-surfaces.md §4.6`). |
| `relation` | namespaced string (`memory:role`, `roadmap:status`, …) | *What kind* of statement this is. Namespaced to prevent collisions (spec §9 namespace registry). |
| `value` | `FactValue` union | The asserted value. See §2.1 for the full type lattice: `string`, `text`, `number`, `boolean`, `datetime`, `ref`, `null`. |
| `source` | URI | *Who* asserted the fact. Stored immutably; relayed facts carry the *originating* source, not the relay chain. |
| `timestamp` | ISO 8601 UTC | Wall-clock write time, set by the node (clients may suggest). |
| `hlc` | HLC string (`{wall_ms}.{counter}`) | Hybrid logical clock tick — causality-preserving across nodes. Required for federation ordering (§2.4). |
| `confidence` | float `[0.0, 1.0]` | Asserting party's certainty. `1.0` = certain, `0.0` = retracted. Used in contradiction resolution. |
| `scope` | `local \| team \| company \| public` | Visibility and federation boundary. Enforced at read and write time. |

Facts are **append-only**: there is no `PUT` or `DELETE`. Updating a value means asserting a new fact; the latest fact for a given `(entity, relation, scope)` triple wins by precedence rules.

---

## Provenance and decay

### Provenance (§3.1)

Every fact carries `source` and `timestamp`, stored without modification. Queries return the original `source`, never an intermediate relay. Federated facts additionally carry a `stigmem:received_from` meta-fact (generated automatically by the receiving node):

```json
{
  "entity":   "stigmem:fact:<uuid>",
  "relation": "stigmem:received_from",
  "value":    { "type": "ref", "v": "<originating-node-id>" },
  "source":   "system:stigmem"
}
```

This meta-fact is stored locally and never re-replicated.

### Decay (`valid_until`, §3.2)

Facts have an optional expiry: `valid_until: ISO 8601 | null`. Expired facts:
- Are **hidden** from normal queries (as if they don't exist).
- Are **retained** in the store (queryable with `include_expired=true`).
- Can also be set via a TTL meta-fact: `(entity=<fact-id>, relation="stigmem:ttl", value=<datetime>)`.

`valid_until` and `confidence` are **orthogonal**: a historical certain fact has `confidence=1.0` and `valid_until` set to when it was superseded by a newer value.

---

## Scope hierarchy and enforcement (§2.2, §3.4)

```
local   ─── node-only, never leaves this instance
team    ─── logical team boundary, node-operator-defined, never federated
company ─── owning company node; federated only when PeerDeclaration explicitly allows
public  ─── federatable to any registered peer by default
```

**Write-time enforcement:** A client presenting an API key with `allowed_scopes: ["local"]` cannot write a `public`-scoped fact.

**Read-time enforcement:** Cross-scope queries are additive — a query with no scope filter returns results from all scopes the caller's key allows.

**Federation enforcement:** Nodes MUST reject outbound replication of facts whose scope exceeds what the active PeerDeclaration permits. Nodes MUST reject inbound facts whose scope exceeds what the peer is authorized to write.

---

## Contradiction semantics (§3.3)

A contradiction exists when two facts share `(entity, relation, scope)` but have different values and both have `confidence > 0.0`. **Both facts are retained.** The node auto-generates:

```json
{
  "entity":   "stigmem:conflict:<uuid>",
  "relation": "stigmem:conflict:between",
  "value":    { "type": "text", "v": "<fact-id-a> <fact-id-b>" },
  "source":   "system:stigmem",
  "confidence": 1.0,
  "scope":    "<same as conflicting facts>"
}
```

Plus a `stigmem:conflict:status = "unresolved"` companion fact.

**Resolution order at query time:**
1. Higher `confidence` wins.
2. Equal confidence → higher `hlc` wins (causal ordering via §2.4).
3. Tie → both returned with `contradicted: true`; caller decides.

Resolution is explicit and traceable: `POST /v1/conflicts/:id/resolve` writes a new fact with the resolved value, updating conflict status to `"resolved"` with full provenance.

---

## Hybrid Logical Clock (§2.4)

Every node maintains a single HLC:

```
HLC = "{wall_ms_utc}.{counter}"    // e.g. "1746230400000.003"
```

**Advance rules:**
1. On local write: `hlc = max(now_ms, last_hlc_ms)` as wall; increment counter if wall unchanged.
2. On receiving a federated fact: `hlc = max(now_ms, received_hlc_ms)`; increment counter.

Causally ordered facts (`a.hlc < b.hlc`) are handled correctly across nodes. Equal HLCs on different nodes indicate concurrent writes; §3.3 contradiction policy applies. The HLC prevents the split-brain scenario where two nodes partition, accept divergent writes, and then disagree about ordering on reunion.

---

## Federation protocol (§6)

### Handshake (§6.1–6.2)

A **PeerDeclaration** is a signed JSON document declaring federation intent:

```json
{
  "declaring_node_id": "stigmem://node.alice.example",
  "target_node_id":    "stigmem://node.bob.example",
  "allowed_scopes":    ["public"],
  "direction":         "bidirectional",
  "signed_at":         "2026-05-01T00:00:00Z",
  "declaration_sig":   "<Ed25519 signature of canonical JSON of the above fields>"
}
```

The signature uses the declaring node's `federation_pubkey`, published at `/.well-known/stigmem`. Registration is mutual: both nodes must `POST /v1/federation/peers` with the declaration to activate the peering. Capability negotiation (§6.2) is required as of v0.6.

### Replication (§6.3)

Pull-based: each node's background `federation_pull` task runs periodically, fetching facts from registered peers:

```
GET /v1/federation/facts?since_hlc=<last-seen>&scope=public&limit=500
Authorization: Bearer <peer-token>
```

Peer tokens are short-lived Ed25519-signed JWTs (max 1-hour expiry, replay-protected by nonce). Fact ingestion is **idempotent**: re-asserting a fact that already exists is a no-op. The HLC cursor ensures replication resumes exactly where it left off across restarts.

### Failure modes (§11)

All four failure scenarios are automated in `node/tests/test_failure_modes.py`:

| Scenario | Behavior |
|----------|----------|
| Split-brain | Both nodes accept writes during partition; contradictions surface on reunion; no data loss |
| Malicious peer | Facts asserted in unauthorized scopes are rejected; audit log records the attempt |
| Partial failure | Surviving node stays read/write available; replication resumes from cursor on reconnect |
| Replay attack | Old signed messages are rejected via nonce + timestamp window |

---

## Auth model (§3.5)

Phase 2 implemented API-key auth; Phase 3 extended it with peer tokens for federation.

**API keys (clients):**
- Presented as `Authorization: Bearer <raw-key>` (or `X-API-Key: <key>` for compatibility).
- Node stores only the SHA-256 hex digest; the raw key is never retained.
- Each key maps to an `entity_uri`, a set of permissions (`read`, `write`, `federate`), and `allowed_scopes`.

**Peer tokens (federation):**
- Ed25519-signed JWTs, max 1-hour expiry.
- Signing keypair is separate from API keys; public half published at `/.well-known/stigmem`.
- Nonce cache prevents replay.

Auth mode is advertised at `/.well-known/stigmem` as `"auth": "none" | "required"`. Single-operator deployments MAY set `STIGMEM_AUTH_REQUIRED=false` (the default); all callers are trusted in that mode.

---

## Repo map

```
stigmem/
├── spec/                           ← canonical spec (v0.2 → v0.6-draft)
│   └── README.md                   ← spec status table
│
├── node/                           ← reference node (FastAPI + SQLite)
│   ├── stigmem_node/
│   │   ├── main.py                 ← FastAPI app factory, lifespan, router registration
│   │   ├── auth.py                 ← resolve_identity() dependency; API key validation
│   │   ├── db.py                   ← SQLite connection, schema migrations
│   │   ├── hlc.py                  ← node_hlc.tick() — global HLC (threading.Lock protected)
│   │   ├── federation_pull.py      ← background pull loop (HLC cursor, idempotent ingest)
│   │   ├── federation_ingest.py    ← idempotent fact ingestion; federation audit log
│   │   ├── peer_auth.py            ← PeerDeclaration verification, peer token generation
│   │   ├── peer_token.py           ← Ed25519 JWT sign/verify, nonce cache
│   │   └── routes/
│   │       ├── facts.py            ← POST/GET /v1/facts, conflict detection
│   │       ├── federation.py       ← /v1/federation/* , /v1/conflicts
│   │       └── wellknown.py        ← GET /.well-known/stigmem
│   ├── migrations/
│   │   ├── 001_init.sql            ← facts table
│   │   └── 002_federation.sql      ← peers, conflicts, audit tables
│   └── tests/                      ← 74 passing tests
│       ├── test_facts.py           ← fact CRUD, contradiction, scope enforcement
│       ├── test_federation.py      ← handshake, pull replication, scope leak attempts
│       └── test_failure_modes.py   ← §11 acceptance tests: split-brain, malicious peer, partial failure, replay
│
├── adapters/                       ← platform adapters (Phase 4, in flight)
│   ├── mcp/                        ← MCP server (TypeScript): stigmem_assert + stigmem_query tools
│   ├── openclaw/                   ← Claude Code / OpenClaw adapter (Python): PARA→fact mapping
│   └── paperclip/                  ← Paperclip hook adapter (JS): emits lifecycle events as facts
│
├── dogfood/                        ← CEO memory migration scripts
│   ├── migrate_ceo_memory.py       ← PARA memory → Stigmem fact migration
│   └── snapshot.sh                 ← snapshot current node state
│
└── docs/                           ← Docusaurus 3 documentation site
    └── docs/                       ← content
        ├── about/                  ← state-of-stigmem.md (this sprint)
        ├── getting-started/        ← quickstart
        ├── guides/                 ← how-to guides (asserting, querying, federation, conflict resolution)
        ├── architecture/           ← this document
        ├── spec/                   ← spec docs
        └── api-reference/          ← generated from OpenAPI schema
```

---

## Key implementation notes

**SQLite as Phase 2–4 storage.** The schema (spec §10) is migration-friendly by design: column additions do not require table rewrites. A PostgreSQL backend is feasible for Phase 5+ but not required before v1.0.

**HLC requires a threading lock.** The in-process HLC state is shared between the HTTP request path and the background federation pull task. Without `threading.Lock`, concurrent writes race and may produce out-of-order HLC values. Fixed in `hlc.py`; noted in the [Phase 3 exit memo](/ACM/issues/ACM-34).

**Idempotency + conflict edge case.** If fact F arrives from peer A and creates a conflict with local fact G, then F arrives again via replication, the second ingestion is a no-op — it must not create a second conflict record. `federation_ingest.py` handles this; the spec §6.3 needs a normative sentence covering this case before v0.5.1 is finalized.

**`declaration_sig` excluded from its own preimage.** The Ed25519 signature over a PeerDeclaration covers all fields *except* `declaration_sig` itself (which obviously does not exist at signing time). The spec §6.1 now enumerates excluded fields explicitly; `peer_auth.py` implements accordingly.

:::info Sequence diagrams coming
Federation handshake, conflict detection flow, and HLC tick protocol sequence diagrams are planned. Contributions welcome — see `CONTRIBUTING.md` at the repo root for the RFC process.
:::
