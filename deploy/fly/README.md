# Fly.io Deploy Recipe

Deploys a single stigmem node to [Fly.io](https://fly.io) with:
- TLS termination via Fly's edge
- Persistent volume for the SQLite DB (or Turso / libSQL embedded-replica)
- Health-check at `/healthz`
- Optional scale-to-zero (Fly Machines)
- Optional multi-region read replicas

## Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed and authenticated
- Docker (only needed to build locally; Fly remote builder works without it)

## First-time setup

Run all commands from the **repo root** (the build context is always the root).

```bash
# 1. Pick a globally unique app name
export APP=my-stigmem-node

# 2. Create the app (no deploy yet)
fly apps create "$APP"

# 3. Create a persistent volume (1 GiB, region iad; adjust as needed)
fly volumes create stigmem_data --size 1 --region iad --app "$APP"

# 4. Set required secrets
fly secrets set --app "$APP" \
  STIGMEM_NODE_URL="https://$APP.fly.dev"

# 5. Optional: enable OIDC auth (recommended for production)
fly secrets set --app "$APP" \
  STIGMEM_AUTH_REQUIRED=true \
  STIGMEM_OIDC_ENABLED=true \
  STIGMEM_OIDC_ISSUER_URL="<YOUR_IDP_ISSUER>" \
  STIGMEM_OIDC_AUDIENCE="<YOUR_CLIENT_ID>" \
  STIGMEM_OIDC_ALLOWED_DOMAINS="example.com"

# 6. Deploy
fly deploy --config deploy/fly/fly.toml --app "$APP"
```

After deploy, check:
```bash
fly status --app "$APP"
curl https://"$APP".fly.dev/healthz
```

## Subsequent deploys

```bash
fly deploy --config deploy/fly/fly.toml --app "$APP"
```

## Turso / libSQL backend (recommended for multi-region)

libSQL embedded-replica keeps a local copy for low-latency reads and syncs
writes to Turso's global edge — no sticky-session headaches.

```bash
# Create a Turso DB
turso db create "$APP"
turso db tokens create "$APP"  # copy the token

fly secrets set --app "$APP" \
  STIGMEM_STORAGE_BACKEND=libsql \
  STIGMEM_LIBSQL_URL="libsql://<DB>.turso.io" \
  STIGMEM_LIBSQL_AUTH_TOKEN="<TOKEN>"
```

Then redeploy. The local `stigmem.db` becomes the embedded-replica cache;
the Turso endpoint is the primary.

## Multi-region replicas

Fly Machines can run in multiple regions. Each extra region gets a read-replica.
```bash
fly scale count 2 --region lhr --app "$APP"
```

For federation (separate nodes peering), see the federation guide in docs.

## Scale to zero

Fly Machines support scale-to-zero. Add to `fly.toml`:
```toml
[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

Cold-start latency is ~300 ms; set `min_machines_running = 1` to avoid it for
latency-sensitive workloads.

## Encryption at rest

```bash
fly secrets set --app "$APP" \
  STIGMEM_AT_REST_ENCRYPTION=on \
  MY_DB_PASSPHRASE="<STRONG_RANDOM_PASSPHRASE>"

# Then set the env var name pointer (not the value itself):
fly secrets set --app "$APP" \
  STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_DB_PASSPHRASE
```

## Metrics

The node exposes Prometheus metrics at `:9091/metrics`.
Fly scrapes this automatically when `[metrics]` is present in `fly.toml`.
