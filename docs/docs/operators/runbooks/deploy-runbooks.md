---
title: Deploy Runbooks
sidebar_label: Deploy Runbooks
description: Step-by-step deployment runbook for the Docker Compose reference deployment, the only deployment surface stable in v0.9.0a1.
audience: Operator
---

# Deploy Runbooks

**Audience:** operators deploying Stigmem for the first time or migrating between environments.
**Spec reference:** none — this is operational, not protocol.
**Source recipes:** [`deploy/compose/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy/compose) in the repo.

:::caution Scope in v0.9.0a1
The only **Stable** deployment surface in v0.9.0a1 is the Docker Compose reference deployment. Fly.io, Helm/Kubernetes, systemd, Grafana dashboards, and PaaS templates have been moved to `experimental/deploy-*/` per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md) and are gated by the [ADR-008 reintroduction process](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). Recipes still exist as starting points but are unsupported until they pass ADR-008 promotion. See **[Features → Deployment](../../concepts/features#operations-v090a1-critical-path)** for the full disposition.
:::

---

## Docker Compose

**Best for:** local development, single-server self-hosting, air-gapped environments, evaluation deployments.
**Backend:** SQLite (default) or libSQL.

### Prerequisites

- Docker ≥ 24
- Docker Compose v2 ≥ 2.20

### Step 1 — Clone and configure

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
cp deploy/compose/.env.example deploy/compose/.env
```

Edit `deploy/compose/.env`:

```bash
# Required
STIGMEM_FEDERATION_PUBKEY=<your-pub>
STIGMEM_FEDERATION_PRIVKEY=<your-priv>

# SQLite (default) — no additional vars needed
STIGMEM_STORAGE_BACKEND=sqlite

# libSQL (optional)
# STIGMEM_STORAGE_BACKEND=libsql
# STIGMEM_LIBSQL_URL=libsql://your-db.turso.io
# STIGMEM_LIBSQL_AUTH_TOKEN=<token>
```

To generate a federation keypair:

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes_raw()
pub_bytes  = priv.public_key().public_bytes_raw()
print('STIGMEM_FEDERATION_PRIVKEY=' + base64.urlsafe_b64encode(priv_bytes).decode())
print('STIGMEM_FEDERATION_PUBKEY='  + base64.urlsafe_b64encode(pub_bytes).decode())
"
```

Store both values in your secrets manager — the runtime requires both.

### Step 2 — Start

```bash
docker compose -f deploy/compose/docker-compose.yml up --build -d
```

This starts a single node on port 8765. To start two federated nodes:

```bash
docker compose up --build -d   # uses root docker-compose.yml
```

### Step 3 — Health check

```bash
curl -s http://localhost:8765/healthz
# → {"status":"ok","backend":"sqlite"}
```

### Step 4 — Persist keypairs across container recreation

Add the keypair vars to `deploy/compose/.env` (Step 1) before the first start, or set them in the `environment:` block of your `docker-compose.yml`. Without persisting them, a new container auto-generates a new identity and existing peers will not recognize it.

### Updating

```bash
git pull
docker compose up --build -d
```

Migrations run automatically on startup.

---

## Deferred deployment surfaces

The recipes below are **not part of the v0.9.0a1 supported surface.** They live under `experimental/deploy-*/` and may be reintroduced in a later release once they pass the ADR-008 gates (threat-model delta → ADR → conformance vectors → 30-day operator soak → documentation parity).

| Surface | Recipe location | Status |
|---|---|---|
| Fly.io | [`experimental/deploy-fly/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-fly) | Deferred (no Spec-X assigned) |
| Helm / Kubernetes | [`experimental/deploy-helm/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm) | Deferred (no Spec-X assigned) |
| systemd / bare metal | [`experimental/deploy-systemd/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-systemd) | Deferred (no Spec-X assigned) |
| PaaS (Render, Railway, App Runner, Cloud Run) | [`experimental/deploy-paas/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-paas) | Deferred (no Spec-X assigned) |
| Grafana dashboards | [`experimental/deploy-grafana/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-grafana) | Deferred (no Spec-X assigned) |

Each `experimental/deploy-*/` directory contains a `STATUS.md` describing what would be required to graduate the surface.

---

## After deploying: what's next?

1. **Connect to peers** → [Federation peer setup](./federation-setup)
2. **Schedule backups** → [Backup & restore](./backup-restore)
3. **Set up monitoring** → [Monitoring & debugging](../observability/monitoring)
