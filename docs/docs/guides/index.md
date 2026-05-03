---
id: index
title: Guides
sidebar_label: Overview
---

# Guides

Practical guides for common Stigmem operations. Each guide includes a working `curl` or Python example.

## Available guides

| Guide | Topic |
|-------|-------|
| [Asserting facts](./asserting-facts) | Create, update, and retract facts |
| [Querying facts](./querying-facts) | Filter by entity, relation, scope, confidence, and time |
| [Federation](./federation) | Connect nodes, register peers, and replicate facts |
| [Conflict resolution](./conflict-resolution) | Detect and resolve contradictory facts |
| [Authentication](./authentication) | API keys and per-scope permissions |

---

## Phase 6 — Public Beta + 4-Node Federation

Phase 6 deliverables: installer, 4-node topology validation, v0.8 MCP tools, and design-partner pilots.

| Guide | Topic |
|-------|-------|
| [4-Node Topology](./federation-4node) | Full-mesh 4-node cluster setup, soak tooling, and failure modes |
| [Design Partner Notes](./design-partner-notes) | Feedback themes from Zep, Letta, and Cognee pilots |

For installation, see the [Installation page](../getting-started/installation) and [Quickstart](../getting-started/quickstart).

---

## v0.8 Protocol Operations

New in spec v0.8 — fact lifecycle management and multi-hop federation patterns.

| Guide | Spec | Topic |
|-------|------|-------|
| [Decay Semantics](./decay) | §15 | Retract or reduce confidence of stale facts via configurable `DecayPolicy` |
| [Synthesis](./synthesis) | §16 | Confidence-weighted current-state snapshot for agent context injection |
| [Relay Backpressure](./relay-backpressure) | §6.7 | Lag signals and throttle behavior in N-node relay topologies |
| [Scope Propagation](./scope-propagation) | §6.8 | Transitive scope non-escalation and company re-federation restriction |

---

## Pre-GA Hardening

| Guide | Status | Topic |
|-------|--------|-------|
| [Federation (soak results)](./federation#soak-results) | ✅ shipped | Cursor-resume behavior verified under 4-node failure injection |
| [DB-Loss Recovery](./cursor-reset-recovery) | ✅ shipped | `cursor-export` / `cursor-import` runbook — bounds re-pull cost after DB loss |
| [Async Lint/Decay APIs](./async-jobs) | ✅ shipped | Job submission, status polling, and cancellation for lint and decay sweeps |

---

## Per-Principal Identity Hardening

These guides cover source attestation, OIDC-backed human keys, and the joined audit trail.

| Guide | Topic |
|-------|-------|
| [Agent Keypairs](./agent-keypairs) | Ed25519 keypair registration and node-enforced source attestation |
| [Human Key Issuance](./human-key-issuance) | OIDC-backed key issuance for human principals |
| [Audit Log](./audit-log) | End-to-end audit trail: principal → attested-source → fact-id |

---

## Human Surface

These guides cover the human-facing browser UI and OIDC identity bridge.

| Guide | Topic |
|-------|-------|
| [Human Surface (Web UI)](./human-surface) | Browser UI for curators, contributors, and consumers |
| [OIDC / SSO Integration](./oidc-sso) | OIDC bridge — human IdP identity → scoped Stigmem API key |

---

## Memory Garden + Source Attestation

These guides cover the two new primitives added in spec v0.9.

| Guide | Topic |
|-------|-------|
| [Memory Gardens](./memory-gardens) | Named, ACL'd partitions above scope — roles, membership API, enforcement |
| [Source Attestation](./source-attestation) | Signed source URIs bound to auth principal; node rejects mismatched sources |
