---
id: human-key-issuance
title: Human Key Issuance (OIDC)
sidebar_label: Human Key Issuance (C2)
---

# Human Key Issuance (OIDC)

**Audience:** Node operators setting up human-facing access, and developers integrating Stigmem with an identity provider.

:::info Coming in Track C
OIDC-backed human key issuance is planned for Track C — Per-Principal Identity Hardening ([ACM-86](/ACM/issues/ACM-86)). This page is a stub. Content will be completed once the implementation lands.
:::

## Overview

The existing API-key model (§3.5) issues opaque tokens administered manually. Track C — work item C2 ties key issuance to an OIDC identity provider so that:

- Human users authenticate via their IdP (e.g. Google, GitHub, Okta).
- The node exchanges the OIDC ID token for a scoped Stigmem principal.
- The principal's key is bound to the OIDC subject claim — keys rotate on IdP token expiry.
- The `source` field on facts asserted by a human principal reflects the verified OIDC identity (e.g. `human:alice@example.com`).

This is the companion flow to C1 (agent keypairs): together they make every source claim in the fact store verifiably principal-bound.

## Foundation: current API-key model

Today, API keys are issued out-of-band by the node operator and stored as SHA-256 hashes:

```bash
# Today: manually provisioned key
curl -H 'X-API-Key: my-static-key' http://localhost:8000/v1/facts
```

C2 adds an OIDC exchange endpoint that replaces manual provisioning for human users.

## Topics to be covered

- Configuring the OIDC provider (`STIGMEM_OIDC_ISSUER`, `STIGMEM_OIDC_CLIENT_ID`)
- The OIDC exchange flow: ID token → Stigmem principal + scoped key
- Claim mapping: which OIDC claims become the principal URI
- Token expiry, renewal, and key rotation
- Disabling OIDC (fallback to static API keys only)
- Security considerations: token validation, audience binding

## See also

- [Authentication](./authentication) — existing API-key and peer-token auth model
- [Agent Keypairs](./agent-keypairs) — C1: verifiable source attestation for agents
- [Audit Log](./audit-log) — C3: querying the attestation audit trail
