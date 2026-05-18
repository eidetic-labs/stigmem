---
title: Deployment & Installation
sidebar_label: Install
audience: Operator
---

# Deployment & Installation

**Audience:** node operators installing Stigmem for the first time, or migrating an existing bare-metal install to Docker.

:::tip Operator handbook
For the narrative Docker Compose runbook, see **[Operating Stigmem → Deploy runbooks](../runbooks/deploy-runbooks)**.
:::

The reference node ships as a Docker image. Docker Compose is the supported deployment path in v0.9.0a1 for both local development and single-host production. For development against source, see [Running without Docker](#running-without-docker).

:::caution Other deployment surfaces are deferred
Fly.io, Helm/Kubernetes, systemd, PaaS, and Grafana recipes have been moved to [`experimental/deploy-*/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental) per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md). They remain available as starting points but are unsupported until they pass the [ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). See **[Features → Deployment](../../concepts/features#operations-v090a1-critical-path)** for the full disposition.
:::

## Deploy recipe

The [`deploy/compose/`](https://github.com/eidetic-labs/stigmem/tree/main/deploy/compose) directory contains the supported Docker Compose reference recipe. The sections below cover the Docker Compose path in detail.

---

## Container image tags — which one should I pull? {#image-tags}

The reference node image is published to GHCR at [`ghcr.io/eidetic-labs/stigmem-node`](https://github.com/eidetic-labs/stigmem/pkgs/container/stigmem-node). Several tag flavours are published in parallel — choose the one that matches your stability needs:

| Tag | Stability | Use when… | Example |
|---|---|---|---|
| `:0.9.0aN` (or `:0.9.0bN`, `:1.0.0rcN`, `:1.0.0`) | **Immutable** — never reassigned after publish ([release rule 2](https://github.com/eidetic-labs/stigmem/blob/main/docs/internal/release-cadence.md#rule-2--tags-are-immutable-after-publish)) | **Production.** Reproducible builds, audit-traceable deployments, change-control gates. | `ghcr.io/eidetic-labs/stigmem-node:0.9.0a1` |
| `:0.9.0-alpha.N` / `:0.9.0-beta.N` / `:1.0.0-rc.N` / `:1.0.0` | Immutable | Same artefact as the row above, in semver-strict spelling. Use whichever your tooling prefers. | `ghcr.io/eidetic-labs/stigmem-node:0.9.0-alpha.1` |
| `:latest` | Rolling — advances on every release tag push, never on a plain `main` push | Quickstart, eval, demos. You accept that the image will silently advance when a new release ships. | `ghcr.io/eidetic-labs/stigmem-node:latest` |
| `:edge` | Rolling — advances on every `main` push | Tracking tip-of-trunk between releases. CI-tested but not release-gated. | `ghcr.io/eidetic-labs/stigmem-node:edge` |
| `:<short-sha>` (7-char git short SHA) | Immutable for the lifetime of the tag ([retention](#image-retention) prunes after 90 days) | Forensics, rollback to a specific commit, reproducing a CI failure. | `ghcr.io/eidetic-labs/stigmem-node:b1147a6` |
| `@sha256:<digest>` | Immutable, tamper-evident — fixes the **content**, not the **label** | **Hardened production / supply-chain-conscious deployments.** A retagged or republished image cannot affect a digest pin. | `ghcr.io/eidetic-labs/stigmem-node@sha256:c0038b06…` |

**Quick rule of thumb:**

- Trying things out → `:latest`.
- Running a real workload → `:0.9.0aN` (your current release).
- Auditable production → `@sha256:<digest>` of the version tag you intend to ship.

:::tip Verifying what `:latest` resolves to today
```bash
docker pull ghcr.io/eidetic-labs/stigmem-node:latest
docker inspect --format '{{.RepoDigests}}' ghcr.io/eidetic-labs/stigmem-node:latest
```
The printed digest is what's actually running. Pin to that digest in your Compose / Helm chart for a tamper-evident production deployment.
:::

### Image retention {#image-retention}

The publish workflow tags every release with `:latest` + the version pair (`:0.9.0aN` and `:0.9.0-alpha.N`), and every `main` commit with `:edge` + `:<short-sha>`. To keep the GHCR tag inventory manageable without losing supply-chain auditability:

- **Retained forever:** `:latest`; all version tags (`:0.9.0aN`, `:0.9.0bN`, `:1.0.0rcN`, `:1.0.0`); `:edge`.
- **Retained for 90 days:** short-SHA tags (`:<7-char-sha>`) and their orphan Sigstore signature artefacts (`sha256-…sig`).

Operationally enforced by [`.github/workflows/ghcr-retention.yml`](https://github.com/eidetic-labs/stigmem/blob/main/.github/workflows/ghcr-retention.yml), which runs weekly. The retention policy itself is documented as [release rule 7](https://github.com/eidetic-labs/stigmem/blob/main/docs/internal/release-cadence.md#rule-7--ghcr-image-retention) in `docs/internal/release-cadence.md`.

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
git clone https://github.com/eidetic-labs/stigmem
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

Then follow the [Quickstart](../../get-started/quickstart-tutorial) to complete the federation handshake and assert your first fact.

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

Nodes run on ports 8765–8768. See the [4-node federation guide](../../concepts/federation/federation-4node) for peer wiring, backpressure, and failure injection.

---

## Environment variable reference

All variables use the `STIGMEM_` prefix and can be set in the `environment:` block of `docker-compose.yml`, as system environment variables, or in a `.env` file next to the node binary.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_DB_PATH` | `stigmem.db` | Path to the SQLite database file |
| `STIGMEM_HOST` | `0.0.0.0` | Bind address |
| `STIGMEM_PORT` | `8765` | Port the HTTP server listens on |
| `STIGMEM_NODE_URL` | `http://localhost:8765` | Public URL of this node — included in `PeerDeclaration` payloads (`Spec-05-Federation-Trust`) |
| `STIGMEM_LOG_LEVEL` | `info` | Log verbosity: `debug` · `info` · `warning` · `error` |
| `STIGMEM_AUTH_REQUIRED` | `true` | When `true` (default), every request must carry a valid Bearer token. Set `false` only for single-operator / local-only installs |

### Federation (`Spec-05-Federation-Trust`)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_FEDERATION_ENABLED` | `false` | Enable the pull-replication loop |
| `STIGMEM_FEDERATION_PUBKEY` | `""` | Base64url-encoded Ed25519 public key. Auto-generated on first start if empty; **persist this** |
| `STIGMEM_FEDERATION_PRIVKEY` | `""` | Base64url-encoded Ed25519 private key. Auto-generated on first start if empty; **persist this** |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | Seconds between pull cycles. Peer-advertised `pull_interval_s` takes precedence (`Spec-05-Federation-Trust`) |
| `STIGMEM_FEDERATION_PUSH_ENABLED` | `false` | Enable push replication (experimental; off by default) |
| `STIGMEM_FEDERATION_NONCE_WINDOW_S` | `300` | How long a nonce is retained to block replays (`Spec-11-Replay-Protection`, default = 5 min) |
| `STIGMEM_FEDERATION_ALLOW_TEAM` | `false` | Allow `team`-scoped facts to cross federation boundaries. Requires explicit opt-in; all crossings are audit-logged |

### Decay (`Spec-X9-Decay-Semantics`)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_DECAY_TTL_SECONDS` | `0` | When a sweep runs without an explicit `ttl_seconds`, decay facts older than this. `0` = disabled |
| `STIGMEM_DECAY_MIN_CONFIDENCE` | `0.0` | When a sweep runs without an explicit `min_confidence`, decay facts below this confidence. `0.0` = disabled |

### Attestation & security (`Spec-X6-Source-Attestation`)

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_ATTESTATION_REQUIRED` | `false` | Require a valid Ed25519 attestation token on every `POST /v1/facts`. Enable for multi-tenant or public nodes |
| `STIGMEM_SOURCE_ATTESTATION_MODE` | `off` | Legacy compatibility field for source-attestation mode. Default installs do not enforce source-attestation behavior; use the experimental source-attestation plugin plus explicit plugin gates for runtime enforcement. |

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

For macOS persistent service (LaunchAgent, no Docker), see [Installation](../../get-started/installation#running-as-a-persistent-service-macos).
