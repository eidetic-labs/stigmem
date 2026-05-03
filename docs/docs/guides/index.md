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

Phase 6 deliverables: installer, 4-node topology validation, v0.8 MCP tools, and design-partner pilots ([ACM-60](/ACM/issues/ACM-60)).

| Guide | Deliverable | Topic |
|-------|------------|-------|
| [4-Node Topology](./federation-4node) | D1 ([ACM-61](/ACM/issues/ACM-61)) | Full-mesh 4-node cluster setup, soak tooling, and failure modes |
| [Design Partner Notes](./design-partner-notes) | D5 ([ACM-65](/ACM/issues/ACM-65)) | Feedback themes from Zep, Letta, and Cognee pilots |

For installation, see the [Installation page](../getting-started/installation) (D2) and [Quickstart](../getting-started/quickstart).

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

## Track F — Pre-GA Hardening + Deferred-Spec Cleanup

Pre-GA hardening items from the Phase 6 audit ([ACM-100](/ACM/issues/ACM-100)).

| Guide | Track F item | Status | Topic |
|-------|-------------|--------|-------|
| [Federation (soak results)](./federation#soak-results) | F1 ([ACM-101](/ACM/issues/ACM-101)) | ✅ shipped | Cursor-resume behavior verified under 4-node failure injection |
| [DB-Loss Recovery](./cursor-reset-recovery) | F2 ([ACM-102](/ACM/issues/ACM-102)) | ✅ shipped | `cursor-export` / `cursor-import` runbook — bounds re-pull cost after DB loss |
| [Async Lint/Decay APIs](./async-jobs) | F3 ([ACM-103](/ACM/issues/ACM-103)) | ✅ shipped | Job submission, status polling, and cancellation for lint and decay sweeps |
| F4–F6 | [ACM-104](/ACM/issues/ACM-104)–[ACM-106](/ACM/issues/ACM-106) | 📋 tracked | IntentEnvelope, fuzzy entity resolver, Migration 004 scope columns |

:::info F4–F6 docs coming soon
Pages for F4–F6 will be added as the engineering items ship.
:::

---

## Track C — Per-Principal Identity Hardening

These guides cover source attestation, OIDC-backed human keys, and the joined audit trail. Implementation is in progress; pages are stubs pending the shipping items.

| Guide | Track C item | Topic |
|-------|-------------|-------|
| [Agent Keypairs](./agent-keypairs) | C1 ([ACM-85](/ACM/issues/ACM-85)) | Ed25519 keypair registration and node-enforced source attestation |
| [Human Key Issuance](./human-key-issuance) | C2 ([ACM-86](/ACM/issues/ACM-86)) | OIDC-backed key issuance for human principals |
| [Audit Log](./audit-log) | C3 ([ACM-87](/ACM/issues/ACM-87)) | End-to-end audit trail: principal → attested-source → fact-id |

---

## Track B — Human Surface (UX + Web UI + OIDC)

These guides cover the human-facing browser UI and OIDC identity bridge. Implementation is in progress.

| Guide | Track B item | Topic |
|-------|-------------|-------|
| [Human Surface (Web UI)](./human-surface) | B2 ([ACM-81](/ACM/issues/ACM-81)) | Browser UI for curators, contributors, and consumers |
| [OIDC / SSO Integration](./oidc-sso) | B3 ([ACM-82](/ACM/issues/ACM-82)) | OIDC bridge — human IdP identity → scoped Stigmem API key |

---

## Track A — Memory Garden + Source Attestation

These guides cover the two new primitives added in spec v0.9. Spec drafts are in progress ([ACM-75](/ACM/issues/ACM-75), [ACM-76](/ACM/issues/ACM-76)).

| Guide | Track A item | Topic |
|-------|-------------|-------|
| [Memory Gardens](./memory-gardens) | A1/A3 ([ACM-75](/ACM/issues/ACM-75), [ACM-77](/ACM/issues/ACM-77)) | Named, ACL'd partitions above scope — roles, membership API, enforcement |
| [Source Attestation](./source-attestation) | A2 ([ACM-76](/ACM/issues/ACM-76)) | Signed source URIs bound to auth principal; node rejects mismatched sources |
