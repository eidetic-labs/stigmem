---
id: installation
title: Installation
sidebar_label: Installation
---

# Installation

Stigmem ships as a Docker image. The quickest way to get a running node is with Docker Compose — no Python installation required.

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker | ≥ 24 |
| Docker Compose (v2) | ≥ 2.20 |

## Single-command install (two-node federation)

```bash
git clone https://github.com/giganomix/stigmem
cd stigmem
docker compose up --build -d
```

This builds the reference node image once and starts two federated nodes:

| Container | Host port | Well-known URL |
|-----------|-----------|----------------|
| `node-a` | 8765 | `http://localhost:8765/.well-known/stigmem` |
| `node-b` | 8766 | `http://localhost:8766/.well-known/stigmem` |

Verify both are healthy:

```bash
curl -s http://localhost:8765/healthz   # {"status":"ok"}
curl -s http://localhost:8766/healthz   # {"status":"ok"}
```

For the full two-node federation walk-through (peer handshake, assert a fact, verify replication), continue to the [Quickstart](./quickstart).

## Docker Compose configuration

`docker-compose.yml` in the repo root sets up the two-node quickstart cluster. Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `STIGMEM_FEDERATION_ENABLED` | `true` | Enable/disable federation pull loop |
| `STIGMEM_NODE_URL` | (container URL) | Public URL of this node (used in PeerDeclarations) |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | Seconds between pull cycles |
| `STIGMEM_SECRET_KEY` | auto-generated | Ed25519 private key seed — persist this across restarts |

To customize, copy `docker-compose.yml` and edit the `environment:` block before running.

## 4-node topology (soak / staging)

For multi-node deployments, use the soak Compose file:

```bash
docker compose -f infra/docker-compose.soak.yml up --build -d
```

This starts four nodes (`node-a` through `node-d` on ports 8765–8768) in a full-mesh topology. See the [4-node topology guide](../guides/federation-4node) for peer wiring, failure injection, and soak metrics.

## Running without Docker (development)

For development against the source directly:

```bash
cd stigmem/node
pip install -e .      # or: uv sync
python -m stigmem_node
```

The node starts on `http://localhost:8000`. Interactive Swagger UI at `http://localhost:8000/docs`.

## Upgrading

```bash
git pull
docker compose up --build -d   # rebuilds the image from updated source
```

Data volumes persist across rebuilds. Run database migrations automatically on startup — there is no manual migration step.

## Teardown

```bash
docker compose down      # stop containers; preserve data volumes
docker compose down -v   # stop and delete all data volumes
```
