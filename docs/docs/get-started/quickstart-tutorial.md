---
title: Quickstart — two nodes federating
sidebar_label: Federation Tutorial
slug: quickstart-tutorial
---

# Quickstart — two nodes federating

**Goal:** run two stigmem nodes on one machine and watch a fact asserted on Node A replicate automatically to Node B.  
**Time:** under 5 minutes on a machine with Docker and Docker Compose installed.

Federation peer registration is **automatic** — no manual `docker exec` commands needed.

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | ≥ 24 |
| Docker Compose (v2) | ≥ 2.20 |
| `curl` + `jq` | any recent version |
| `helm` | ≥ 3.14 (Kubernetes install only) |

No Python installation required — the nodes run in containers.

## Step 1 — Clone and start the stack

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
make up
```

`make up` runs `docker compose up --build -d` (both `docker-compose.yml` and `compose.override.yml`), which starts three services:

| Service | Role | Host port |
|---------|------|-----------|
| `node-a` | stigmem node | 8765 |
| `node-b` | stigmem node | 8766 |
| `federation-init` | one-shot peer wirer | — |

**Startup ordering:** `node-b` has `depends_on: node-a: condition: service_healthy` — it does not start until `node-a` passes its `/healthz` check. `federation-init` waits for _both_ nodes to be healthy before running.

## Step 2 — Verify automatic federation

Wait about 15 s, then check service status:

```bash
docker compose ps
```

Expected: `node-a` and `node-b` show `healthy`; `federation-init` shows `exited (0)`.

Inspect the init log:

```bash
make logs
```

Look for:

```
federation-init-1  | federation-init: starting
federation-init-1  |   node-a  id=abc12345…  pub=abc123def456…
federation-init-1  |   node-b  id=def67890…  pub=def456ghi789…
federation-init-1  |   registering node-a → node-b…
federation-init-1  |     status=active
federation-init-1  |   registering node-b → node-a…
federation-init-1  |     status=active
federation-init-1  | federation-init: done
```

`status=active` confirms the receiving node fetched the sender's `/.well-known/stigmem`, verified the Ed25519 public key, and accepted the signed `PeerDeclaration` (`Spec-05-Federation-Trust`).

Confirm directly:

```bash
curl -s http://localhost:8765/v1/federation/peers | jq '.[].status'  # "active"
curl -s http://localhost:8766/v1/federation/peers | jq '.[].status'  # "active"
```

## Step 3 — Assert a fact on Node A

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "company"
  }' | jq '{id, entity, relation, value, scope}'
```

Record the `id` from the response — you'll use it to confirm replication.

## Step 4 — Verify cross-node replication

Node B pulls facts from Node A on the background pull interval (default 30 s):

```bash
sleep 35
curl -s 'http://localhost:8766/v1/facts?entity=user:alice&scope=company' \
  -H 'Content-Type: application/json' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

The fact asserted on Node A (`localhost:8765`) should appear on Node B (`localhost:8766`) with a `source_node` field pointing to Node A's `node_id`.

:::info Pull interval
The default pull interval is 30 s (`STIGMEM_FEDERATION_PULL_INTERVAL_S`). Lower it in `docker-compose.yml` for testing.
:::

## Step 5 — Federation audit log

Every pull event and peer action is recorded:

```bash
curl -s http://localhost:8766/v1/federation/audit | jq '.entries[-3:]'
```

---

## Makefile targets

| Target | What it does |
|--------|-------------|
| `make up` | Build and start the stack detached. Dev overlay (`compose.override.yml`) applied automatically. |
| `make down` | Stop containers; keep data volumes. |
| `make logs` | Tail logs from all services (`docker compose logs -f`). |
| `make verify` | End-to-end smoke test — starts nodes, asserts a fact, verifies replication, tears down. |

To run without the dev overlay (production-only):

```bash
make up COMPOSE_FLAGS="-f docker-compose.yml"
```

## Development profile (live-reload)

`compose.override.yml` is automatically merged by `docker compose` and `make up`. It:

- Sets `STIGMEM_LOG_LEVEL=debug` on both nodes.
- Mounts `./node/src` into the containers (read-only) so the running process sees source changes.
- Overrides both node entrypoints to `uvicorn --reload` so any `.py` change under `node/src/` restarts the node process inside the container within ~1 s.

To run without live-reload:

```bash
make up COMPOSE_FLAGS="-f docker-compose.yml"
# or
docker compose -f docker-compose.yml up --build -d
```

:::caution Helm / Kubernetes is deferred in v0.9.0a1
The Helm chart has been moved to [`experimental/deploy-helm/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm) per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md). It remains buildable but is unsupported until the [ADR-008 reintroduction gates](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) pass. The supported v0.9.0a1 deployment surface is Docker Compose (above).
:::

:::tip Key generation
Generate Ed25519 keypairs with `python3 infra/soak/keys.py`. Keys must be base64url-encoded without padding (`=`).
:::

## federation-init internals (for operators)

`federation-init` is a one-shot init container defined in `docker-compose.yml`. It runs `scripts/federation-init.py` and exits.

### How it works

1. **Wait for node DBs** — polls each node's SQLite DB (`/data/node-a/stigmem.db`, `/data/node-b/stigmem.db`) every 2 s until `federation_pubkey`, `federation_privkey`, and `node_id` rows are present in `node_meta` (up to 30 retries = 60 s). The DBs are mounted read-only via named volumes.

2. **Sign PeerDeclarations** — for each direction (A→B, B→A), constructs a `PeerDeclaration` with `node_id`, `node_url`, `federation_pubkey`, `allowed_scopes`, and `signed_at` (UTC). Produces canonical JSON (sorted keys, no whitespace) and signs with Ed25519 (`Spec-05-Federation-Trust`).

3. **Register peers** — POSTs the signed payload to `POST /v1/federation/peers` on the remote node. HTTP 409 means already registered and is silently skipped.

4. **Exit** — exits 0 on success, 1 if any registration failed. `restart: on-failure` in `docker-compose.yml` retries on transient errors.

### Environment overrides

| Variable | Default | Purpose |
|----------|---------|---------|
| `NODE_A_DB` | `/data/node-a/stigmem.db` | Path to node-a's SQLite DB |
| `NODE_B_DB` | `/data/node-b/stigmem.db` | Path to node-b's SQLite DB |
| `NODE_A_URL` | `http://node-a:8765` | Node A internal URL |
| `NODE_B_URL` | `http://node-b:8765` | Node B internal URL |
| `SCOPES` | `company,public` | Comma-separated allowed scopes |

### Idempotency

Re-running `federation-init` (e.g., after `make down && make up`) is safe — HTTP 409 on already-registered peers is silently skipped, and the service exits 0 as long as both nodes are reachable.

---

## What's next

- [Assert facts guide](../concepts/facts/asserting-facts.md) — full fact schema, scopes, and TTLs
- [Federation guide](../concepts/federation/) — scope enforcement, conflict resolution, production keys
- [4-node topology](../concepts/federation/federation-4node.md) — full-mesh setup, failure injection, soak metrics
- [API reference](../reference/api/index.md) — full endpoint reference
- [Architecture](../reference/architecture/index.md) — HLC and PeerDeclaration internals

## Teardown

```bash
make down              # stop containers; keep data volumes
docker compose down -v # stop and delete all data volumes
```
