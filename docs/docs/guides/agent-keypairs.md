---
id: agent-keypairs
title: Per-Agent Keypair Registration
sidebar_label: Agent Keypairs (C1)
---

# Per-Agent Keypair Registration

**Audience:** Node operators and agent developers who need verifiable source attestation on asserted facts.

:::info Coming in Track C
Per-agent keypair registration is planned for Track C — Per-Principal Identity Hardening (ACM-85). This page is a stub. Content will be completed once the implementation lands.
:::

## Overview

Today, Stigmem nodes identify the _source_ of a fact via the `source` field (a URI string, e.g. `agent:settings-sync`) but do not cryptographically verify that the asserting client controls that identity. Track C — work item C1 closes this gap.

**After C1 ships:**

- Each agent registers an Ed25519 keypair with the node at enrollment time.
- Every `POST /v1/facts` request from a registered agent must include a signature covering the fact payload.
- The node rejects facts whose source attestation is missing or fails verification.
- The existing Phase 2 API-key model (§3.5) continues to work for human-facing clients; keypair auth is additive.

## Foundation: current auth and provenance model

Stigmem v0.5 introduced per-scope API-key restrictions (§3.5). The `source` field on every fact already provides provenance metadata (§3.1):

```bash
# Today: source is asserted by the client — not verified
curl -s -X POST http://localhost:8000/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity": "user:alice",
    "relation": "memory:context",
    "value": "working on stigmem C1",
    "source": "agent:coding-assistant",
    "confidence": 1.0,
    "scope": "local"
  }'
```

C1 replaces the unverified `source` claim with a cryptographically attested one.

## Topics to be covered

- Generating an Ed25519 keypair for an agent
- Registering the keypair with the node (`POST /v1/principals/agents`)
- Signing fact payloads and including the attestation header
- Node-side verification and rejection policy
- Migrating existing agents from API-key-only to keypair-attested auth
- Env var: `STIGMEM_REQUIRE_SOURCE_ATTESTATION`

## See also

- [Authentication](./authentication) — existing API-key and peer-token auth model
- [Human Key Issuance](./human-key-issuance) — C2: OIDC-backed keys for human principals
- [Audit Log](./audit-log) — C3: querying the attestation audit trail
