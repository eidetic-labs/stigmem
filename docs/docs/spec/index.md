---
title: Specification
sidebar_label: Overview
audience: Spec
description: Stigmem protocol specification — section navigator for v2.0.
sidebar_position: 6
---

# Stigmem Protocol Specification

:::note Authoritative source
Spec source markdown lives in [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md) and [`spec/stigmem-spec-v1.1-draft.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.1-draft.md). Each section below renders the source text inline.
:::

:::info Security disclosure
Report vulnerabilities via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories) — not as public issues.
:::

## Sections

| Section | Status | Summary |
|---------|--------|---------|
| [§1. Motivation](./motivation) | Stable (v1.0) | Why immutable typed facts beat per-agent mutable stores. |
| [§2. Atomic Fact Shape](./atomic-fact-shape) | Stable (v1.0; v1.1 §2.8) | The fact tuple, value types, scopes, HLC, identity, federation-trust fields. |
| [§3. Fact Semantics](./fact-semantics) | Stable (v1.0) | Read/write semantics, retraction, contradiction, identity binding. |
| [§4. Intent Envelope](./intent-envelope) | Stable (v1.0) | Goal/constraint/preference/handoff envelope types. |
| [§5. Wire Format](./wire-format) | Stable (v1.0; v1.1 §5.21–5.25) | JSON/HTTP wire format for facts, peers, gardens, trust manifests, and capability tokens. |
| [§6. Federation](./federation) | Stable (v0.8 N-node) | Peer handshake, pull replication, scope enforcement, conflict semantics, backpressure. |
| [§7. Design Decisions Log](./design-decisions-log) | Stable | Why the spec made the calls it did. |
| [§8. Open Questions](./open-questions) | Living | Currently-unresolved questions. |
| [§9. Namespace Registry](./namespace-registry) | Stable | Reserved relation prefixes and community registry process. |
| [§10. Schema and Migration](./schema-and-migration) | Stable | SQL schema migrations 001-013. |
| [§11. Failure Mode Scenarios](./failure-mode-scenarios) | Stable | Acceptance test scenarios — split-brain, malicious peer, partial failure, replay attack. |
| [§12. Adapter ABI](./adapter-abi) | Stable | Minimum contract for platform adapters. |
| [§14. Lint Semantics](./lint-semantics) | Stable | POST /v1/lint — orphan relations, scope-escalation violations. |
| [§15. Decay Semantics](./decay-semantics) | Stable | Configurable TTL and confidence-decay policies. |
| [§16. Synthesis](./synthesis) | Stable | POST /v1/synthesis — confidence-weighted current-state snapshots. |
| [§17. Memory Garden](./memory-garden) | Normative (v1.0) | Named, ACL'd partitions of the fact store. |
| [§18. Source Attestation](./source-attestation) | Normative (v1.0) | API-key → entity_uri binding. |
| [§19. Federation Trust](./federation-trust) | Normative (v1.1) | Org manifests, capability tokens, source-trust score, quarantine. |
| [§20. Recall & Graph](./recall-graph) | Normative (v1.1) | Graph adjacency index, vector embeddings, hybrid recall pipeline. |
| [§21. Lazy Instruction Discovery](./lazy-instruction-discovery) | DRAFT normative | Boot stub + manifest + on-demand recall. |
| [§22. Security Hardening](./security-hardening) | DRAFT normative | mTLS federation, key rotation, audit log, per-principal quotas. |
| [§23. Right-to-be-Forgotten Tombstones](./right-to-be-forgotten-tombstones) | DRAFT normative | Cryptographic tombstones, recall-time suppression. |
| [§24. Time-Travel / As-Of Queries](./time-travel-as-of-queries) | DRAFT normative | as_of parameter on /v1/recall and /v1/facts. |
| [§25. Content-Addressed Fact IDs](./content-addressed-fact-ids) | DRAFT normative | SHA-256 CIDs for deduplication and tamper detection. |

## Archive

Previous spec versions are available via the version dropdown (v1.1, v0.2).
