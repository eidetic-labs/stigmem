---
title: Deploy Runbooks
sidebar_label: Deploy Runbooks
description: Step-by-step deployment runbooks for Fly.io, Docker Compose, Helm/Kubernetes, systemd, and PaaS environments.
audience: Operator
---

# Deploy Runbooks

**Audience:** operators deploying Stigmem for the first time or migrating between environments.  
**Spec reference:** none — this is operational, not protocol.  
**Source recipes:** [`deploy/`](https://github.com/Eidetic-Labs/stigmem/tree/main/deploy) in the repo.

Pick the environment that matches your infrastructure, then follow the runbook end to end. Each runbook ends with a health check and a pointer to next steps.

---

## Fly.io

**Best for:** personal nodes, small teams, zero-config TLS, minimal ops overhead.  
**Backend:** libSQL/Turso (recommended) or SQLite + persistent volume.

### Prerequisites

- `flyctl` installed and authenticated (`fly auth login`)
- Turso CLI (if using libSQL): `curl -sSfL https://get.tur.so/install.sh | bash`

### Step 1 — Create the app

```bash
cd deploy/fly
fly launch --no-deploy --name stigmem-prod --region iad
```

Fly will prompt for a region. Choose the region closest to your users.

### Step 2 — Attach a persistent volume (SQLite path only; skip for libSQL)

```bash
fly volumes create stigmem_data --region iad --size 10
```

Then confirm `fly.toml` has the mount:

```toml
[[mounts]]
  source      = "stigmem_data"
  destination = "/app/data"
```

### Step 3 — Generate a federation keypair

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

Store the output in your secrets manager — you'll need both values below.

### Step 4 — Set secrets

```bash
# Always set
fly secrets set \
  STIGMEM_FEDERATION_PUBKEY="<your-pub>" \
  STIGMEM_FEDERATION_PRIVKEY="<your-priv>"

# libSQL / Turso
TURSO_URL=$(turso db show stigmem-prod --url)
TURSO_TOKEN=$(turso db tokens create stigmem-prod)
fly secrets set \
  STIGMEM_STORAGE_BACKEND=libsql \
  STIGMEM_LIBSQL_URL="$TURSO_URL" \
  STIGMEM_LIBSQL_AUTH_TOKEN="$TURSO_TOKEN"

# SQLite (alternative)
fly secrets set STIGMEM_STORAGE_BACKEND=sqlite
```

### Step 5 — Deploy

```bash
fly deploy
```

### Step 6 — Health check

```bash
fly status
curl -s "https://$(fly status --json | jq -r '.Hostname')/healthz"
# → {"status":"ok","backend":"libsql"}
```

### Updating

```bash
git pull
fly deploy
```

Migrations run automatically on startup.

---

## Docker Compose

**Best for:** local development, single-server self-hosting, air-gapped environments.  
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

---

## Helm / Kubernetes

**Best for:** enterprise Kubernetes deployments, multi-tenant clusters, team-managed infrastructure.  
**Backend:** Postgres (recommended) or libSQL.

### Prerequisites

- `helm` ≥ 3.12 installed
- Kubernetes cluster with `kubectl` access
- Postgres instance available (or use `bitnami/postgresql` subchart)

### Step 1 — Add the Stigmem Helm repo

```bash
helm repo add stigmem https://helm.stigmem.dev
helm repo update
```

### Step 2 — Create a values override file

```yaml
# values-prod.yaml
image:
  tag: "latest"  # pin to a specific release tag in production

config:
  storageBackend: postgres
  postgresDsn: ""  # set via secret below — do not inline credentials

federation:
  enabled: true
  pubKey: ""   # set via secret
  privKey: ""  # set via secret

service:
  type: ClusterIP
  port: 8765

ingress:
  enabled: true
  host: stigmem.your-domain.com
  tls: true
```

### Step 3 — Create secrets

```bash
kubectl create secret generic stigmem-secrets \
  --from-literal=STIGMEM_POSTGRES_DSN="postgresql://user:pass@host:5432/stigmem" \
  --from-literal=STIGMEM_FEDERATION_PUBKEY="<your-pub>" \
  --from-literal=STIGMEM_FEDERATION_PRIVKEY="<your-priv>"
```

Reference the secret in `values-prod.yaml`:

```yaml
envFrom:
  - secretRef:
      name: stigmem-secrets
```

### Step 4 — Install

```bash
helm install stigmem stigmem/stigmem \
  --namespace stigmem \
  --create-namespace \
  --values values-prod.yaml
```

### Step 5 — Health check

```bash
kubectl -n stigmem get pods
kubectl -n stigmem port-forward svc/stigmem 8765:8765
curl -s http://localhost:8765/healthz
# → {"status":"ok","backend":"postgres"}
```

### Upgrading

```bash
helm upgrade stigmem stigmem/stigmem \
  --namespace stigmem \
  --values values-prod.yaml
```

The node runs migrations on startup — no pre-upgrade migration job required.

---

## systemd (bare metal / sovereign)

**Best for:** air-gapped deployments, sovereign infrastructure, bare-metal servers without Docker.  
**Backend:** SQLite (file) or self-hosted libSQL sqld.

### Prerequisites

- Linux with systemd
- Python ≥ 3.11 and `uv` installed (`pip install uv`)
- `stigmem-node` package installed (`uv pip install stigmem-node`)

### Step 1 — Install the node binary

```bash
uv pip install stigmem-node

# Verify
stigmem --version
```

### Step 2 — Create a data directory and config

```bash
sudo mkdir -p /var/lib/stigmem
sudo chown stigmem:stigmem /var/lib/stigmem   # create a dedicated user if not present
sudo useradd --system --no-create-home --shell /usr/sbin/nologin stigmem
sudo chown stigmem:stigmem /var/lib/stigmem
```

Create `/etc/stigmem/env`:

```bash
STIGMEM_STORAGE_BACKEND=sqlite
STIGMEM_DB_PATH=/var/lib/stigmem/stigmem.db
STIGMEM_PORT=8765
STIGMEM_HOST=127.0.0.1
STIGMEM_NODE_URL=https://stigmem.your-domain.com
STIGMEM_FEDERATION_PUBKEY=<your-pub>
STIGMEM_FEDERATION_PRIVKEY=<your-priv>
STIGMEM_LOG_LEVEL=info
```

Restrict permissions:

```bash
sudo chmod 600 /etc/stigmem/env
sudo chown stigmem:stigmem /etc/stigmem/env
```

### Step 3 — Create the systemd service

Copy `deploy/systemd/stigmem.service` from the repo, or create `/etc/systemd/system/stigmem.service`:

```ini
[Unit]
Description=Stigmem reference node
After=network.target

[Service]
User=stigmem
Group=stigmem
EnvironmentFile=/etc/stigmem/env
ExecStart=/usr/local/bin/stigmem serve
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Step 4 — Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable stigmem
sudo systemctl start stigmem
```

### Step 5 — Health check

```bash
systemctl status stigmem
curl -s http://localhost:8765/healthz
# → {"status":"ok","backend":"sqlite"}
journalctl -u stigmem -n 50
```

### Updating

```bash
uv pip install --upgrade stigmem-node
stigmem migrate   # run as the stigmem user or with appropriate env
sudo systemctl restart stigmem
```

---

## PaaS (Render, Railway, AWS App Runner, GCP Cloud Run)

**Best for:** operators who want managed infrastructure without Kubernetes complexity.  
**Backend:** Postgres (recommended via managed add-on) or libSQL.

These platforms share a common pattern: container-based deployment with environment variables injected at runtime.

### Environment variables

Set these in your platform's environment/secrets UI:

```bash
STIGMEM_STORAGE_BACKEND=postgres
STIGMEM_POSTGRES_DSN=postgresql://user:pass@host:5432/stigmem

# OR libSQL
STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_LIBSQL_URL=libsql://your-db.turso.io
STIGMEM_LIBSQL_AUTH_TOKEN=<token>

# Always
STIGMEM_FEDERATION_PUBKEY=<your-pub>
STIGMEM_FEDERATION_PRIVKEY=<your-priv>
STIGMEM_NODE_URL=https://your-app.platform-domain.com
```

### Dockerfile

Use the image from the repo root, or reference `ghcr.io/eidetic-labs/stigmem:latest`. The image exposes port 8765 and runs `stigmem serve` by default.

### Health check path

Configure your platform's health check to hit `GET /healthz`. The response is:

```json
{"status": "ok", "backend": "postgres"}
```

### Platform-specific notes

| Platform | Postgres add-on | Notes |
|---|---|---|
| Render | Render Postgres | Use the Internal Connection String from the Postgres service dashboard |
| Railway | Railway Postgres | Use `$DATABASE_URL` variable injected automatically |
| AWS App Runner | RDS via VPC connector | Requires a VPC connector for private RDS access |
| GCP Cloud Run | Cloud SQL via socket | Use Cloud SQL Auth Proxy sidecar or Cloud SQL connector |

---

## After deploying: what's next?

1. **Connect to peers** → [Federation peer setup](./federation-setup)
2. **Schedule backups** → [Backup & restore](./backup-restore)
3. **Set up monitoring** → [Monitoring & debugging](../observability/monitoring)
4. **Estimate costs** → [Cost calculator](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/billing)
