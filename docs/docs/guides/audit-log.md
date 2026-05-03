---
id: audit-log
title: Audit Log
sidebar_label: Audit Log (C3)
---

# Audit Log

**Audience:** Node operators and security engineers who need an end-to-end trail linking facts to verified principals.

:::info Coming in Track C
The joined audit log surface is planned for Track C — Per-Principal Identity Hardening (ACM-87). This page is a stub. Content will be completed once the implementation lands.
:::

## Overview

Stigmem already tracks provenance at two levels:

- **Fact provenance** — every fact carries a `source` field and the node records `stigmem:received_from` meta-facts (§3.1).
- **Federation audit** — the `federation_audit` table (§10) logs inter-node fact exchange.

Track C — work item C3 adds a unified audit surface that joins these with the verified principal introduced by C1 and C2:

```
principal (OIDC sub / agent key fingerprint)
  └── attested-source (URI verified by keypair)
        └── fact-id (the asserted fact record)
```

The result is a queryable trail that answers: _who_ (principal) used _what credential_ (attested source) to assert _which fact_ (fact-id), and when.

## Foundation: current provenance infrastructure

The `source` field and meta-fact provenance are available today:

```bash
# Query facts with provenance meta-facts
curl -s "http://localhost:8000/v1/facts?entity=stigmem%3Afact%3A<uuid>" \
  -H 'X-API-Key: dev-key' | jq '.facts[] | select(.relation == "stigmem:received_from")'
```

C3 adds `GET /v1/audit` (or similar) that exposes the joined view without needing manual meta-fact traversal.

## Topics to be covered

- Querying the audit log: `GET /v1/audit` endpoint parameters
- Filtering by principal, source, fact-id, time range
- Retention policy and log rotation (`STIGMEM_AUDIT_RETENTION_DAYS`)
- Exporting audit records for SIEM integration
- Understanding the `principal → attested-source → fact-id` join
- What is logged for API-key clients vs. keypair-attested agents vs. OIDC humans

## See also

- [Agent Keypairs](./agent-keypairs) — C1: establishing verified source attestation
- [Human Key Issuance](./human-key-issuance) — C2: OIDC-backed principal identities
- [Authentication](./authentication) — baseline auth and the source field
