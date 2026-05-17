---
title: Quickstart — two nodes federating
sidebar_label: Federation Tutorial
slug: quickstart-tutorial
---

# Quickstart — two nodes federating

**Goal:** run two stigmem nodes on one machine and watch a fact asserted on Node A replicate automatically to Node B.  
**Time:** under 5 minutes on a machine with Docker and Docker Compose installed.

The fastest reproducible path is `make demo`. It starts two local nodes,
registers them as peers, asserts a fact on node A, waits for pull replication,
checks node B, prints recent audit entries, and tears the stack down.

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
make demo
```

`make demo` runs `scripts/quickstart-verify.sh`. By default it uses the pinned
GHCR image from `docker-compose.yml` for speed. Contributors who need to prove
the local working tree can set `DEMO_BUILD=1 make demo` to force a local image
build first.

The quickstart starts two services:

| Service | Role | Host port |
|---------|------|-----------|
| `node-a` | stigmem node | 8765 |
| `node-b` | stigmem node | 8766 |

If ports 8765/8766 are busy, the demo script automatically selects free host
ports starting at 18765.

## Step 2 — Verify federation

The demo prints each step as it runs:

```text
Step 0 — docker compose up -d
Step 2 — Inspecting /.well-known/stigmem
Step 3 — Peer handshake (both directions)
Step 4 — Asserting fact on node-a
Step 5 — Waiting 35s for federation pull
Step 6 — Federation audit log on node-b
```

`quickstart smoke test PASSED` confirms the receiving node accepted the signed
peer declaration, pull replication moved the fact, and the audit endpoint stayed
readable.

To keep the demo stack running for manual inspection:

```bash
KEEP_UP=1 make demo
```

## Step 3 — Manual fact assertion

With `KEEP_UP=1`, assert another fact on node A:

```bash
curl -s -X POST "${NODE_A:-http://localhost:8765}/v1/facts" \
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
curl -s "${NODE_B:-http://localhost:8766}/v1/facts?entity=user:alice&scope=company" \
  -H 'Content-Type: application/json' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

The fact asserted on Node A (`localhost:8765`) should appear on Node B (`localhost:8766`) with a `source_node` field pointing to Node A's `node_id`.

:::info Pull interval
The default pull interval is 30 s (`STIGMEM_FEDERATION_PULL_INTERVAL_S`). Lower it in `docker-compose.yml` for testing.
:::

## Step 5 — Federation audit log

Every pull event and peer action is recorded:

```bash
curl -s "${NODE_B:-http://localhost:8766}/v1/federation/audit" | jq '.entries[-3:]'
```

---

## Makefile targets

| Target | What it does |
|--------|-------------|
| `make demo` | End-to-end two-node smoke test: start, peer, assert, replicate, audit, tear down. |
| `DEMO_BUILD=1 make demo` | Same demo, but force-build the local working tree image. |
| `KEEP_UP=1 make demo` | Leave the stack running after the demo for manual inspection. |
| `make demo-attack` | Malicious-peer rejection demo: unauthorized scope write and source forgery. |

For ad hoc compose work, use `docker compose up -d` and `docker compose down -v`.

:::caution Helm / Kubernetes is deferred in v0.9.0a1
The Helm chart has been moved to [`experimental/deploy-helm/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm) per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md). It remains buildable but is unsupported until the [ADR-008 reintroduction gates](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) pass. The supported v0.9.0a1 deployment surface is Docker Compose (above).
:::

:::tip Key generation
Generate Ed25519 keypairs with `python3 infra/soak/keys.py`. Keys must be base64url-encoded without padding (`=`).
:::

## Peer registration internals

The demo registers each direction by running the CLI inside each node container:

```bash
stigmem federation register-peer \
  --local-url  http://node-a:8765 \
  --remote-url http://node-b:8765 \
  --scopes company,public
```

The receiving node fetches the sender's `/.well-known/stigmem`, verifies the
federation public key, and stores an active peer record. HTTP 409 means a prior
run already registered that peer; the demo clears volumes before starting so the
handshake is deterministic.

### Environment overrides

| Variable | Default | Purpose |
|----------|---------|---------|
| `STIGMEM_NODE_A_HOST_PORT` | first free port at/above 18765 | Node A host port for the demo script |
| `STIGMEM_NODE_B_HOST_PORT` | next free port after node A | Node B host port for the demo script |
| `PULL_WAIT_S` | `35` | Seconds to wait before checking node B for replicated facts |
| `KEEP_UP` | `0` | Set to `1` to leave containers running after the demo |
| `DEMO_BUILD` | `0` | Set to `1` to force `docker compose up --build -d` |

### Idempotency

Re-running `make demo` is safe. The script starts by running
`docker compose down -v --remove-orphans` so stale peer registrations, test
facts, and volumes do not affect the next handshake.

---

## What's next

- [Assert facts guide](../concepts/facts/asserting-facts.md) — full fact schema, scopes, and TTLs
- [Federation guide](../concepts/federation/) — scope enforcement, conflict resolution, production keys
- [4-node topology](../concepts/federation/federation-4node.md) — full-mesh setup, failure injection, soak metrics
- [API reference](../reference/api/index.md) — full endpoint reference
- [Architecture](../reference/architecture/index.md) — HLC and PeerDeclaration internals

## Teardown

```bash
docker compose down -v # stop and delete all data volumes
```
