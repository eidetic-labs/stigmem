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
| **Node Metadata** | `/.well-known/stigmem` | None | §5.3 |
| **Health** | `/healthz` | None | — |

## Authentication

All endpoints except `/.well-known/stigmem` and `/healthz` require an `X-API-Key` header:

```bash
curl -H 'X-API-Key: <your-key>' http://localhost:8000/v1/facts
```

Set `STIGMEM_AUTH_REQUIRED=false` to disable auth in development.

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
