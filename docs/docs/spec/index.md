---
title: Specification
sidebar_label: Overview
audience: Spec
description: Stigmem protocol specification — modular spec navigator for v0.9.0a1.
sidebar_position: 6
---

# Stigmem Protocol Specification

:::note Authoritative source
The maintained protocol composition is generated from the modular component specs and colocated experimental specs rendered below. Section-based pages remain compatibility entry points for older links while ADR-010 extraction finishes. Historical evolutionary snapshots remain archived in the repository.
:::

:::info Security disclosure
Report vulnerabilities via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories) — not as public issues.
:::

## Modular Spec Map

| Rendered Entry Point | Maintained Spec Home | Summary |
|---------|--------|---------|
| [Motivation](./motivation) | Protocol overview prose | Why immutable typed facts beat per-agent mutable stores. |
| [Atomic Fact Shape](./atomic-fact-shape) | [`Spec-01-Fact-Model`](./specs/fact-model) | Fact tuple, value types, HLC field, and fact-model boundaries. |
| [Fact Semantics](./fact-semantics) | [`Spec-15-Fact-Semantics`](./specs/fact-semantics) | Provenance, expiry, retraction, contradiction, and conflict entities. |
| Intent Envelope | [`Spec-X8-Intent-Envelope`](./experimental/intent-envelope) | Deferred indefinitely per ADR-001; design intent preserved for ADR-008 reintroduction. |
| [Wire Format](./wire-format) | [`Spec-03-HTTP-API`](./specs/http-api) | JSON/HTTP API surface and route contracts. |
| [Federation](./federation) | [`Spec-05-Federation-Trust`](./specs/federation-trust) | Peer declaration, capability negotiation, replication, and federation scope rules. |
| [Design Decisions Log](./design-decisions-log) | Protocol overview prose | Historical rationale; not an independent component spec. |
| [Open Questions](./open-questions) | Planning/issue-tracking material | Open design questions; not an independent component spec. |
| [Namespace Registry](./namespace-registry) | [`Spec-16-Namespace-Registry`](./specs/namespace-registry) | Reserved prefixes and registry rules. |
| [Schema and Migration](./schema-and-migration) | [`Spec-17-Schema-and-Migration`](./specs/schema-and-migration) | Schema, migration cursor, indexes, and backend contract. |
| [Failure Mode Scenarios](./failure-mode-scenarios) | [`Spec-18-Conformance-and-Failure-Modes`](./specs/conformance-and-failure-modes) | Federation and conformance acceptance scenarios. |
| [Adapter ABI](./adapter-abi) | [`Spec-19-Adapter-ABI`](./specs/adapter-abi) | Minimum adapter contract and conformance expectations. |
| [Lint Semantics](./lint-semantics) | [`Spec-20-Lint-Semantics`](./specs/lint-semantics) | Read-only lint checks, finding shapes, severity, and async job behavior. |
| Decay Semantics | [`Spec-X9-Decay-Semantics`](./experimental/decay-semantics) | Experimental/deferred decay sweep semantics. |
| Synthesis | [`Spec-X10-Synthesis`](./experimental/synthesis) | Experimental/deferred synthesis semantics. |
| Memory Garden | [`Spec-02-Scopes-and-ACL`](./specs/scopes-and-acl), [`Spec-08-Quarantine-Garden`](./specs/quarantine-garden), [`Spec-X5-Memory-Garden-Advanced-ACL`](./experimental/memory-garden-advanced-acl) | Basic scopes/gardens are core; advanced ACL remains experimental. |
| Source Attestation | [`Spec-X6-Source-Attestation`](./experimental/source-attestation) | Experimental source-to-key binding. |
| [Federation Trust](./federation-trust) | [`Spec-04-Manifests`](./specs/manifests), [`Spec-05-Federation-Trust`](./specs/federation-trust), [`Spec-06-Capability-Tokens`](./specs/capability-tokens), [`Spec-08-Quarantine-Garden`](./specs/quarantine-garden) | Manifests, capability tokens, peer trust, and quarantine boundaries. |
| Recall & Graph | [`Spec-07-Recall-Pipeline`](./specs/recall-pipeline), [`Spec-X11-Recall-Graph`](./experimental/recall-graph) | Core recall pipeline plus experimental graph/embedding features. |
| Subscriptions / push federation | [`Spec-X7-Subscriptions`](./experimental/subscriptions) | Experimental subscription and push-delivery semantics. |
| Lazy Instruction Discovery | [`Spec-X1-Lazy-Instruction-Discovery`](./experimental/lazy-instruction-discovery) | Experimental lazy instruction recall. |
| [Security Hardening](./security-hardening) | [`Spec-09-Audit-Log`](./specs/audit-log), [`Spec-10-Hardening`](./specs/hardening), [`Spec-11-Replay-Protection`](./specs/replay-protection), [`Spec-12-HLC-Bounded-Skew`](./specs/hlc-bounded-skew) | mTLS, key rotation, audit, quotas, replay protection, and HLC skew bounds. |
| Right-to-be-Forgotten Tombstones | [`Spec-X2-RTBF-Tombstones`](./experimental/rtbf-tombstones) | Experimental/deferred tombstone behavior. |
| Time-Travel / As-Of Queries | [`Spec-X3-Time-Travel-Queries`](./experimental/time-travel-queries) | Experimental/deferred as-of query behavior. |
| [Content-Addressed Fact IDs](./content-addressed-fact-ids) | [`Spec-21-Content-Addressed-IDs`](./specs/content-addressed-ids) | Core CIDs per ADR-017. |

## Archive

Previous evolutionary spec snapshots (`pre-reset` through `v2.0`) remain preserved under the repository archive. Per ADR-001, those version *markers* labeled internal development checkpoints, not tagged releases; the canonical version line of stigmem begins at v0.9.0a1.
