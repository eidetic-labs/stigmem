# Docker Compose Deploy Recipe

Single-server or local-dev deployment using Docker Compose.
The compose file supports three profiles:

| Profile flag | What starts |
|---|---|
| _(none)_ | Single stigmem node (SQLite) |
| `--profile federation` | Two-node local federation ring |
| `--profile postgres` | Postgres sidecar (placeholder; backend coming soon) |

## Quick start

```bash
# From repo root:
cp deploy/compose/.env.example deploy/compose/.env
# Edit .env — at minimum set STIGMEM_NODE_URL to your machine's address

docker compose -f deploy/compose/docker-compose.yml \
               --env-file deploy/compose/.env \
               up -d --build
```

Verify:
```bash
curl http://localhost:8765/healthz
# → {"status":"ok","node_id":"..."}

# Write a fact
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{"entity":"deploy","relation":"status","value":{"type":"string","v":"ok"},"source":"smoke","scope":"local"}'

# Read it back
curl -s 'http://localhost:8765/v1/facts?entity=deploy&scope=local' | python3 -m json.tool
```

## Two-node federation ring

```bash
docker compose -f deploy/compose/docker-compose.yml \
               --env-file deploy/compose/.env \
               --profile federation up -d --build

# After both nodes are healthy, exchange federation invites:
# See docs.stigmem.dev/guides/federation for the handshake procedure.
curl http://localhost:8765/healthz
curl http://localhost:8766/healthz
```

## Data persistence

Data is stored in named Docker volumes (`stigmem-data`, `stigmem-b-data`).
To persist to a host path instead, replace the volume entry:

```yaml
volumes:
  - /opt/stigmem/data:/data
```

## Stopping and removing

```bash
# Stop (keep volumes)
docker compose -f deploy/compose/docker-compose.yml down

# Stop and remove all data (destructive!)
docker compose -f deploy/compose/docker-compose.yml down -v
```

## libSQL / Turso backend

Set in `.env`:
```
STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_LIBSQL_URL=libsql://<DB>.turso.io
STIGMEM_LIBSQL_AUTH_TOKEN=<TOKEN>
```

## Encryption at rest

Set in `.env`:
```
STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=STIGMEM_DB_PASSPHRASE
STIGMEM_DB_PASSPHRASE=<strong-random-passphrase>
```
