---
id: index
title: Guides
sidebar_label: Overview
---

# Guides

Practical guides for common Stigmem operations. Each guide includes a working `curl` or Python example.

## Core operations

| Guide | Topic |
|-------|-------|
| [Asserting facts](./asserting-facts) | Create, update, and retract facts |
| [Querying facts](./querying-facts) | Filter by entity, relation, scope, confidence, and time |
| [Federation](./federation) | Connect nodes, register peers, and replicate facts |
| [Conflict resolution](./conflict-resolution) | Detect and resolve contradictory facts |
| [Authentication](./authentication) | API keys and per-scope permissions |

---

## Phase 10 features (§21 — DRAFT)

New DRAFT sections covering instruction migration and lazy instruction discovery (spec §21).

| Guide | Spec | Topic |
|-------|------|-------|
| [Instruction Migration](./instruction-migration) | §21 | `stigmem instruction migrate` — convert markdown files to facts, publish manifest, tombstone removed units |

---

## v1.1 features (Phase 9 — DRAFT)

New DRAFT normative sections in v1.1 (spec §20).

| Guide | Spec | Topic |
|-------|------|-------|
| [Recall](./recall) | §20.3 | Hybrid recall — lexical + dense + graph pipeline, token budget, weight tuning |
| [Memory Cards](./memory-cards) | §20.4 | Per-entity pre-aggregated summaries — stale-on-write, refresh-on-read, divergence policy |
| [Subscriptions](./subscriptions) | §20.3–§20.6 | Standing fact-change watches — webhook and wake delivery, circuit breaker, replay window |
| [Python SDK](./python-sdk) | — | `StigmemClient` / `AsyncStigmemClient` API reference — all methods, models, exceptions |

---

## v1.0 features

New normative sections in v1.0 (spec §§17–18) and supporting node capabilities.

| Guide | Spec | Topic |
|-------|------|-------|
| [Memory Gardens](./memory-gardens) | §17 | Named, ACL'd partitions above scope — roles, membership API, enforcement |
| [Source Attestation](./source-attestation) | §18 | `entity_uri` binding on API keys; enforce, warn, or off modes |
| [Multi-Tenant Scoping](./multi-tenancy) | — | Complete data isolation for multiple teams or customers on one node |
| [Fuzzy Entity Resolver](./fuzzy-entity-resolver) | §2.6.6 | Semantic alias matching on entity lookup |
| [Billing Hooks](./billing-hooks) | — | `BillingEvent` emission on writes — log or forward to a custom backend |
| [Agent Keypairs](./agent-keypairs) | §18 | Ed25519 keypair registration and node-enforced source attestation |
| [Human Key Issuance](./human-key-issuance) | — | OIDC-backed key issuance for human principals |
| [OIDC / SSO Integration](./oidc-sso) | — | OIDC bridge — human IdP identity → scoped Stigmem API key |
| [Human Surface (Web UI)](./human-surface) | — | Browser UI for curators, contributors, and consumers |
| [Audit Log](./audit-log) | §18 | End-to-end audit trail: principal → attested-source → fact-id |

---

## Fact lifecycle

| Guide | Spec | Topic |
|-------|------|-------|
| [Decay Semantics](./decay) | §15 | Retract or reduce confidence of stale facts via configurable `DecayPolicy` |
| [Synthesis](./synthesis) | §16 | Confidence-weighted current-state snapshot for agent context injection |
| [Async Lint/Decay APIs](./async-jobs) | §14.5, §15.4 | Job submission, status polling, and cancellation for lint and decay sweeps |

---

## Federation deep-dives

| Guide | Spec | Topic |
|-------|------|-------|
| [4-Node Topology](./federation-4node) | §6 | Full-mesh 4-node cluster setup, soak tooling, and failure modes |
| [Relay Backpressure](./relay-backpressure) | §6.7 | Lag signals and throttle behavior in N-node relay topologies |
| [Scope Propagation](./scope-propagation) | §6.8 | Transitive scope non-escalation and `company` re-federation restriction |
| [DB-Loss Recovery](./cursor-reset-recovery) | §6 | `cursor-export` / `cursor-import` runbook — bounds re-pull cost after DB loss |

---

## Reference

| Guide | Topic |
|-------|-------|
| [Intent Envelopes](./intent-envelopes) | Non-normative §4 draft — goal, constraint, preference, handoff |
| [Design Partner Notes](./design-partner-notes) | Feedback themes from Zep, Letta, and Cognee pilots |
