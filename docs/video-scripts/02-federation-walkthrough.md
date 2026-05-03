# Script 2 — Federation Walkthrough

**Target duration:** ~9 min 45 s  
**Audience:** Node operator connecting two stigmem nodes  
**Format:** Screen-recording, terminal split-view (two panes), narrated  

---

## YouTube / channel description block

```
stigmem — Federation Walkthrough (v1.0)

Connect two stigmem nodes, watch facts replicate automatically,
inspect the pull-loop handshake, and demo scope enforcement and conflict resolution.

Timestamps:
0:00 — What federation is and why it matters
1:15 — Starting the two-node stack
2:30 — Inspecting the automatic peer handshake
4:00 — Assert a company-scoped fact on Node A
4:45 — Wait for replication and verify on Node B
6:00 — Conflict detection and resolution
7:30 — Scope enforcement: local facts stay local
8:30 — Federation audit log
9:15 — What's next

GitHub: https://github.com/Eidetic-Labs/stigmem
Docs: https://stigmem.dev/docs/guides/federation
```

---

## Production notes

- Resolution: 1920×1080
- Use a two-pane terminal split: left = Node A commands, right = Node B commands
- Mask or substitute any real API keys before recording
- **Section [4:45] — `sleep 35` b-roll cut:** The script calls `sleep 35` while waiting for the pull interval. Do NOT hold on the idle terminal for 35 s of dead air. At the `sleep 35` command, cut to the static Mermaid pull-loop diagram (see `docs/docs/architecture/index.md`), narrate the pull cycle over the diagram, then cut back to the terminal when the query fires. Resume narration from the query output.

---

## Script

### [0:00] What federation is and why it matters

**[Screen: architecture diagram from docs/docs/architecture/index.md or Mermaid diagram]**

> "Federation is stigmem's mechanism for synchronizing facts across multiple nodes. Each node maintains its own local fact store. The federation protocol propagates facts bidirectionally so every peer eventually holds a consistent view of each allowed scope."

> "The key design choices: pull-based replication — nodes pull from their peers on a configurable interval, no push required. Identity via Ed25519 — each node signs a `PeerDeclaration` that peers verify before accepting. And scope enforcement — only facts in agreed scopes cross the boundary. A `local`-scoped fact never leaves its node, regardless of what peers are configured."

> "In the Docker Compose setup we ship, all of this is wired automatically. Let me show you."

---

### [1:15] Starting the two-node stack

**[Screen: terminal]**

> "From the repo root, start the stack."

```bash
git clone https://github.com/Eidetic-Labs/stigmem   # skip if already cloned
cd stigmem
make up
```

> "`make up` starts three services: `node-a` on port 8765, `node-b` on 8766, and `federation-init` — a one-shot container that wires the two nodes together automatically."

```bash
docker compose ps
```

> "Wait until `node-a` and `node-b` show `healthy` and `federation-init` shows `exited (0)`. The `exited (0)` is the success indicator — the init script ran, registered the peers in both directions, and shut down cleanly."

---

### [2:30] Inspecting the automatic peer handshake

**[Screen: terminal — run make logs, filter for federation-init output]**

```bash
make logs 2>&1 | grep "federation-init"
```

> "The init log shows exactly what happened: it fetched each node's `node_id` and `federation_pubkey` from the SQLite database, constructed a signed `PeerDeclaration` for each direction, and POSTed it to the remote node."

> "`status=active` in the log confirms each remote node fetched our `.well-known/stigmem`, verified the Ed25519 signature on the declaration, and accepted the peer — per spec §6.1."

> "Confirm the live peer status directly on both nodes."

```bash
# Left pane — Node A
curl -s http://localhost:8765/v1/federation/peers | jq '.[].{node_id, status}'

# Right pane — Node B
curl -s http://localhost:8766/v1/federation/peers | jq '.[].{node_id, status}'
```

> "Both return `status: active`. The federation link is live."

---

### [4:00] Assert a company-scoped fact on Node A

**[Screen: left pane — Node A terminal]**

> "Now let's put data through the link. I'll assert a company-scoped fact on Node A."

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "agent:assistant",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "concise replies"},
    "source":     "agent:orchestrator",
    "confidence": 0.9,
    "scope":      "company"
  }' | jq '{id, entity, value, scope}'
```

> "Company scope — this fact should replicate to Node B. Note the typed value object: `{\"type\": \"string\", \"v\": \"concise replies\"}`. That's the required format."

**[Highlight the `id` in the output]**

> "Note that `id` — we'll query for it on Node B."

---

### [4:45] Wait for replication and verify on Node B

**[Screen: terminal — type `sleep 35` and immediately cut to b-roll]**

```bash
sleep 35
```

> **[CUT TO: Mermaid pull-loop diagram — narrate over diagram]**

> "While we wait for the pull interval, here's what's happening behind the scenes. Node B's pull loop wakes every 30 seconds — that's `STIGMEM_FEDERATION_PULL_INTERVAL_S`. It calls `GET /v1/federation/facts` on Node A, presenting the peer token it received during registration. Node A returns new facts since the last cursor position. Node B ingests them into its local store and advances the cursor. The cursor is persisted in the `replication_cursors` table, so even a restart won't cause re-delivery of facts."

> **[CUT BACK TO: right pane — Node B terminal, `sleep` has finished]**

```bash
curl -s 'http://localhost:8766/v1/facts?entity=agent:assistant&scope=company' \
  -H 'X-API-Key: dev-key' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

> "There it is on Node B. Notice the `source_node` field — it points to Node A's `node_id`, telling you this fact originated remotely. That provenance is preserved through replication."

---

### [6:00] Conflict detection and resolution

**[Screen: left pane — assert a conflicting fact on Node A]**

> "What happens when two nodes assert different values for the same entity–relation–scope? Stigmem detects the conflict on ingest and surfaces it."

> "Let me assert a conflicting preference on Node A — same entity, relation, and scope, but a different value."

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "agent:assistant",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "verbose replies"},
    "source":     "agent:reviewer",
    "confidence": 0.8,
    "scope":      "company"
  }' | jq '{id, value}'
```

> "After the next pull, Node B will detect a conflict. List conflicts on Node B."

```bash
sleep 35 && \
curl -s http://localhost:8766/v1/conflicts \
  -H 'X-API-Key: dev-key' | jq '.[0] | {conflict_id, entity, relation}'
```

> "There's the conflict record. Resolve it by nominating the winning fact."

```bash
CONFLICT_ID=$(curl -s http://localhost:8766/v1/conflicts \
  -H 'X-API-Key: dev-key' | jq -r '.[0].conflict_id')

WINNING_ID=$(curl -s http://localhost:8766/v1/conflicts \
  -H 'X-API-Key: dev-key' | jq -r '.[0].facts[0].id')

curl -s -X POST "http://localhost:8766/v1/conflicts/${CONFLICT_ID}/resolve" \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d "{
    \"winning_fact_id\": \"${WINNING_ID}\",
    \"resolution_note\": \"Original preference confirmed by reviewer\"
  }" | jq '{conflict_id, status}'
```

> "The resolve endpoint is `POST /v1/conflicts/{conflict_id}/resolve` — note the conflict ID is in the path, not the request body. Resolution writes a new fact with a `stigmem:resolves` relation that marks the conflict as settled."

---

### [7:30] Scope enforcement: local facts stay local

**[Screen: left pane — assert a local-scoped fact on Node A]**

> "Scope enforcement is a hard boundary. Let me prove it."

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "agent:assistant",
    "relation":   "session:scratch",
    "value":      {"type": "string", "v": "draft thoughts"},
    "source":     "agent:assistant",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq '{id, scope}'
```

> "Now wait for the pull interval and query Node B for that entity."

```bash
sleep 35 && \
curl -s 'http://localhost:8766/v1/facts?entity=agent:assistant&relation=session:scratch' \
  -H 'X-API-Key: dev-key' | jq '.facts | length'
```

> "Zero. The `local`-scoped fact never left Node A. This is the core privacy boundary — agent scratch state and working memory stay on the local node regardless of federation configuration."

---

### [8:30] Federation audit log

**[Screen: terminal]**

> "Every pull event, peer registration, conflict detection, and scope check is recorded in the audit log."

```bash
curl -s http://localhost:8765/v1/federation/audit | jq '.entries[-5:]'
```

> "You can filter by event type."

```bash
curl -s 'http://localhost:8765/v1/federation/audit?event_type=pull' | \
  jq '.entries[-3:] | .[] | {timestamp, peer_node_id, fact_count, cursor}'
```

> "Healthy replication looks like a steady stream of `pull` events with monotonically increasing cursors and a non-zero `fact_count` when new facts were available. A stalled cursor with zero facts for many cycles usually means a network issue or an expired peer token."

---

### [9:15] What's next

**[Screen: docs site]**

> "That covers the core federation workflow: automatic peering, pull-based replication, conflict detection and resolution, and scope enforcement."

> "For advanced topics: the federation guide in the docs covers manual key management, production TLS setup, key rotation, and the 4-node full-mesh topology with failure injection."

> "Next up: the MCP adapter video, which shows how to wire stigmem into Claude Code so your agents can assert and query facts directly from their context."

> "Thanks for watching."

---

*End of Script 2*
