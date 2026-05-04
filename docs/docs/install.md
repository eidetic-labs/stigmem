---
id: install
title: Deployment & Installation
sidebar_label: Deployment
---

# Deployment & Installation

**Audience:** node operators installing Stigmem for the first time, or migrating an existing bare-metal install to Docker.

:::tip Operator handbook
For narrative runbooks covering Fly.io, Helm, systemd, PaaS, and backend selection, see **[Operating Stigmem → Deploy runbooks](./operating/deploy-runbooks)**.
:::

The reference node ships as a Docker image. Docker Compose is the recommended deployment path for both local development and single-host production. For development against source, see [Running without Docker](#running-without-docker).

## Deploy recipes

The [`deploy/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy) directory
contains self-contained reference recipes for every common hosting environment:

| Recipe | Best for |
|---|---|
| [Fly.io](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/fly) | Personal / small team; zero-config TLS |
| [Docker Compose](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/compose) | Local dev / single-server self-host |
| [Helm](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/helm) | Kubernetes / enterprise |
| [systemd](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/systemd) | Sovereign, air-gapped, bare metal |
| [PaaS](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/paas) | Render, Railway, AWS App Runner, GCP Cloud Run |

See [`deploy/README.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/deploy/README.md)
for a decision tree. The sections below cover the Docker Compose path in detail.

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker | ≥ 24 |
| Docker Compose (v2) | ≥ 2.20 |
| Git | any recent |

No Python or Node.js installation is required for the Docker path.

---

## One-click Docker Compose install

Clone the repo and start two federated nodes with a single command:

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
docker compose up --build -d
```

This builds the reference node image once and starts `node-a` and `node-b`:

| Container | Host port | Key endpoints |
|-----------|-----------|---------------|
| `node-a` | 8765 | `http://localhost:8765/healthz` · `/docs` · `/.well-known/stigmem` |
| `node-b` | 8766 | `http://localhost:8766/healthz` · `/docs` · `/.well-known/stigmem` |

Verify both are healthy:

```bash
curl -s http://localhost:8765/healthz   # → {"status":"ok"}
curl -s http://localhost:8766/healthz   # → {"status":"ok"}
```

Then follow the [Quickstart](./getting-started/quickstart) to complete the federation handshake and assert your first fact.

### Persist your keypairs

By default, each node auto-generates an Ed25519 keypair on first start and stores it in `node_meta`. To survive container recreation, supply your own:

```bash
# Generate a keypair (requires Python)
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64, os
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes_raw()
pub_bytes  = priv.public_key().public_bytes_raw()
print('STIGMEM_FEDERATION_PRIVKEY=' + base64.urlsafe_b64encode(priv_bytes).decode())
print('STIGMEM_FEDERATION_PUBKEY='  + base64.urlsafe_b64encode(pub_bytes).decode())
"
```

Add those two variables to the `environment:` block of your `docker-compose.yml`.

### Stop and clean up

```bash
docker compose down      # stop containers; preserve data volumes
docker compose down -v   # stop and delete all data
```

---

## Multi-node topology (soak / staging)

For 4-node full-mesh federation with shorter pull intervals:

```bash
# Generate keypairs for all four nodes
cd infra && python soak/keys.py > soak/.env

# Start the cluster
docker compose -f infra/docker-compose.soak.yml --env-file infra/soak/.env up --build -d
```

Nodes run on ports 8765–8768. See the [4-node federation guide](./guides/federation-4node) for peer wiring, backpressure, and failure injection.

---

## Environment variable reference

All variables use the `STIGMEM_` prefix and can be set in the `environment:` block of `docker-compose.yml`, as system environment variables, or in a `.env` file next to the node binary.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_DB_PATH` | `stigmem.db` | Path to the SQLite database file |
| `STIGMEM_HOST` | `0.0.0.0` | Bind address |
| `STIGMEM_PORT` | `8765` | Port the HTTP server listens on |
| `STIGMEM_NODE_URL` | `http://localhost:8765` | Public URL of this node — included in `PeerDeclaration` payloads (§5.3) |
| `STIGMEM_LOG_LEVEL` | `info` | Log verbosity: `debug` · `info` · `warning` · `error` |
| `STIGMEM_AUTH_REQUIRED` | `true` | When `true` (default), every request must carry a valid Bearer token. Set `false` only for single-operator / local-only installs |

### Federation (§6)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_FEDERATION_ENABLED` | `false` | Enable the pull-replication loop |
| `STIGMEM_FEDERATION_PUBKEY` | `""` | Base64url-encoded Ed25519 public key. Auto-generated on first start if empty; **persist this** |
| `STIGMEM_FEDERATION_PRIVKEY` | `""` | Base64url-encoded Ed25519 private key. Auto-generated on first start if empty; **persist this** |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | Seconds between pull cycles. Peer-advertised `pull_interval_s` takes precedence (§6.3) |
| `STIGMEM_FEDERATION_PUSH_ENABLED` | `false` | Enable push replication (experimental; off by default) |
| `STIGMEM_FEDERATION_NONCE_WINDOW_S` | `300` | How long a nonce is retained to block replays (§6.6, default = 5 min) |
| `STIGMEM_FEDERATION_ALLOW_TEAM` | `false` | Allow `team`-scoped facts to cross federation boundaries. Requires explicit opt-in; all crossings are audit-logged |

### Decay (§15)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_DECAY_TTL_SECONDS` | `0` | When a sweep runs without an explicit `ttl_seconds`, decay facts older than this. `0` = disabled |
| `STIGMEM_DECAY_MIN_CONFIDENCE` | `0.0` | When a sweep runs without an explicit `min_confidence`, decay facts below this confidence. `0.0` = disabled |

### Attestation & security (§18)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_ATTESTATION_REQUIRED` | `false` | Require a valid Ed25519 attestation token on every `POST /v1/facts`. Enable for multi-tenant or public nodes |
| `STIGMEM_SOURCE_ATTESTATION_MODE` | `warn` | How the node enforces §18 source-attestation. `off` = no check · `warn` = accept with `attested=false`, log warning · `enforce` = reject with HTTP 403 |

### OIDC bridge (§B3)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_OIDC_ENABLED` | `false` | Enable the OIDC → API key bridge |
| `STIGMEM_OIDC_ISSUER_URL` | `""` | IdP issuer URL; discovery doc fetched from `{issuer_url}/.well-known/openid-configuration` |
| `STIGMEM_OIDC_AUDIENCE` | `""` | Expected `aud` claim in the `id_token` |
| `STIGMEM_OIDC_TOKEN_TTL_HOURS` | `8` | Lifetime of issued API keys in hours (default = one working-day session) |
| `STIGMEM_OIDC_ALLOWED_DOMAINS` | `""` | Comma-separated list of allowed email domains; empty = allow any |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_ASYNC_JOB_THRESHOLD` | `100000` | Fact count per scope above which `POST /v1/decay/sweep` returns `202 Accepted` and runs in the background |

---

## Upgrade

### Upgrading a Docker Compose install

```bash
git pull
docker compose up --build -d
```

Data volumes persist across rebuilds. Database migrations run automatically on startup — there is no manual migration step.

### Upgrading from bare-metal to Docker Compose

If you ran the node directly via `uv run python -m stigmem_node` or the macOS LaunchAgent, follow these steps to migrate to Docker Compose without losing data.

**1 — Stop the existing service**

```bash
# If running as a macOS LaunchAgent:
bash scripts/service-uninstall.sh

# If running manually, stop the process (Ctrl-C or kill the PID).
```

**2 — Locate your database**

By default the bare-metal node writes to `data/stigmem.db` (relative to the repo root). Confirm:

```bash
ls -lh data/stigmem.db
```

If you set `STIGMEM_DB_PATH`, use that path instead.

**3 — Create a Docker volume and copy data in**

```bash
# Create the named volumes Docker Compose expects
docker volume create stigmem__node-a-data
docker volume create stigmem__node-b-data

# Copy your existing database into node-a's volume
# (adjust the source path if your DB was elsewhere)
docker run --rm \
  -v "$(pwd)/data/stigmem.db:/src/stigmem.db:ro" \
  -v "stigmem__node-a-data:/data" \
  busybox cp /src/stigmem.db /data/stigmem.db
```

:::note Volume naming
Docker Compose prefixes volume names with the project name (derived from the directory name). If your repo directory is not named `stigmem`, replace `stigmem__` with `<directory-name>_`.
:::

**4 — Start Docker Compose**

```bash
docker compose up --build -d
```

Verify the node-a data was picked up:

```bash
curl -s 'http://localhost:8765/v1/facts?limit=5' | jq .facts
```

**5 — (Optional) Restore your keypair**

If you had a stable `STIGMEM_FEDERATION_PUBKEY` / `STIGMEM_FEDERATION_PRIVKEY` set in your bare-metal environment, add those same values to the `environment:` section of `docker-compose.yml` before starting, so your node's identity is preserved and existing peers recognize it.

---

## Running without Docker

For development against the source directly:

```bash
cd stigmem/node
uv sync                          # install dependencies
uv run python -m stigmem_node    # starts on http://localhost:8765
```

Interactive Swagger UI: `http://localhost:8765/docs`.

For macOS persistent service (LaunchAgent, no Docker), see [Installation](./getting-started/installation#running-as-a-persistent-service-macos).
