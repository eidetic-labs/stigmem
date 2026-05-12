---
title: Specification
sidebar_label: Overview
audience: Spec
description: Stigmem protocol specification — section navigator for v0.9.0a1.
sidebar_position: 6
---

# Stigmem Protocol Specification

:::note Authoritative source
Canonical spec is [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md). Each section below renders the canonical source text inline while section-by-section review against the reference implementation continues. Earlier evolutionary snapshots (`pre-reset` through `v2.0`) are at [`spec/archive/evolution/`](https://github.com/Eidetic-Labs/stigmem/tree/main/spec/archive/evolution).
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
| §4. Intent Envelope | Deferred indefinitely | Per ADR-001. Spec text + STATUS at [`experimental/intent-envelope/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/intent-envelope). Goal/constraint/preference/handoff envelope types — design intent preserved as ADR-008 reintroduction candidate. |
| [§5. Wire Format](./wire-format) | Stable (v1.0; v1.1 §5.21–5.25) | JSON/HTTP wire format for facts, peers, gardens, trust manifests, and capability tokens. |
| [§6. Federation](./federation) | Stable (the pre-reset spec N-node) | Peer handshake, pull replication, scope enforcement, conflict semantics, backpressure. |
| [§7. Design Decisions Log](./design-decisions-log) | Stable | Why the spec made the calls it did. |
| [§8. Open Questions](./open-questions) | Living | Currently-unresolved questions. |
| [§9. Namespace Registry](./namespace-registry) | Stable | Reserved relation prefixes and community registry process. |
| [§10. Schema and Migration](./schema-and-migration) | Stable | SQL schema migrations 001-013. |
| [§11. Failure Mode Scenarios](./failure-mode-scenarios) | Stable | Acceptance test scenarios — split-brain, malicious peer, partial failure, replay attack. |
| [§12. Adapter ABI](./adapter-abi) | Stable | Minimum contract for platform adapters. |
| [§14. Lint Semantics](./lint-semantics) | Stable | POST /v1/lint — orphan relations, scope-escalation violations. |
| §15. Decay Semantics | Deferred from v0.9.0a1 | Per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md). Spec content at [`experimental/decay/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/decay/spec.md). |
| §16. Synthesis | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/synthesis/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/synthesis/spec.md). |
| §17. Memory Garden | Basic stable; advanced ACL deferred | Basic in canonical spec; advanced ACL at [`experimental/memory-garden-acl/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/memory-garden-acl/spec.md) per [ADR-011](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/011-cross-cutting-extraction.md). |
| §18. Source Attestation | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/source-attestation/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/source-attestation/spec.md). |
| [§19. Federation Trust](./federation-trust) | Stable in v0.9.0a1 (basic mTLS + capability tokens) | Advanced trust scoring deferred. |
| §20. Recall & Graph | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/recall-graph/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/recall-graph/spec.md). |
| §21. Lazy Instruction Discovery | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/lazy-instruction-discovery/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/lazy-instruction-discovery/spec.md). |
| [§22. Security Hardening](./security-hardening) | Stable in v0.9.0a1 | mTLS federation, key rotation, audit log, per-principal quotas. |
| §23. Right-to-be-Forgotten Tombstones | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/tombstones/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/tombstones/spec.md). |
| §24. Time-Travel / As-Of Queries | Deferred from v0.9.0a1 | Per ADR-002. Spec content at [`experimental/time-travel/spec.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/time-travel/spec.md). |
| [§25. Content-Addressed Fact IDs](./content-addressed-fact-ids) | **Stable in core** ([ADR-017](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md)) | SHA-256 CIDs for deduplication and tamper detection. |

## Archive

Previous evolutionary spec snapshots (`pre-reset` through `v2.0`) are preserved at [`spec/archive/evolution/`](https://github.com/Eidetic-Labs/stigmem/tree/main/spec/archive/evolution) — see that directory's README. Per [ADR-001](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/001-versioning.md), those version *markers* labeled internal development checkpoints, not tagged releases; the canonical version line of stigmem begins at v0.9.0a1.
