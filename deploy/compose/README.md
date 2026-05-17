# Docker Compose Deploy Recipe

Single-server or local-dev deployment using Docker Compose.
The compose file supports three profiles:

| Profile flag | What starts |
|---|---|
| _(none)_ | Single stigmem node (SQLite) |
| `--profile federation` | Two-node local plaintext federation ring |
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

This profile is a local plaintext demo. It sets `STIGMEM_FEDERATION_INSECURE=1`
so contributors can exercise replication without provisioning certificates. Do
not use it for production or cross-host federation.

```bash
docker compose -f deploy/compose/docker-compose.yml \
               --env-file deploy/compose/.env \
               --profile federation up -d --build

# After both nodes are healthy, exchange federation invites:
# See docs.stigmem.dev/guides/federation for the handshake procedure.
curl http://localhost:8765/healthz
curl http://localhost:8766/healthz
```

## Two-node mTLS federation example

Use the mTLS compose example when you want a production-shaped local federation
ring. It mounts node certificates and a shared CA bundle, sets
`STIGMEM_TLS_CERT_PATH`, `STIGMEM_TLS_KEY_PATH`, and
`STIGMEM_TLS_CA_BUNDLE`, and does not set `STIGMEM_FEDERATION_INSECURE`.

Generate demo certificate material:

```bash
./deploy/compose/generate-mtls-demo-certs.sh
```

Run the scripted end-to-end smoke:

```bash
bash scripts/mtls-compose-smoke.sh
```

The smoke command generates local-only certificate material in a temp directory,
starts the mTLS compose stack without `STIGMEM_FEDERATION_INSECURE`, verifies
both HTTPS health checks with client certificates, registers peers in both
directions, asserts a fact on node A, verifies federation on node B, and tears
the stack down. Set `KEEP_UP=1` to leave the compose project running for
debugging.

Start the mTLS ring:

```bash
docker compose -f deploy/compose/docker-compose.mtls.yml up -d --build
```

Verify both nodes using the generated client certificates:

```bash
curl --cacert deploy/compose/tls/ca.crt \
  --cert deploy/compose/tls/node-a.crt \
  --key deploy/compose/tls/node-a.key \
  --resolve stigmem-a:8765:127.0.0.1 \
  https://stigmem-a:8765/healthz

curl --cacert deploy/compose/tls/ca.crt \
  --cert deploy/compose/tls/node-b.crt \
  --key deploy/compose/tls/node-b.key \
  --resolve stigmem-b:8766:127.0.0.1 \
  https://stigmem-b:8766/healthz
```

The generated files under `deploy/compose/tls/` are ignored by git. Replace
them with certificates from your real federation CA for any persistent
environment.

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
