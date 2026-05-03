---
id: index
title: API Reference
sidebar_label: Overview
---

# API Reference

The Stigmem reference node exposes a REST API implementing spec §5. The interactive API reference below is auto-generated from the OpenAPI schema served at `http://localhost:8000/openapi.json`.

## Endpoint groups

| Group | Base path | Auth | Spec |
|-------|-----------|------|------|
| **Facts** | `/v1/facts` | API key | §5.1–§5.5 |
| **Federation** | `/v1/federation/*` | API key + peer token | §5.6–§5.11, §6 |
| **Conflicts** | `/v1/conflicts` | API key | §5.9–§5.10 |
| **Gardens** | `/v1/gardens/*` | API key (role-gated) | §5.14–§5.20, §17 |
| **Lint** | `/v1/lint` | API key | §14 |
| **Decay** | `/v1/decay/sweep` | API key | §15 |
| **Synthesis** | `/v1/synthesis` | API key | §16 |
| **Auth / Keys** | `/v1/auth/keys/*` | Admin API key | §3.5 |
| **Auth / Audit** | `/v1/auth/audit` | Admin API key | §18 |
| **Admin / Billing** | `/v1/admin/billing/events` | Admin API key | — |
| **Async Jobs** | `/v1/jobs/:id` | API key | §14.5, §15.4 |
| **Identity** | `/v1/me` | API key | — |
| **Node Metadata** | `/.well-known/stigmem` | None | §5.3 |
| **Health** | `/healthz` | None | — |

## Authentication

All endpoints except `/.well-known/stigmem` and `/healthz` require an API key. Pass it as a Bearer token:

```bash
curl -H 'Authorization: Bearer <your-key>' http://localhost:8000/v1/facts
```

Set `STIGMEM_AUTH_REQUIRED=false` to disable auth in development.

### OIDC / SSO

Human principals can obtain an API key via OIDC. Configure `STIGMEM_OIDC_*` env vars; the node validates the JWT and maps role claims to `admin|writer|reader`. See [OIDC / SSO Integration](../guides/oidc-sso).

### Multi-tenant requests

Include the `X-Stigmem-Tenant` header to scope a request to a specific tenant:

```bash
curl -H 'Authorization: Bearer <your-key>' \
     -H 'X-Stigmem-Tenant: acme-corp' \
     http://localhost:8000/v1/facts
```

The header is required when `STIGMEM_TENANT_HEADER_REQUIRED=true`. See [Multi-Tenant Scoping](../guides/multi-tenancy).

### Federation peer tokens

Federation endpoints (`/v1/federation/facts`, `/v1/federation/facts/push`) additionally require a peer token:

```
Authorization: Bearer <peer-token>
```

Peer tokens are Ed25519-signed JWTs exchanged during the federation handshake (spec §6.3).

## Generating interactive docs

The interactive try-it-out panels are generated from the live OpenAPI schema:

```bash
# Terminal 1 — start the reference node
cd stigmem/node
uv run python -m stigmem_node

# Terminal 2 — regenerate and serve docs
cd stigmem/docs
npm run gen-api-docs
npm run start
```

After regenerating, the sidebar shows individual endpoint pages with live request panels.

:::info
The API reference sidebar is populated by `npm run gen-api-docs`. Until that command has run, only this overview page appears.
:::
