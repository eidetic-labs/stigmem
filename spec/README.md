# Stigmem Spec — Status Table

This directory contains the canonical specification for the Stigmem federated knowledge protocol.

| File | Version | Status | Key additions vs prior |
|------|---------|--------|------------------------|
| [`stigmem-spec-v0.2.md`](stigmem-spec-v0.2.md) | v0.2 | Stable baseline | `text` FactValue type, reification pattern, `valid_until` field |
| [`stigmem-spec-v0.3-draft.md`](stigmem-spec-v0.3-draft.md) | v0.3 | Stable | Auth stub (§3.5), namespace registry plan (§9), federation as community-feedback stub (§6), `stigmem:channel` escalation fix |
| [`stigmem-spec-v0.4-draft.md`](stigmem-spec-v0.4-draft.md) | v0.4 | Stable | Auth promoted to implemented (§3.5), `PATCH /v1/facts/:id/confidence` retraction (§5.4), `GET /v1/facts/:id` single-fact route (§5.5), `text` size guidance, migration-friendliness note on schema (§10) |
| [`stigmem-spec-v0.5-draft.md`](stigmem-spec-v0.5-draft.md) | v0.5 | Stable | §6 Federation promoted to normative concrete spec, new federation wire routes (§5.6–5.10), HLC timestamps (§2.4), per-scope key restrictions (§3.5), conflict-first-class semantics formalized (§3.3), §11 Failure Modes acceptance scenarios |
| [`stigmem-spec-v0.6-draft.md`](stigmem-spec-v0.6-draft.md) | v0.6 | Stable | §2.5 Entity URI scheme (`stigmem://`) normative, §6.2 capability negotiation now required, §12 Adapter ABI normative (MCP, Paperclip, OpenClaw), §13 reserved for Phase 5+ |
| [`stigmem-spec-v0.7-draft.md`](stigmem-spec-v0.7-draft.md) | v0.7 | Stable | §14 Lint Semantics normative (`POST /v1/lint`, MCP `lint_scope`, `LINT_VECTORS`); §2.6 Entity Naming Rules normative; `stigmem:lint:` prefix reserved; §6 promoted v0.6 → stable |
| [`stigmem-spec-v0.8-draft.md`](stigmem-spec-v0.8-draft.md) | v0.8 | Stable | §15 Decay Semantics (`POST /v1/decay/sweep`, `DecayPolicy` registry, `decay_scope` MCP tool); §16 Synthesis (`POST /v1/synthesis`, `synthesize_scope` MCP tool); §6.7 N-node federation backpressure; §6.8 scope propagation invariants; §1–14 promoted to stable; `stigmem:decay:` prefix reserved |
| [`stigmem-spec-v0.9-draft.md`](stigmem-spec-v0.9-draft.md) | v0.9 | Working draft | §17 Memory Garden primitive (named ACL'd partitions, admin/writer/reader roles, garden-tagged facts); §18 Source Attestation (`entity_uri` bound to API key, enforce/warn/off modes); §5.14–§5.20 garden + attestation wire routes; §2 `garden_id` and `attested` fields on FactRecord; `garden:` prefix reserved |

---

## Section status by version

| Section | v0.2 | v0.3 | v0.4 | v0.5 | v0.6 | v0.7 | v0.8 | Notes |
|---------|------|------|------|------|------|------|------|-------|
| §1 Motivation | Stable | Stable | Stable | Stable | Stable | Stable | Stable | Unchanged since v0.2 |
| §2 Atomic Fact Shape | Stable | Stable | Stable | Stable | Stable | Stable | Stable | `hlc` field added v0.5 |
| §2.1 FactValue | Stable | Stable | Stable | Stable | Stable | Stable | Stable | `text` size guidance added v0.4 |
| §2.2 FactScope | Stable | Stable | Stable | Stable | Stable | Stable | Stable | Federation enforcement clarified v0.5 |
| §2.3 Reification | Stable | Stable | Stable | Stable | Stable | Stable | Stable | |
| §2.4 HLC Timestamps | — | — | — | **New (normative)** | Stable | Stable | Stable | Required for federation causality |
| §2.5 Entity URI scheme | — | — | — | — | **New (normative)** | Stable | Stable | `stigmem://` formal scheme; informal URIs deprecated |
| §2.6 Entity Naming Rules | — | — | — | — | — | **New (normative)** | Stable | Strict normalizer on ingest; case normalization; migration 003 |
| §3.1 Provenance | Stable | Stable | Stable | Stable | Stable | Stable | Stable | Federated provenance meta-fact added v0.5 |
| §3.2 Decay / `valid_until` | Stable | Stable | Stable | Stable | Stable | Stable | Stable | |
| §3.3 Contradiction | Draft | Draft | Stable | **Formalized (normative)** | Stable | Stable | Stable | `stigmem:conflict:*` facts + resolution API formalized v0.5 |
| §3.4 Scope Enforcement | Stable | Stable | Stable | Stable | Stable | Stable | Stable | Federation enforcement added v0.5 |
| §3.5 Auth / Identity | — | Stub | **Implemented (normative)** | Extended (peer tokens) | Stable | Stable | Stable | Phase 2: API keys. Phase 3: Ed25519 peer tokens |
| §4 Intent Envelope | Draft | Draft | Draft | Draft | Draft | Draft | Draft | Community feedback wanted; not yet implemented |
| §5 HTTP Wire Format (§5.1–5.5) | — | Stable | Stable | Stable | Stable | Stable | Stable | Core CRUD + retraction + single-fact GET |
| §5.6–5.10 Federation Wire Routes | — | — | — | **New (normative)** | Stable | Stable | Stable | Peer registration, handshake, pull, push, conflicts, audit |
| §6 Federation Protocol | — | Stub | RFC stub | **Normative** | Stable | Stable | Stable | Two-node federation, HLC replication, Ed25519 peer tokens |
| §6.2 Capability Negotiation | — | — | Optional | Optional | **Required** | Required | Required | Promoted to required in v0.6 |
| §6.7 N-node Backpressure | — | — | — | — | — | — | **New (draft)** | Relay lag signals, HTTP 503 throttle for multi-hop topologies |
| §6.8 Scope Propagation Invariants | — | — | — | — | — | — | **New (normative)** | `company`-scoped facts MUST NOT be re-federated (closes §8.5) |
| §7 Client SDKs | — | — | — | Referenced | Referenced | Referenced | Referenced | Python + TypeScript SDKs; not spec-normative |
| §8 Implementation Gaps | — | — | Informative | Informative | Informative | Informative | Informative | Captured during Phase 2; three v0.5.1 errata items from Phase 3 |
| §9 Namespace Registry | — | Stable | Stable | Stable | Stable | Stable | Stable | `stigmem:`, `rel:`, `memory:` governance |
| §10 Database Schema | — | — | Stable | Stable | Stable | Stable | Stable | Migration-friendly SQLite schema |
| §11 Failure Modes | — | — | — | **New (normative)** | Stable | Stable | Stable | Split-brain, malicious peer, partial failure, replay attack |
| §12 Adapter ABI | — | — | — | — | **New (normative)** | Stable | Stable | MCP, Paperclip, OpenClaw adapter contracts |
| §13 Phase 5+ Reserved | — | — | — | — | Updated | Updated | Updated | Lint + entity normalization addressed; remainder deferred to Phase 6+ |
| §14 Lint Semantics | — | — | — | — | — | **New (normative)** | Stable | `POST /v1/lint`; four checks; MCP `lint_scope`; `LINT_VECTORS` conformance vectors |
| §15 Decay Semantics | — | — | — | — | — | — | **New (draft)** | `POST /v1/decay/sweep`; configurable TTL + confidence-decay policies |
| §16 Synthesis | — | — | — | — | — | — | **New (draft)** | `POST /v1/synthesis`; `synthesize_scope` MCP tool; confidence-weighted snapshots |

---

## What "stable" means here

A section marked **Stable** has a shipped implementation in `stigmem/node/` that passes the test suite. Changes to stable sections require a spec PR with CTO review and a corresponding test update.

A section marked **Draft** has partial or no implementation. Breaking changes are permitted without a version increment until the section is promoted to Stable.

A section marked **RFC stub** or **Community feedback wanted** has spec text but no implementation. Comments and PRs are open.

---

## Current working draft

The active development version is **v0.9-draft**. Sections §1–16 are stable (§15 and §16 promoted from draft in v0.9). §17 (Memory Garden) and §18 (Source Attestation) are new in v0.9. §4 (Intent Envelope) remains draft.

**Phase 7 additions (v0.9):**
- §17 Memory Garden — named ACL'd partitions (`garden_id`), admin/writer/reader roles, garden-tagged facts; `garden:` prefix reserved
- §18 Source Attestation — `entity_uri` bound to API key, enforce/warn/off modes; `attested` field on FactRecord
- §5.14–§5.20 garden + attestation wire routes
- §2 extended: `garden_id` and `attested` fields on FactRecord

**Phase 6 additions (v0.8):**
- §15 Decay Semantics — configurable TTL + confidence-decay policies, `POST /v1/decay/sweep`, `DecayPolicy` registry
- §16 Synthesis — confidence-weighted snapshot API, `POST /v1/synthesis`, `synthesize_scope` MCP tool
- §6.7 N-node federation backpressure — cascade behavior in relay nodes, 4-node topology
- §6.8 Scope propagation invariants — transitive escalation prevention, re-federation restrictions

**Phase 3 errata resolved in Phase 4:**
1. §6 signing spec now enumerates excluded fields (the `declaration_sig` exclusion from its own preimage)
2. §6.3 idempotency + conflict: re-ingestion of an existing-conflict fact is a no-op
3. §2.4 threading note added for concurrent HLC implementors

*Source: Phase 3 exit memo.*
