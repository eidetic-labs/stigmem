# Script: Federation Walkthrough
<!-- Video 2 of 3 | Target length: ≤ 10 min | Audience: node operators -->

## Video description (YouTube / project channel copy)

> Connect two stigmem nodes, watch facts replicate automatically, and learn how the federation handshake works under the hood — Ed25519 key verification, scope enforcement, and the audit log.
>
> **Timestamps**
> [0:00] Introduction
> [0:45] How federation works (30-second overview)
> [2:00] Start the two-node stack
> [3:15] Inspect the federation handshake
> [4:45] Assert a scoped fact on Node A
> [6:00] Verify replication on Node B
> [7:15] Federation audit log
> [8:15] Scope enforcement — why local facts don't replicate
> [9:15] Wrap-up and next steps

---

## Production notes

- **Recording environment:** two terminal panes side-by-side (left = Node A, right = Node B), 1920×1080.
- Label the left pane "Node A — :8765" and the right pane "Node B — :8766" with colored title bars.
- **Do not** show real API keys — use `dev-key` throughout.
- Each `[PAUSE]` marker = ~2 s silence for edits.

---

## [0:00] Introduction

**[SCREEN: title card — "Stigmem: Federation Walkthrough"]**

> Stigmem is designed to be federated from day one. In this video you'll connect two nodes, watch a fact asserted on Node A appear automatically on Node B, and see how the protocol enforces scope boundaries — so `local` facts never leave the node they were created on.
>
> This builds on video 1. If you haven't run a single node yet, start there first.

---

## [0:45] How federation works — 30-second overview

**[SCREEN: Mermaid diagram — two nodes, arrow from Node A to Node B labeled "pull (every 30 s)", arrow from Node B to Node A labeled "pull (every 30 s)"]**

> Federation in stigmem uses a **pull** model. Each node independently polls its registered peers for new facts. Here's the four-step handshake:
>
> 1. Node A registers with Node B by posting a **PeerDeclaration** — a signed JSON payload containing Node A's `node_id`, public URL, Ed25519 public key, and the scopes it wants to share (spec §6.1).
> 2. Node B fetches Node A's `/.well-known/stigmem` endpoint and verifies the Ed25519 signature.
> 3. Once the peer is `active`, Node B's pull loop fetches new facts from Node A every 30 seconds using a cursor — so restarts and partitions don't cause duplicates.
> 4. Scope filtering happens at the sending node: `local` facts are never included in pull responses.

**[PAUSE]**

> The Docker Compose quickstart automates steps 1–2 with a `federation-init` one-shot container. You don't need to manually sign PeerDeclarations for local development.

---

## [2:00] Start the two-node stack

**[SCREEN: left terminal]**

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
make up
```

> If you already have the repo, `make up` is enough — it's idempotent.

**[SCREEN: left terminal — `docker compose ps`]**

```bash
docker compose ps
```

> Wait about 15 seconds. You want:
> - `node-a` → `healthy`
> - `node-b` → `healthy`
> - `federation-init` → `exited (0)`

**[PAUSE]**

> Exit code zero from `federation-init` means both peer registrations succeeded. If you see exit code 1, run `make logs` and look for the `federation-init` lines — most likely a node wasn't healthy in time.

---

## [3:15] Inspect the federation handshake

**[SCREEN: left terminal]**

> Let's look at the `federation-init` log to see exactly what happened:

```bash
make logs 2>&1 | grep "federation-init"
```

> You'll see output like:

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

> `status=active` means Node B fetched Node A's well-known endpoint, verified the Ed25519 public key against the `declaration_sig` in the PeerDeclaration, and accepted the registration.

**[SCREEN: left terminal — query peers]**

> Confirm from the API:

```bash
# Peers known to Node A
curl -s http://localhost:8765/v1/federation/peers \
  -H 'X-API-Key: dev-key' | jq '[.[] | {node_id, status, allowed_scopes}]'

# Peers known to Node B
curl -s http://localhost:8766/v1/federation/peers \
  -H 'X-API-Key: dev-key' | jq '[.[] | {node_id, status, allowed_scopes}]'
```

> Each node lists the other as a peer with `"status": "active"` and `"allowed_scopes": ["company", "public"]`.

---

## [4:45] Assert a scoped fact on Node A

**[SCREEN: left terminal — "Node A :8765"]**

> Now assert a fact on Node A using `scope: company`. Company-scoped facts replicate to all peers that registered with `company` in their `allowed_scopes`.

```bash
FACT=$(curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "project:acme-platform",
    "relation":   "roadmap:status",
    "value":      {"type": "string", "v": "in-progress"},
    "source":     "agent:planner",
    "confidence": 1.0,
    "scope":      "company"
  }')

echo $FACT | jq '{id, entity, relation, value, scope, hlc}'
```

**[SCREEN: highlight `id` field]**

> Save the `id` — we'll use it to confirm replication. Note the `scope` is `company` and the `hlc` shows the hybrid logical clock tick.

**[PAUSE]**

> Node B's pull loop runs every 30 seconds by default. Rather than wait, let's check the environment variable that controls this:

```bash
docker compose exec node-b env | grep PULL_INTERVAL
# STIGMEM_FEDERATION_PULL_INTERVAL_S=30
```

> For this demo, 35 seconds is the safe wait. You can lower the interval in `docker-compose.yml` for faster iteration in development.

---

## [6:00] Verify replication on Node B

**[SCREEN: right terminal — "Node B :8766"]**

```bash
sleep 35
curl -s 'http://localhost:8766/v1/facts?entity=project:acme-platform&scope=company' \
  -H 'X-API-Key: dev-key' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

**[SCREEN: highlight `source_node` field in output]**

> The fact is there on Node B. Notice `source_node` is set to Node A's `node_id` — this is how the receiving node tracks provenance. The fact's `id` is identical to what we got from Node A: stigmem uses content-addressed IDs, so the same fact always has the same ID regardless of which node you query.

**[PAUSE]**

> **Conflict detection:** if you assert a different value for the same entity/relation/scope on Node B before the Node A fact replicates, stigmem records a `ConflictRecord` and surfaces it in the response. Resolve conflicts with `POST /v1/facts/resolve` — we demonstrate that in video 3 via the MCP adapter.

---

## [7:15] Federation audit log

**[SCREEN: right terminal — "Node B :8766"]**

> Every pull event is recorded in the federation audit log:

```bash
curl -s http://localhost:8766/v1/federation/audit \
  -H 'X-API-Key: dev-key' | jq '.entries[-5:] | .[] | {event, peer_node_id, facts_ingested, cursor, ts}'
```

> You'll see entries with:
> - `event: pull_complete` — a successful pull cycle
> - `facts_ingested` — how many new facts were fetched this cycle
> - `cursor` — the HLC timestamp used as the resume point next cycle

**[PAUSE]**

> The cursor is persisted in the `replication_cursors` table. If Node B restarts, it resumes from the last committed cursor — no re-pull from the beginning, no duplicates. This was verified in a 4-node soak test on 2026-05-02: five facts asserted during a node-stop window were all recovered within 30 s on restart.

---

## [8:15] Scope enforcement

**[SCREEN: left terminal — "Node A :8765"]**

> Let's confirm that `local`-scoped facts do not cross node boundaries:

```bash
# Assert a local fact on Node A
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:session-token",
    "value":      {"type": "string", "v": "secret-abc"},
    "source":     "agent:auth",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq '{id, scope}'
```

**[SCREEN: right terminal — "Node B :8766", wait ~35s]**

```bash
sleep 35
curl -s 'http://localhost:8766/v1/facts?entity=user:alice&relation=memory:session-token' \
  -H 'X-API-Key: dev-key' | jq '.facts | length'
# 0
```

> Zero facts on Node B. The sending node's pull endpoint filters out `local` facts at the query layer before responding to peers. Scope isolation is enforced server-side — there is no client-side honor system.

---

## [9:15] Wrap-up and next steps

**[SCREEN: title card with links]**

> You've seen two stigmem nodes federate automatically: the Ed25519 peer handshake, cursor-based pull, scope enforcement, and the audit log.
>
> Next steps:
> - **MCP adapter** — watch video 3 to use stigmem from Claude Code or any MCP host without writing any HTTP code
> - **4-node topology guide** — `docs.stigmem.dev/docs/guides/federation-4node` — full-mesh setup with failure injection
> - **Spec §6** — the complete federation protocol including peer token format and conflict semantics

**[SCREEN: terminal — teardown]**

```bash
make down
```

---

*End of script — estimated runtime: ~9 min 45 s*
