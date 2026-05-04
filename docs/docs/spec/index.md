---
id: index
title: Specification
sidebar_label: Overview
---

# Stigmem Protocol Specification

:::note Version
These docs track **Stigmem spec v1.1-draft rev 11** (§22 DRAFT normative, Phase 12; §21 DRAFT normative, Phase 10), **v1.1-draft** (§19–§20 normative), and **v1.0** (§1–§18 stable). See the [v0.2 docs](/docs/v0.2/spec) for the prior stable release.

§22 Security Hardening was introduced in **v1.1-draft rev 11** (Phase 12) and is DRAFT normative; it will be promoted to normative in v2.0. §21 Lazy Instruction Discovery was introduced in **v1.1-draft rev 6** (Phase 10) and is DRAFT normative. §19 Federation Trust and §20 Recall & Graph were promoted to normative in v1.1. §1–§18 are unchanged from v1.0.
:::

The Stigmem specification defines the wire format, fact semantics, and federation protocol for the Stigmem knowledge graph. The authoritative sources are `spec/stigmem-spec-v1.0.md` (§1–§18), and `spec/stigmem-spec-v1.1-draft.md` (§19–§22 + v1.1 additions to §2 and §5; §21 added in rev 6; §22 added in rev 11) in the repository.

:::info Security
Report vulnerabilities via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories) — not as public issues. Full policy and coordinated disclosure terms: [SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md).
:::

## Spec sections

| Section | Topic | Status |
|---------|-------|--------|
| §1 | Motivation | Stable (v1.0) |
| §2 | Atomic Fact Shape | Stable (v1.0) |
| §2.1 | FactValue types | Stable (v1.0) |
| §2.2 | FactScope | Stable (v1.0) |
| §2.3 | Reification | Stable (v1.0) |
| §2.4 | Hybrid Logical Clock | Stable (new in v0.5) |
| §2.8 | Federation Trust Fields (`derived_from`, `attestation_chain`, `source_trust`) | **Normative (new in v1.1)** — [Federation Trust guide](/docs/guides/federation-trust) |
| §3 | Fact Semantics | Stable (v1.0) |
| §4 | Intent Envelope | Stable (v1.0) |
| §5 | Wire Format | Stable (v1.0) |
| §5.21–5.25 | Federation Trust wire routes (manifest, capability token, quarantine) | **Normative (new in v1.1)** — [Federation Trust guide](/docs/guides/federation-trust) |
| §6 | Federation | Stable (extended v0.8 for N-node backpressure) |
| §6.7 | N-node Backpressure Patterns | Draft (new in v0.8) — [guide](/docs/guides/relay-backpressure) |
| §6.8 | Scope Propagation Invariants | Normative (new in v0.8) — [guide](/docs/guides/scope-propagation) |
| §7 | Design Decisions | Stable (v1.0) |
| §8 | Open Questions | Living |
| §9 | Namespace Registry | Stable (v1.0) |
| §10 | Schema and Migration | Stable — migration 012 adds `tenant_id`; migration 006 adds federation trust tables (v1.1) ([multi-tenant guide](/docs/guides/multi-tenancy)) |
| §11 | Failure Mode Scenarios | Stable (new in v0.5) |
| §12 | Adapter ABI | Stable (new in v0.6) |
| §14 | Lint Semantics | Stable (new in v0.7) |
| §15 | Decay Semantics | Stable (promoted v0.9) — [guide](/docs/guides/decay) |
| §16 | Synthesis | Stable (promoted v0.9) — [guide](/docs/guides/synthesis) |
| §17 | Memory Garden | Stable (normative in v1.0) |
| §18 | Source Attestation | Stable (normative in v1.0) |
| §19 | Federation Trust | **Normative (v1.1)** — [guide](/docs/guides/federation-trust); Security Policy moved to Appendix A |
| §20 | Recall & Graph | **Normative (v1.1, Phase 9)** — see §20.1–§20.6 below |
| §20.1 | Graph Adjacency Index (`entity_edges`, k-hop traversal) | **Normative (v1.1)** — [API reference](/docs/api-reference) |
| §20.2 | Vector Embeddings (model selection, `vec_facts`, text composition, decay) | **Normative (v1.1)** — [Embeddings guide](/docs/guides/embeddings) |
| §20.3 | Recall API (`GET/POST /v1/recall`; lexical + dense + graph; MMR packing; token budget) | **Normative (v1.1)** — [Recall guide](/docs/guides/recall), [API reference](/docs/api-reference) |
| §20.4 | Memory Cards (`stigmem:memory:card` facts; refresh policy; stale-on-write) | **Normative (v1.1)** — [Recall guide](/docs/guides/recall) |
| §20.5 | Subscriptions (`POST /v1/subscriptions`; webhook + wake; ACL re-check at delivery) | **Normative (v1.1)** — [Subscriptions guide](/docs/guides/subscriptions), [API reference](/docs/api-reference) |
| §20.6 | Causal Links & Provenance (`derived_from`; `GET /v1/facts/:id/provenance`) | **Normative (v1.1)** — [API reference](/docs/api-reference) |
| §21 | Lazy Instruction Discovery | **DRAFT normative (v1.1-draft rev 6, Phase 10)** — [Lazy Instructions guide](/docs/guides/lazy-instructions) |
| §21.1 | Boot stub format (`stub_version`, `migration_mode`, `manifest_path`, `max_chunks`, `recall_tool`, `identity_summary`) | **DRAFT normative (v1.1-draft rev 6)** — [Lazy Instructions guide — Boot stub](/docs/guides/lazy-instructions#boot-stub-format) |
| §21.2 | Instruction manifest schema (chunk, `load_triggers`, `tokens`, `guarantee_load`) | **DRAFT normative (v1.1-draft rev 6; `guarantee_load` added rev 9)** — [Lazy Instructions guide — Manifest](/docs/guides/lazy-instructions#instruction-manifest-schema) |
| §21.3 | `recall_instruction` skill — wraps `/v1/agents/{id}/recall-instruction` against `instruction:` scope; `guarantee_load` units | **DRAFT normative (v1.1-draft rev 6)** — [Instruction Migration guide](/docs/guides/instruction-migration) |
| §21.4 | `instruction:` scope semantics — versioning, provenance, garden isolation, cross-agent confidentiality | **DRAFT normative (v1.1-draft rev 6; SE-reviewed rev 10)** — [Lazy Instructions guide — Confidentiality](/docs/guides/lazy-instructions#instruction-scope-confidentiality) |
| §21.5 | Discovery audit — Recall@k, Hit@k, miss rate, probe-set eval (§21.5.4) | **DRAFT normative (v1.1-draft rev 6; RS-reviewed rev 9)** — [Tutorial: Authoring Lazy-Discovery Instructions](/docs/tutorials/authoring-lazy-discovery-instructions) |
| §21.6 | Migration semantics — 5-stage deprecation path, tombstone, backward compatibility | **DRAFT normative (v1.1-draft rev 6)** — [Instruction Migration guide](/docs/guides/instruction-migration) |
| §22 | Security Hardening | **DRAFT normative (v1.1-draft rev 11, Phase 12)** |
| §22.1 | mTLS federation transport (TLS 1.3 floor, cipher suite, cert rotation hook into §19 manifest) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.2 | Key rotation (rollover window, dual-trust period, transparency-log entry, SHOULD cadence) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.3 | Audit log surface (13 required event types, write-ahead ordering, 90-day retention, admin export) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.4 | Per-principal quotas (token-bucket, 7 default dimensions, 429 backpressure shape) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.5 | Replay protection (±5 min clock-skew, persistent nonce cache, 5 error codes) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.6 | Container baseline (distroless, non-root UID 1000, read-only-fs, seccomp, Cosign signing) | **DRAFT normative (v1.1-draft rev 11)** |
| §22.7 | Transparency log own-instance decision memo (5-criterion gate; reference deployment defers self-hosted Rekor) | **DRAFT normative (v1.1-draft rev 11)** |

## Key concepts

### Atomic fact shape (§2)

Every fact is a tuple:

```
(entity, relation, value, source, confidence, scope, hlc, timestamp, valid_until?)
```

- **entity** — URI for the subject (e.g. `user:alice`, `stigmem:rel:<uuid>`)
- **relation** — relation URI from the namespace registry (e.g. `memory:prefers`, §9)
- **value** — one of: string, number, boolean, null, text, datetime, ref (§2.1)
- **source** — agent or system that asserted the fact (provenance, §3)
- **confidence** — 0–1 score; confidence=0 is a retraction (§3)
- **scope** — `local | team | company | public` (§2.2); controls federation eligibility
- **hlc** — Hybrid Logical Clock tick for global ordering (§2.4)
- **valid_until** — optional expiry; expired facts excluded from queries by default (§3)

### Hybrid Logical Clock (§2.4)

New in v0.5. Each node maintains an HLC that combines wall-clock time with a monotonic sequence number and a node-ID suffix. Format: `<wall_ms>-<seq>-<node_prefix>`. The HLC ensures total ordering of facts across federated nodes even under clock skew.

### Federation (§6)

Nodes form a peer mesh via the [federation handshake](/docs/guides). Each peer registers with an Ed25519 declaration signature. Replication is pull-based by default: nodes periodically pull from peers using scoped, cursor-paginated requests authenticated with short-lived peer tokens. Conflicts (contradicting facts from different nodes) are stored as first-class records — see the [Conflicts guide](/docs/guides) for resolution strategies.

### Phase 6 operational tools (§15–16)

v0.8 adds three tools for managing fact health over time. They form a pipeline:

| Tool | Spec | Question answered | Guide |
|---|---|---|---|
| `lint_scope` | §14 | "What is wrong with this scope?" | [Lint guide](/docs/guides/) |
| `decay_scope` | §15 | "Apply configured decay policies" | [Decay guide](/docs/guides/decay) |
| `synthesize_scope` | §16 | "What do I currently know?" | [Synthesis guide](/docs/guides/synthesis) |

§15 and §16 were promoted to **stable** in v0.9.

### N-node federation (§6.7–6.8)

v0.8 adds two new subsections to the federation spec:

- **§6.7 N-node Backpressure** — relay lag signals (`X-Stigmem-Replication-Lag` header, HTTP 503 throttle) for multi-hop topologies. See the [relay backpressure guide](/docs/guides/relay-backpressure).
- **§6.8 Scope Propagation Invariants** — closes v0.7 open question §8.5: `company`-scoped facts MUST NOT be re-federated. See the [scope propagation guide](/docs/guides/scope-propagation).

## Reference node extensions (not yet in spec)

The following reference node features are implemented and tested but do not yet have a formal spec section. They will be folded into a future spec revision.

| Feature | Guide | Status |
|---|---|---|
| Multi-tenant scoping (`tenant_id` on all write tables, migration 012) | [Multi-Tenant Scoping](/docs/guides/multi-tenancy) | Stable (reference node v1.0-rc) |
| Billing hook bus (`HookBus` / `CaptureBus`) | [Billing Hooks](/docs/guides/billing-hooks) | Stable (reference node v1.0-rc) |

:::info Coming soon
Per-section spec reference pages with full wire format examples are planned for the next docs sprint.
:::
