# Render Deploy Guide

Deploy stigmem to [Render](https://render.com) using a Web Service backed by a
persistent Disk (SQLite) or Turso (libSQL, stateless).

## Prerequisites

- A Render account
- The repo pushed to GitHub / GitLab (Render auto-deploys on push)

## Steps

### 1. Create a Web Service

1. **Dashboard → New → Web Service**
2. Connect your repo
3. Settings:
   - **Name**: `stigmem` (or anything)
   - **Region**: nearest to your users
   - **Branch**: `main`
   - **Runtime**: Docker
   - **Dockerfile path**: `node/Dockerfile`
   - **Docker context**: `.` (repo root)
   - **Instance Type**: Starter ($7/mo) or Free (no persistent disk)

### 2. Attach a persistent Disk (SQLite)

1. **Service → Disks → Add Disk**
2. **Mount path**: `/data`
3. **Size**: 1 GiB (adjust as needed)

Skip this step if using the libSQL / Turso backend.

### 3. Set environment variables

In **Service → Environment**, add:

| Key | Value |
|---|---|
| `STIGMEM_PORT` | `8765` |
| `STIGMEM_NODE_URL` | `https://<your-service>.onrender.com` |
| `STIGMEM_DB_PATH` | `/data/stigmem.db` |
| `STIGMEM_LOG_LEVEL` | `info` |
| `STIGMEM_AUTH_REQUIRED` | `true` (recommended for production) |

### 4. Deploy

Click **Deploy**. Render builds the Docker image and starts the container.

Verify:
```bash
curl https://<your-service>.onrender.com/healthz
```

## libSQL / Turso (stateless, no disk needed)

Add these secrets instead of mounting a disk:

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

## Health check

Render's health check should be configured as:
- **Path**: `/healthz`
- **Period**: 10s
