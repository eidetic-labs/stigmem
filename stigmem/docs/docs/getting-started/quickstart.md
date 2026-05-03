---
id: quickstart
title: Quickstart — two nodes federating
sidebar_label: Quickstart
---

# Quickstart — two nodes federating

**Goal:** run two stigmem nodes on one machine and watch a fact asserted on Node A replicate automatically to Node B.  
**Time:** under 10 minutes on a machine with Docker and Docker Compose installed.

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | ≥ 24 |
| Docker Compose (v2) | ≥ 2.20 |
| `curl` + `jq` | any recent version |

No Python installation required — the nodes run in containers.

## Step 1 — Clone and start the nodes

```bash
git clone https://github.com/giganomix/stigmem
cd stigmem
docker compose up --build -d
```

This builds the image once and starts two nodes:

| Container | Host port | Internal URL |
|-----------|-----------|--------------|
| `node-a`  | 8765      | `http://node-a:8765` |
| `node-b`  | 8766      | `http://node-b:8765` |

Wait for both nodes to report healthy (about 10–15 s):

```bash
docker compose ps
```

You should see `healthy` for both services. You can also check directly:

```bash
curl -s http://localhost:8765/healthz   # node-a
curl -s http://localhost:8766/healthz   # node-b
```

Both should return `{"status":"ok"}`.

## Step 2 — Inspect node metadata

Each node exposes its identity and Ed25519 public key:

```bash
curl -s http://localhost:8765/.well-known/stigmem | jq '{node_id, federation_pubkey}'
curl -s http://localhost:8766/.well-known/stigmem | jq '{node_id, federation_pubkey}'
```

Note that each node auto-generates a unique `node_id` and keypair on first start.

## Step 3 — Peer handshake (both directions)

The federation pull protocol (spec §6.1, §6.3) requires each node to trust the other as an authenticated peer before it will serve facts. You need two registrations: Node A registers with Node B, and Node B registers with Node A.

The `stigmem federation register-peer` command signs the `PeerDeclaration` with the local node's Ed25519 private key and POSTs it to the remote node.

**Register Node A with Node B** (run inside the node-a container):

```bash
docker exec stigmem-node-a-1 \
  stigmem federation register-peer \
    --local-url  http://node-a:8765 \
    --remote-url http://node-b:8765 \
    --scopes company,public
```

**Register Node B with Node A** (run inside the node-b container):

```bash
docker exec stigmem-node-b-1 \
  stigmem federation register-peer \
    --local-url  http://node-b:8765 \
    --remote-url http://node-a:8765 \
    --scopes company,public
```

Both should print:

```
peer registered and verified (peer_id=<uuid>)
```

The `active` status means the receiving node fetched the sender's `/.well-known/stigmem`, verified the pubkey matches, and confirmed the Ed25519 signature.

:::tip Container name
Docker Compose names containers `<project>-<service>-<replica>`. If your clone directory is `stigmem`, the containers are `stigmem-node-a-1` and `stigmem-node-b-1`. Verify with `docker compose ps`.
:::

## Step 4 — Assert a fact on Node A

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

## Step 5 — Verify cross-node replication

Node B pulls facts from Node A on the background pull interval (default 30 s). Either wait 30 seconds or trigger an immediate check by querying Node B:

```bash
# Wait up to 35 s for the pull loop to fire, then query Node B:
sleep 35
curl -s 'http://localhost:8766/v1/facts?entity=user:alice&scope=company' \
  -H 'Content-Type: application/json' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

The fact asserted on Node A (`localhost:8765`) should appear on Node B (`localhost:8766`) with a `source_node` field pointing to Node A's `node_id`.

:::info Pull interval
The default pull interval is 30 s (`STIGMEM_FEDERATION_PULL_INTERVAL_S`). For testing you can lower it to 5 s in `docker-compose.yml`.
:::

## Step 6 — Federation audit log

Every pull event and peer action is recorded:

```bash
curl -s http://localhost:8766/v1/federation/audit | jq '.entries[-3:]'
```

---

## What's next

- [Assert facts guide](../guides/asserting-facts.md) — full fact schema, scopes, and TTLs
- [Federation guide](../guides/federation.md) — scope enforcement, conflict resolution, production keys
- [API reference](../api-reference/index.md) — full endpoint reference
- [Architecture](../architecture/index.md) — HLC, PeerDeclaration internals, spec §6

## Teardown

```bash
docker compose down -v   # stops containers and deletes node data volumes
```
