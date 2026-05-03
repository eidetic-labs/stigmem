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

:::info Coming soon
Full guide content is planned for the next docs sprint. The stubs below give a preview of coverage.
:::

## Track C — Per-Principal Identity Hardening

These guides cover source attestation, OIDC-backed human keys, and the joined audit trail. Implementation is in progress; pages are stubs pending the shipping items.

| Guide | Track C item | Topic |
|-------|-------------|-------|
| [Agent Keypairs](./agent-keypairs) | C1 ([ACM-85](/ACM/issues/ACM-85)) | Ed25519 keypair registration and node-enforced source attestation |
| [Human Key Issuance](./human-key-issuance) | C2 ([ACM-86](/ACM/issues/ACM-86)) | OIDC-backed key issuance for human principals |
| [Audit Log](./audit-log) | C3 ([ACM-87](/ACM/issues/ACM-87)) | End-to-end audit trail: principal → attested-source → fact-id |
