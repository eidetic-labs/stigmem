# Stigmem Spec Evolution

> **Renamed from `CHANGELOG.md` (2026-05-09).** This document records how the stigmem protocol specification evolved through development checkpoints (`v0.2` through `v2.0`) into the canonical v0.9.0a1 baseline.
>
> Per [ADR-001](../docs/adr/001-versioning.md): the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09); the version *markers* on earlier checkpoints labeled internal development steps, not tagged releases. The spec *content* under each marker was real protocol specification — reviewed section-by-section against actual implementation in `node/` and migrated forward into [`spec/stigmem-spec-v0.9.0a1.md`](stigmem-spec-v0.9.0a1.md) per master-checklist §4.3a.
>
> The evolutionary snapshots themselves are preserved at [`spec/archive/evolution/`](archive/evolution/) as reference material. Each retains a header banner pointing at the canonical v0.9.0a1 equivalent.
>
> This file (`EVOLUTION.md`) records the development-checkpoint history; the protocol-release-level changelog going forward is at [`CHANGELOG.md`](../CHANGELOG.md) (repo root).

## How the spec evolved through checkpoints

Each checkpoint below captured what the spec said at that step. Major themes that grew across checkpoints:

- **§1–§3** (motivation, atomic-fact-shape, fact-semantics): stable since v0.5; minor clarity improvements through v2.0.
- **§6 federation**: structure stable since v0.6; capability tokens (§19) added in v0.9 drafts; mTLS (§22.1) and audit log (§22.3) added in v1.0-rc.
- **§17 memory garden**: introduced in v0.9 drafts as concept; advanced ACL deferred per [ADR-002](../docs/adr/002-v1-scope.md) + [ADR-011](../docs/adr/011-cross-cutting-extraction.md) → `experimental/memory-garden-acl/spec.md`.
- **§19–§25**: introduced in v2.0 (retracted-label snapshot); deferred to `experimental/<feature>/spec.md` per ADR-002.

For per-section provenance, read the relevant snapshot at `spec/archive/evolution/`.

---

## Historical changelog (preserved verbatim from pre-rename `CHANGELOG.md`)

The version *markers* in entries below labeled internal development checkpoints, not tagged releases. The changes themselves were real spec evolution.

---

## [v1.1-draft] — 2026-05 · v1.0 graph & recall (Graph Memory & Recall) — DRAFT

**Promoted from:** v1.0

### New sections (§20 — draft normative)

- **§20.1 Graph Index** — materialized `entity_edges` table for O(edges) k-hop traversal; `GET /v1/graph/neighbors` route with depth cap (default 2), confidence/trust pruning, and opaque pagination cursor.
- **§20.2 Embedding Storage** — `vec_facts` virtual table (sqlite-vec); per-fact composition string `"{entity} {relation} {value}"`; default model `nomic-embed-text-v1.5` (768-dim, Apache-2.0, offline via Ollama); cloud opt-in via `STIGMEM_EMBED_PROVIDER=openai|voyage`; L2-normalized at insertion. `STIGMEM_EMBED_DIMENSIONS` tracks configured dimensionality; dimensionality change after indexing is a fatal error requiring re-index.
- **§20.3 Recall API** — `GET /POST /v1/recall`; three-stage hybrid pipeline (lexical BM25 + dense ANN + graph BFS); late-fusion formula with salience signals (recency, confidence, access frequency, contradiction penalty, garden tier, source-trust multiplier); token-budget packing via MMR (λ=0.7).
- **§20.4 Memory Cards** — per-entity synthesized summaries stored as `stigmem:memory:card` facts; refreshed on write/decay/age; stale card served with `card_stale: true`; hard cap 4000 tokens; exempt from decay sweeper. `STIGMEM_CARD_MAX_AGE_S` (default 86400).
- **§20.5 Subscriptions** — `POST/GET/DELETE /v1/subscriptions`; webhook and agent-wake delivery; `STIGMEM_SUBSCRIPTION_REPLAY_S` replay window (default 3600s); capability token required on creation (§19.5); per-event garden ACL re-evaluation prevents cross-garden leakage.
- **§20.6 Causal / Derivation Links** — `derived_from: [FactHash]` DAG on fact records; acyclicity enforced at write time; `GET /v1/facts/:id/provenance` provenance-walk route; derived-fact hashes included in recall responses.

### Extended sections

- **§2** — `derived_from` field added to `FactRecord` for causal lineage (complementing the v0.9 attestation_chain).
- **§5** — New routes §20.3 (`/v1/recall`), §20.1 (`/v1/graph/neighbors`), §20.5 (`/v1/subscriptions`), §20.6 (`/v1/facts/:id/provenance`).
- **§10 Database Schema** — migrations for `entity_edges`, `vec_facts`, `subscriptions`, `subscription_events`.

### New environment variables

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_EMBED_PROVIDER` | `ollama` | Embedding backend (`ollama`, `openai`, `voyage`) |
| `STIGMEM_EMBED_MODEL` | `nomic-embed-text` | Model name for the selected provider |
| `STIGMEM_EMBED_DIMENSIONS` | `768` | Embedding vector dimensions; changing after indexing requires re-index |
| `STIGMEM_CARD_MAX_AGE_S` | `86400` | Max age (seconds) before a memory card is invalidated |
| `STIGMEM_SUBSCRIPTION_REPLAY_S` | `3600` | Event replay window for subscriptions |
| `STIGMEM_CURSOR_TTL_S` | `300` | Pagination cursor TTL for `/v1/graph/neighbors` |

### Documentation updates (v1.0 graph & recall)

- `docs/docs/roadmap.md` — v1.0 graph & recall row updated; §20 draft noted.
- `docs/docs/api-reference/index.md` — Recall, Graph, Subscriptions, and Provenance endpoint groups added.
- `docs/docs/architecture/index.md` — Graph index and recall pipeline section added (three-stage pipeline, MMR, memory cards).
- `docs/docs/backends.md` — v1.0 graph & recall and embedding env vars table added.

### Status

§20 is **draft normative** — pending security review of subscription auth (§20.5.5) and cross-garden recall scoping. §1–§19 are normative and unchanged from v1.0 / v1.1-rev2.

---

## [v1.0] — 2026-05-03 · Stable

**Promoted from:** v0.9-draft

### Promoted to stable

- **§17 Memory Garden** — named ACL'd partitions above scope; admin/writer/reader role model; garden-tagged facts subject to ACL at read time; `garden:` prefix reserved in §9; `garden_id` on `FactRecord`. Previously draft in v0.9.
- **§18 Source Attestation** — `entity_uri` bound to API key at creation (immutable); enforcement at write time via `enforce|warn|off` modes; auto-fill `source` from key's `entity_uri`; delegation via `allowed_source_entities`; `attested` field on `FactRecord`. Previously draft in v0.9.
- **§5.14–§5.20** — Garden and attestation wire routes promoted to stable.
- **§2.7 Garden Field / `attested` semantics** — Both fields on `FactRecord` stable.
- **§15 Decay Semantics** / **§16 Synthesis** — Already promoted in v0.9; confirmed stable.

### Deferred

- **§4 Intent Envelope** — Deferred indefinitely. Not implemented; removed from active roadmap. Spec text retained as a non-normative appendix stub.

### Conformance

- v1.0 conformance vector suite published at `data/conformance/v1.0/`. Five vector groups cover: fact assert/query, `/.well-known/stigmem`, garden CRUD, and garden-tagged facts.
- CI gate (`conformance.yml`) runs on every push to `main` and on PRs touching `node/`, `spec/`, `data/conformance/`, or the workflow file. Zero skips enforced.
- All sections §1–§18 are normative and covered by conformance vectors or dedicated test modules.

### Migration

No new database migrations. v0.9 migrations 004 (gardens) and 005 (api_keys + attestation_audit) are the last before v1.0 stable.

---

## [v0.9] — 2026-04 · Working draft (v0.9 substrate)

**Promoted from:** v0.8

### New sections (draft at v0.9, stable at v1.0)

- **§17 Memory Garden** — Named, ACL'd partitions. Facts are tagged with `garden_id`; reads are ACL-gated by role. Garden membership is node-local; `garden_id` MUST NOT be replicated to peers.
- **§18 Source Attestation** — Three enforcement modes (`enforce|warn|off`). Key management API (`POST/GET/PATCH/DELETE /v1/auth/keys`). Attestation audit log. Default mode: `warn`.

### Extended sections

- **§2** — `garden_id: URI | null` and `attested: boolean | null` fields added to `FactRecord`.
- **§3.5 Identity and Auth** — Source attestation enforcement rules; `allowed_source_entities` on the `Identity` shape; `entity_uri` binding semantics.
- **§5** — New wire routes §5.14–§5.20: garden CRUD, garden membership, attestation audit log, key management.
- **§9 Namespace Registry** — `garden:` prefix reserved.
- **§10 Database Schema** — Migration 004 (gardens table) and migration 005 (api_keys extension + attestation_audit table).

---

## [v0.8] — 2026-03 · Public beta (v0.8)

**Promoted from:** v0.7

### New sections

- **§15 Decay Semantics** — `POST /v1/decay/sweep`, configurable TTL + confidence-decay policies, `DecayPolicy` registry, `decay_scope` MCP tool. `stigmem:decay:` prefix reserved.
- **§16 Synthesis** — `POST /v1/synthesis`, confidence-weighted snapshot API, `synthesize_scope` MCP tool.
- **§6.7 N-node Backpressure** — `X-Stigmem-Replication-Lag` header, HTTP 503 throttle for multi-hop relay topologies.
- **§6.8 Scope Propagation Invariants** — `company`-scoped facts MUST NOT be re-federated; closes open question §8.5.

### Promoted

- §§1–§14 all promoted to **stable**.

---

## [v0.7] — 2026-02 · the v0.7 design window

### New sections

- **§14 Lint Semantics** — `POST /v1/lint`, four lint checks, MCP `lint_scope` tool, `LINT_VECTORS` conformance vectors. `stigmem:lint:` prefix reserved.
- **§2.6 Entity Naming Rules** — Strict normalizer on ingest; case normalization; migration 003.

---

## [v0.6] — 2026-01 · the v0.6 design window

### New sections

- **§2.5 Entity URI scheme** — `stigmem://` formal scheme normative; informal URIs deprecated.
- **§12 Adapter ABI** — MCP, Paperclip, and OpenClaw adapter contracts normative.

### Extended sections

- **§6.2 Capability Negotiation** — Promoted from optional to required.

---

## [v0.5] — 2025-12 · the v0.5 design window

### New sections

- **§6 Federation Protocol** — Two-node federation, HLC replication, Ed25519 peer tokens, normative.
- **§5.6–§5.10** — Federation wire routes (peer registration, handshake, pull, push, conflicts, audit).
- **§2.4 HLC Timestamps** — Hybrid Logical Clock required for federation causality ordering.
- **§11 Failure Mode Scenarios** — Split-brain, malicious peer, partial failure, replay attack acceptance tests.

### Extended sections

- **§3.3 Contradiction** — Formalized: `stigmem:conflict:*` facts + resolution API.
- **§3.5 Auth** — Per-scope key restrictions; Ed25519 federation peer tokens.

---

## [v0.4] — 2025-11 · the v0.4 design window

### Extended sections

- **§3.5 Auth** — API keys promoted to normative.
- **§5.4** — `PATCH /v1/facts/:id/confidence` retraction.
- **§5.5** — `GET /v1/facts/:id` single-fact route.
- **§10 Database Schema** — Migration-friendly notes added; SQLite schema stable.

---

## [v0.3] — 2025-10 · the v0.3 design window

### Extended sections

- **§3.5 Auth** — Stub (API keys planned).
- **§6 Federation** — RFC stub; community feedback wanted.
- **§9 Namespace Registry** — `stigmem:channel` escalation fix.

---

## [v0.2] — 2025-09 · Initial release

### New

- Atomic fact shape: `(entity, relation, value, source, confidence, scope, timestamp, valid_until?)`.
- `text` FactValue type; size guidance.
- Reification pattern (`stigmem:rel:` prefix).
- `valid_until` decay field.
