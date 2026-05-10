---
id: multi-tenancy
title: Multi-Tenant Scoping
sidebar_label: Multi-Tenant Scoping
audience: Integrator
status: Beta
---

# Multi-Tenant Scoping

**Audience:** Node operators running a shared stigmem node for multiple teams, customers, or isolated environments.

Multi-tenancy is a reference-node feature (not a spec §). A single stigmem process can serve multiple tenants with complete data isolation — facts, gardens, audit records, and API keys are partitioned by `tenant_id` at the database level.

:::info v1.0 reference node
Tenant isolation shipped in migration `012_multi_tenant` with the v1.0-rc reference node. All pre-migration rows are automatically assigned `tenant_id = "default"`, so single-tenant deployments require no configuration change.
:::

## How it works

Every API key carries a `tenant_id`. When the node authenticates a request it extracts `tenant_id` from the resolved identity and applies it to every read and write:

```
Bearer token → Identity(entity_uri, permissions, tenant_id)
                                                  │
        ┌─────────────────────────────────────────┘
        ▼
  WHERE … AND tenant_id = ?   (every SELECT, INSERT, UPDATE)
```

Tenants are completely opaque to each other. There is no cross-tenant API — a `tenant_id = "acme"` key cannot see, modify, or even confirm the existence of facts belonging to `tenant_id = "beta"`.

## Isolation guarantees

| Resource | Isolation mechanism |
|----------|---------------------|
| Facts | `tenant_id` column on `facts`; all queries filter by caller's tenant |
| Gardens | `UNIQUE(slug, tenant_id)`; same slug can exist in multiple tenants independently |
| Garden ACL | Members are resolved within the tenant; cross-tenant membership is impossible |
| Audit log | `tenant_id` column on `fact_audit_log`; audit queries are tenant-scoped |
| API keys | `tenant_id` column on `api_keys`; a key belongs to exactly one tenant |
| Federation | Garden-isolation invariant applies globally (§6 spec); federation payloads never cross tenant boundaries |

### What is NOT isolated

- **Node-level settings** — env vars like `STIGMEM_SOURCE_ATTESTATION_MODE` apply to all tenants equally.
- **Well-known / health endpoints** — `/.well-known/stigmem` and `/healthz` are public and tenant-agnostic.
- **Node identity** — all tenants share the same node URI and Ed25519 signing key.

## Assigning a tenant to an API key

Tenants are set when creating an API key via the admin API:

```bash
curl -s -X POST http://localhost:8765/v1/auth/keys \
  -H 'Authorization: Bearer <admin-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "entity_uri": "service:payments",
    "permissions": ["read", "write"],
    "tenant_id": "acme-corp",
    "description": "Payments service — acme-corp tenant"
  }'
```

The response includes the raw key (shown once only) and the assigned `tenant_id`:

```json
{
  "key": "stgm_...",
  "entity_uri": "service:payments",
  "permissions": ["read", "write"],
  "tenant_id": "acme-corp"
}
```

All subsequent requests made with this key operate exclusively within `tenant_id = "acme-corp"`.

## Verifying tenant assignment

`GET /v1/me` returns the caller's resolved identity, including `tenant_id`:

```bash
curl -H 'Authorization: Bearer stgm_...' http://localhost:8765/v1/me
# → {"entity_uri": "service:payments", "permissions": ["read", "write"], "tenant_id": "acme-corp"}
```

## Isolation in practice

```bash
# Key A → tenant "acme-corp"
KEY_A=stgm_acme_...
# Key B → tenant "beta-inc"
KEY_B=stgm_beta_...

# Write a fact as acme-corp
FACT_ID=$(curl -s -X POST http://localhost:8765/v1/facts \
  -H "Authorization: Bearer $KEY_A" \
  -H 'Content-Type: application/json' \
  -d '{"entity":"project:alpha","relation":"status","value":"active","source":"service:payments"}' \
  | jq -r .id)

# Same fact is invisible to beta-inc → 404
curl -s -H "Authorization: Bearer $KEY_B" \
  http://localhost:8765/v1/facts/$FACT_ID
# → {"detail": "Not found"}
```

## Default tenant

Keys created without an explicit `tenant_id` are assigned `tenant_id = "default"`. All pre-v1.0 data already lives in `"default"`. This means:

- Single-tenant deployments continue working with zero changes.
- If you want to add a second tenant, you create new keys with a different `tenant_id` — existing keys remain in `"default"`.

## Security posture

Multi-tenancy is enforced in the database layer, not just in application logic:

- Every table that holds user data (`facts`, `gardens`, `api_keys`, `fact_audit_log`) has a `tenant_id` column.
- Indexed for query performance (`idx_facts_tenant`, `idx_audit_tenant`).
- No application path bypasses the `tenant_id` filter. The full isolation test suite is in `node/tests/test_multi_tenant.py`.

For production deployments serving multiple customers:

```bash
# Require authentication on all requests (no anonymous access)
STIGMEM_AUTH_REQUIRED=true

# Enforce source attestation — each tenant's writes must match their entity_uri
STIGMEM_SOURCE_ATTESTATION_MODE=enforce
```

See [Source Attestation](./source-attestation) and the [Features page](../../learn/features) for the full hardening checklist.

## Tenant naming

`tenant_id` is an opaque string. Conventions:

- Use a stable, URL-safe slug: `acme-corp`, `team-ml`, `staging`.
- Keep it consistent across all keys belonging to that tenant.
- There is no tenant registry in the node — tenant identity is implicit in key assignment.

## See also

- [Authentication](./authentication) — API key lifecycle, permissions
- [Billing Hooks](./billing-hooks) — per-tenant billing event emission
- [Audit Log](./audit-log) — querying the tenant-scoped audit trail
- [Source Attestation](./source-attestation) — enforce `entity_uri` binding per tenant
- [Upgrade to v1.0](../../learn/quickstart/upgrade-v1) — migrating from single-tenant v0.x deployments
- [Installation](../../learn/quickstart/installation) — node setup and environment configuration
