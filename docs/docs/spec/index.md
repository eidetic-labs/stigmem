---
title: Specification
sidebar_label: Overview
audience: Spec
description: Stigmem protocol specification — modular spec navigator for v0.9.0a1.
sidebar_position: 6
---

# Stigmem Protocol Specification

:::note Authoritative source
The maintained protocol composition is [`spec/PROTOCOL.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/PROTOCOL.md), generated from modular component specs under [`spec/specs/`](https://github.com/Eidetic-Labs/stigmem/tree/main/spec/specs) and colocated experimental specs under [`experimental/<feature>/spec.md`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental). The pages below remain rendered compatibility entry points for older section-based links while ADR-010 extraction finishes. Historical evolutionary snapshots are preserved at [`spec/archive/evolution/`](https://github.com/Eidetic-Labs/stigmem/tree/main/spec/archive/evolution).
:::

:::info Security disclosure
Report vulnerabilities via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories) — not as public issues.
:::

## Modular Spec Map

| Rendered Entry Point | Maintained Spec Home | Summary |
|---------|--------|---------|
| [Motivation](./motivation) | Protocol overview prose | Why immutable typed facts beat per-agent mutable stores. |
| [Atomic Fact Shape](./atomic-fact-shape) | [`Spec-01-Fact-Model`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/01-fact-model.md) | Fact tuple, value types, HLC field, and fact-model boundaries. |
| [Fact Semantics](./fact-semantics) | [`Spec-15-Fact-Semantics`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/15-fact-semantics.md) | Provenance, expiry, retraction, contradiction, and conflict entities. |
| Intent Envelope | [`Spec-X8-Intent-Envelope`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/intent-envelope/spec.md) | Deferred indefinitely per ADR-001; design intent preserved for ADR-008 reintroduction. |
| [Wire Format](./wire-format) | [`Spec-03-HTTP-API`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/03-http-api.md) | JSON/HTTP API surface and route contracts. |
| [Federation](./federation) | [`Spec-05-Federation-Trust`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/05-federation-trust.md) | Peer declaration, capability negotiation, replication, and federation scope rules. |
| [Design Decisions Log](./design-decisions-log) | Protocol overview prose | Historical rationale; not an independent component spec. |
| [Open Questions](./open-questions) | Planning/issue-tracking material | Open design questions; not an independent component spec. |
| [Namespace Registry](./namespace-registry) | [`Spec-16-Namespace-Registry`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/16-namespace-registry.md) | Reserved prefixes and registry rules. |
| [Schema and Migration](./schema-and-migration) | [`Spec-17-Schema-and-Migration`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/17-schema-and-migration.md) | Schema, migration cursor, indexes, and backend contract. |
| [Failure Mode Scenarios](./failure-mode-scenarios) | [`Spec-18-Conformance-and-Failure-Modes`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/18-conformance-and-failure-modes.md) | Federation and conformance acceptance scenarios. |
| [Adapter ABI](./adapter-abi) | [`Spec-19-Adapter-ABI`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/19-adapter-abi.md) | Minimum adapter contract and conformance expectations. |
| [Lint Semantics](./lint-semantics) | [`Spec-20-Lint-Semantics`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/20-lint-semantics.md) | Read-only lint checks, finding shapes, severity, and async job behavior. |
| Decay Semantics | [`Spec-X9-Decay-Semantics`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/decay/spec.md) | Experimental/deferred decay sweep semantics. |
| Synthesis | [`Spec-X10-Synthesis`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/synthesis/spec.md) | Experimental/deferred synthesis semantics. |
| Memory Garden | [`Spec-02-Scopes-and-ACL`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/02-scopes-and-acl.md), [`Spec-08-Quarantine-Garden`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/08-quarantine-garden.md), [`Spec-X5-Memory-Garden-Advanced-ACL`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/memory-garden-acl/spec.md) | Basic scopes/gardens are core; advanced ACL remains experimental. |
| Source Attestation | [`Spec-X6-Source-Attestation`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/source-attestation/spec.md) | Experimental source-to-key binding. |
| [Federation Trust](./federation-trust) | [`Spec-04-Manifests`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/04-manifests.md), [`Spec-05-Federation-Trust`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/05-federation-trust.md), [`Spec-06-Capability-Tokens`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/06-capability-tokens.md), [`Spec-08-Quarantine-Garden`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/08-quarantine-garden.md) | Manifests, capability tokens, peer trust, and quarantine boundaries. |
| Recall & Graph | [`Spec-07-Recall-Pipeline`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/07-recall-pipeline.md), [`Spec-X11-Recall-Graph`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/recall-graph/spec.md) | Core recall pipeline plus experimental graph/embedding features. |
| Subscriptions / push federation | [`Spec-X7-Subscriptions`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/subscriptions/spec.md) | Experimental subscription and push-delivery semantics. |
| Lazy Instruction Discovery | [`Spec-X1-Lazy-Instruction-Discovery`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/lazy-instruction-discovery/spec.md) | Experimental lazy instruction recall. |
| [Security Hardening](./security-hardening) | [`Spec-09-Audit-Log`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/09-audit-log.md), [`Spec-10-Hardening`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/10-hardening.md), [`Spec-11-Replay-Protection`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/11-replay-protection.md), [`Spec-12-HLC-Bounded-Skew`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/12-hlc-bounded-skew.md) | mTLS, key rotation, audit, quotas, replay protection, and HLC skew bounds. |
| Right-to-be-Forgotten Tombstones | [`Spec-X2-RTBF-Tombstones`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/tombstones/spec.md) | Experimental/deferred tombstone behavior. |
| Time-Travel / As-Of Queries | [`Spec-X3-Time-Travel-Queries`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/time-travel/spec.md) | Experimental/deferred as-of query behavior. |
| [Content-Addressed Fact IDs](./content-addressed-fact-ids) | [`Spec-21-Content-Addressed-IDs`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/specs/21-content-addressed-ids.md) | Core CIDs per ADR-017. |

## Archive

Previous evolutionary spec snapshots (`pre-reset` through `v2.0`) are preserved at [`spec/archive/evolution/`](https://github.com/Eidetic-Labs/stigmem/tree/main/spec/archive/evolution) — see that directory's README. Per [ADR-001](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/001-versioning.md), those version *markers* labeled internal development checkpoints, not tagged releases; the canonical version line of stigmem begins at v0.9.0a1.
