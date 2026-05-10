# Railway Deploy Guide

Deploy stigmem to [Railway](https://railway.app) — GitHub-connected, auto-deploys
on every push.

## Prerequisites

- A Railway account
- The repo pushed to GitHub

## Steps

### 1. Create a project

1. **New Project → Deploy from GitHub repo**
2. Select your repo

Railway auto-detects the Dockerfile.

### 2. Configure the service

In **Service → Settings**:

- **Dockerfile path**: `node/Dockerfile`
- **Build context** (if configurable): `.` (repo root)
- **Port**: `8765`

### 3. Set environment variables

In **Service → Variables**, add:

| Key | Value |
|---|---|
| `STIGMEM_PORT` | `8765` |
| `STIGMEM_NODE_URL` | `https://${{RAILWAY_STATIC_URL}}` |
| `STIGMEM_DB_PATH` | `/data/stigmem.db` |
| `STIGMEM_LOG_LEVEL` | `info` |
| `STIGMEM_AUTH_REQUIRED` | `true` |

Railway injects `RAILWAY_STATIC_URL` automatically; use `${{RAILWAY_STATIC_URL}}`
in other variable values to reference it.

### 4. Add a volume (SQLite persistence)

1. **Project → New → Volume**
2. Attach it to your service
3. **Mount path**: `/data`

Skip this step if using the libSQL / Turso backend.

### 5. Deploy

Railway deploys automatically. Check **Deployments** for the build log.

```bash
curl https://<railway-domain>/healthz
```

## libSQL / Turso (stateless)

| Key | Value |
|---|---|
| `STIGMEM_STORAGE_BACKEND` | `libsql` |
| `STIGMEM_LIBSQL_URL` | `libsql://<DB>.turso.io` |
| `STIGMEM_LIBSQL_AUTH_TOKEN` | `<TOKEN>` |

## OIDC auth

| Key | Value |
|---|---|
| `STIGMEM_OIDC_ENABLED` | `true` |
| `STIGMEM_OIDC_ISSUER_URL` | `<IDP_ISSUER>` |
| `STIGMEM_OIDC_AUDIENCE` | `<CLIENT_ID>` |
| `STIGMEM_OIDC_ALLOWED_DOMAINS` | `example.com` |

## Rollback

Railway keeps previous deployment artifacts.
Click any past deployment → **Redeploy** to roll back instantly.
