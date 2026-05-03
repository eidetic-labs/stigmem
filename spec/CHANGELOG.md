# Stigmem Spec Changelog

All notable changes to the Stigmem protocol specification. Versions correspond to the files in this directory.

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

## [v0.9] — 2026-04 · Working draft (Phase 7 — substrate)

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

## [v0.8] — 2026-03 · Public beta (Phase 6)

**Promoted from:** v0.7

### New sections

- **§15 Decay Semantics** — `POST /v1/decay/sweep`, configurable TTL + confidence-decay policies, `DecayPolicy` registry, `decay_scope` MCP tool. `stigmem:decay:` prefix reserved.
- **§16 Synthesis** — `POST /v1/synthesis`, confidence-weighted snapshot API, `synthesize_scope` MCP tool.
- **§6.7 N-node Backpressure** — `X-Stigmem-Replication-Lag` header, HTTP 503 throttle for multi-hop relay topologies.
- **§6.8 Scope Propagation Invariants** — `company`-scoped facts MUST NOT be re-federated; closes open question §8.5.

### Promoted

- §§1–§14 all promoted to **stable**.

---

## [v0.7] — 2026-02 · Phase 5

### New sections

- **§14 Lint Semantics** — `POST /v1/lint`, four lint checks, MCP `lint_scope` tool, `LINT_VECTORS` conformance vectors. `stigmem:lint:` prefix reserved.
- **§2.6 Entity Naming Rules** — Strict normalizer on ingest; case normalization; migration 003.

---

## [v0.6] — 2026-01 · Phase 4

### New sections

- **§2.5 Entity URI scheme** — `stigmem://` formal scheme normative; informal URIs deprecated.
- **§12 Adapter ABI** — MCP, Paperclip, and OpenClaw adapter contracts normative.

### Extended sections

- **§6.2 Capability Negotiation** — Promoted from optional to required.

---

## [v0.5] — 2025-12 · Phase 3

### New sections

- **§6 Federation Protocol** — Two-node federation, HLC replication, Ed25519 peer tokens, normative.
- **§5.6–§5.10** — Federation wire routes (peer registration, handshake, pull, push, conflicts, audit).
- **§2.4 HLC Timestamps** — Hybrid Logical Clock required for federation causality ordering.
- **§11 Failure Mode Scenarios** — Split-brain, malicious peer, partial failure, replay attack acceptance tests.

### Extended sections

- **§3.3 Contradiction** — Formalized: `stigmem:conflict:*` facts + resolution API.
- **§3.5 Auth** — Per-scope key restrictions; Ed25519 federation peer tokens.

---

## [v0.4] — 2025-11 · Phase 2

### Extended sections

- **§3.5 Auth** — API keys promoted to normative.
- **§5.4** — `PATCH /v1/facts/:id/confidence` retraction.
- **§5.5** — `GET /v1/facts/:id` single-fact route.
- **§10 Database Schema** — Migration-friendly notes added; SQLite schema stable.

---

## [v0.3] — 2025-10 · Phase 1

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
