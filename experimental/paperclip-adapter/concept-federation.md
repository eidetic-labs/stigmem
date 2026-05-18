---
title: Paperclip — Federation Integration
sidebar_label: Paperclip Federation
audience: Integrator
---

# Paperclip — Federation Integration Guide

**Audience:** Paperclip operators deploying stigmem as the persistent fact store for a Paperclip agent fleet, including connecting a company-managed node to a federated peer.

---

## Integration scope

Stigmem provides a **shared cognitive layer** that sits above the Paperclip orchestration layer.
It is not a replacement for Paperclip task state — it extends it:

| Paperclip owns | Stigmem owns |
|----------------|-------------|
| Issue lifecycle, checkout, comments | Cross-heartbeat fact history |
| Agent assignments and routing | Company-wide preferences and constraints |
| Run logs and CI output | Architectural decisions with provenance |
| Real-time heartbeat wakes | Decay-aware working memory |

The canonical integration model is:

- **One shared stigmem node** per Paperclip company — all agents read from and write to the same node.
- **Federation** connects that node to an upstream peer (e.g., an Eidetic Labs reference node, a partner company's node, or a second region for resilience).
- **The Paperclip adapter** (`adapters/paperclip/`) wires agent heartbeats to the node: pull context on start, push lifecycle facts at checkout/block/done.
- **The MCP server** (`adapters/mcp/`) exposes stigmem as five Claude Code tools agents can call directly in their reasoning loop.

---

## Architecture

```
                     FEDERATION
  Eidetic Labs node ◄────────────► Company stigmem node  (shared)
  (or any peer)          pull/push       │
                                         │  HTTP
                         ┌───────────────┤
                         │               │
                   Agent A (CTO)   Agent B (CEO)
                   heartbeat        heartbeat
                         │               │
                         └──── MCP ──────┘
                            (6 tools via stdio)
```

Every agent in the Paperclip company points to the same `STIGMEM_URL`. Federation keeps
the company node in sync with upstream peers. Agents never talk directly to an upstream node.

---

## Prerequisites

| Tool | Notes |
|------|-------|
| Docker ≥ 24 | Nodes run in containers |
| Docker Compose v2 ≥ 2.20 | For the local two-node quickstart |
| Node.js ≥ 18 | For the MCP server and `emit-fact.js` helper |
| Python ≥ 3.11 + `uv` | For the adapter CLI and key generation |
| `cryptography` Python package | `pip install cryptography` — for Ed25519 keypair generation |

---

## Step 1 — Deploy the company stigmem node {#deploy}

### Option A: Docker Compose (recommended for getting started)

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem

# Generate a federation keypair for this node
python infra/soak/keys.py | head -2 > .env.node
# .env.node now contains NODE_A_PUBKEY and NODE_A_PRIVKEY

# Rename keys to the expected variable names
sed -i '' 's/NODE_A_PUBKEY/STIGMEM_FEDERATION_PUBKEY/g; s/NODE_A_PRIVKEY/STIGMEM_FEDERATION_PRIVKEY/g' .env.node

# Start a single node
docker compose -f docker-compose.yml up --build -d node-a

# Confirm healthy
curl http://localhost:8765/healthz   # {"status":"ok"}
curl http://localhost:8765/.well-known/stigmem | jq '{node_id, version, federation}'
```

### Option B: Kubernetes (production)

See the [Helm install guide](../../get-started/quickstart-tutorial#kubernetes-install-helm) for
`federation-values.yaml` and the `stigmem-keys` Kubernetes Secret setup.

### Persistent node on macOS (dev/dogfood)

```bash
bash scripts/service-install.sh
# Installs a LaunchAgent that starts stigmem at login and restarts on crash
```

---

## Step 2 — Provision an API key for agents {#api-key}

By default, dev nodes run with `auth=none`. For production, enable API-key auth and mint
a company-wide key:

```bash
# Mint a key for the Paperclip company
curl -X POST http://localhost:8765/v1/auth/keys \
  -H 'Content-Type: application/json' \
  -d '{
    "label":      "paperclip-company",
    "scopes":     ["company", "public"],
    "expires_in": null
  }' | jq '{key_id, api_key}'
```

Store the returned `api_key` in your Paperclip adapter config (or the `.claude/settings.json`
environment block for Claude Code agents) as `STIGMEM_API_KEY`. All agents share this key.
Use a Memory Garden (Step 5) to partition access if you need per-team isolation.

---

## Step 3 — Build and configure the MCP server {#mcp-server}

```bash
cd stigmem/adapters/mcp
pnpm install && pnpm build
# produces: stigmem/adapters/mcp/dist/server.js
```

Add to `.mcp.json` at the root of your Paperclip workspace (picked up by Claude Code and the Paperclip harness):

```json
{
  "mcpServers": {
    "stigmem": {
      "command": "node",
      "args": ["/absolute/path/to/stigmem/adapters/mcp/dist/server.js"],
      "env": {
        "STIGMEM_URL":    "http://localhost:8765",
        "STIGMEM_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

Available tools after connection:

| Tool | Heartbeat use |
|------|--------------|
| `assert_fact` | Push lifecycle facts (checkout, decision, blocked, done) |
| `query_facts` | Pull constraints and preferences on startup |
| `subscribe_scope` | Cursor-poll for new facts in a scope |
| `resolve_contradiction` | Triage conflicts from federated peers |
| `lint_scope` | Health sweep — stale facts, contradictions, orphans |

---

## Step 4 — Install the Paperclip company skill {#skill}

Load `adapters/paperclip/skill.md` as a company skill in Paperclip. This injects
the stigmem usage instructions into every agent without per-agent configuration.

```bash
# Via the Paperclip company skills API (or UI)
# Upload adapters/paperclip/skill.md as a new company skill named "stigmem"
```

Once installed, agents will:
- Query `entity=company:<your-company>` at heartbeat start for active constraints
- Assert `paperclip:checkout` when claiming a task
- Assert `paperclip:issue_status` on block or completion
- Assert `intent:handoff_to` before delegating

Configure per-agent identity via environment variable in adapter config:

```bash
STIGMEM_SOURCE_ENTITY=agent:cto   # or agent:ceo, agent:senior-engineer, etc.
```

---

## Step 5 — Federate with a peer node {#federation}

To connect your company node to an upstream peer (Eidetic Labs reference node, a partner,
or a second instance):

### 5a. Get your node's keypair

```bash
curl http://localhost:8765/.well-known/stigmem | jq '{node_id, federation}'
# federation.pubkey is your node's public key
```

### 5b. Generate a declaration signature

Use the signing snippet from the [federation guide](../../concepts/federation/#peer-declaration) or the
automated `scripts/federation-init.py` helper. For a manual one-off:

```python
import json, base64, datetime
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

priv_b64 = "<your-STIGMEM_FEDERATION_PRIVKEY>"
priv = Ed25519PrivateKey.from_private_bytes(
    base64.urlsafe_b64decode(priv_b64 + "==")
)

declaration = {
    "node_id":           "stigmem:node:<your-node-id>",
    "node_url":          "https://<your-public-url>",
    "federation_pubkey": "<your-pub-b64>",
    "allowed_scopes":    ["company", "public"],
    "signed_at":         datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
}
canonical = json.dumps(declaration, sort_keys=True, separators=(",", ":")).encode()
sig = priv.sign(canonical)
print(base64.urlsafe_b64encode(sig).decode().rstrip("="))
```

### 5c. Register your node with the peer

```bash
curl -X POST https://peer.example.com/v1/federation/peers \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <peer-node-api-key>' \
  -d '{
    "node_id":         "stigmem:node:<your-node-id>",
    "node_url":        "https://<your-public-url>",
    "allowed_scopes":  ["company", "public"],
    "declaration_sig": "<sig-from-5b>"
  }'
```

Confirm `"status": "active"` in the response.

### 5d. Verify replication

```bash
# Assert a test fact on your node
curl -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "company:paperclip",
    "relation":   "meta:federation_test",
    "value":      {"type": "string", "v": "online"},
    "source":     "agent:operator",
    "confidence": 1.0,
    "scope":      "public"
  }'

# Wait for pull interval (default 30 s), then check the peer
sleep 35
curl "https://peer.example.com/v1/facts?entity=company:paperclip&scope=public" | jq '.facts[]'
```

---

## End-to-end validation checklist {#validation}

Use this checklist to confirm the integration is working before declaring the setup ready.

### Node health

- [ ] `GET /healthz` returns `{"status":"ok"}`
- [ ] `GET /.well-known/stigmem` returns `node_id`, `version`, and `federation.pubkey`

### Fact read/write (agent perspective)

- [ ] `assert_fact` via MCP tool writes a fact and returns a `fact_id`
- [ ] `query_facts` via MCP tool retrieves the asserted fact by entity + relation
- [ ] `subscribe_scope` returns `has_more: false` on an idle scope (no stuck cursors)

### Heartbeat lifecycle facts

- [ ] CTO agent asserts `paperclip:checkout` on task pickup and the fact appears in stigmem
- [ ] CEO agent can query `entity=issue:<task-id>` and see the `paperclip:checkout` fact
- [ ] `paperclip:issue_status=done` appears after task completion

### Federation replication

- [ ] Peer registration returns `"status": "active"` (not 403 or 409)
- [ ] A `public`-scope fact asserted on the company node appears on the peer within 60 s
- [ ] A `company`-scope fact does **not** appear on a peer registered for `public` only (scope isolation)
- [ ] Audit log at `GET /v1/federation/audit` shows successful pull events

### Conflict handling (optional but recommended)

- [ ] Assert two conflicting facts (same entity/relation/scope, different values) on two nodes
- [ ] `GET /v1/conflicts` on the ingest node returns a `ConflictRecord`
- [ ] `POST /v1/conflicts/<id>/resolve` with a `winning_fact_id` closes the conflict

### Smoke test (automated)

```bash
bash adapters/mcp/tests/smoke.sh   # requires STIGMEM_URL set
make verify                        # end-to-end two-node Docker Compose smoke test
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `403 Forbidden` on peer register | Signature verification failed | Re-generate the declaration_sig; check that `node_url` matches your node's actual URL |
| `409 Conflict` on peer register | Already registered | Safe to ignore; replication is still active |
| Peer `status=inactive` | Node was unreachable during health check | Confirm your node's public URL is reachable from the peer; re-register if needed |
| Facts not appearing on peer after 60 s | Pull interval or network issue | Check `GET /v1/federation/audit` on the peer for pull errors; verify `allowed_scopes` match |
| `STIGMEM_URL is required` | MCP server env not set | Add `STIGMEM_URL` to `.mcp.json` env block |
| Tools timeout | Node not running | `curl http://localhost:8765/healthz`; restart with `bash scripts/service-install.sh` |
| Duplicate facts after restart | Cursor loss and full re-pull | Expected behavior; ingest layer deduplicates by fact ID automatically |

---

## Memory Gardens for multi-tenant isolation {#gardens}

If multiple teams share a single node and need ACL-isolated fact partitions:

```bash
# Create a garden for the engineering team
curl -X POST http://localhost:8765/v1/gardens \
  -H 'Content-Type: application/json' \
  -d '{
    "name":          "engineering",
    "admin_sources": ["agent:cto"],
    "writer_sources": ["agent:senior-engineer", "agent:qa"],
    "reader_sources": ["agent:ceo"]
  }' | jq '{garden_id, name}'
```

Assert facts into the garden by including `garden_id` in the fact payload. Facts in a garden
are only readable by sources with the appropriate role — scoped federation does not override
garden ACLs.

---

## See also

- [Paperclip connector](./paperclip) — MCP config, tool reference, heartbeat pattern
- [Federation guide](../../concepts/federation/) — key generation, peer tokens, scope enforcement
- [Asserting facts](../../concepts/facts/asserting-facts) — FactValue schema, relation naming, TTLs
- [Querying facts](../../concepts/facts/querying-facts) — filtering, pagination, cursor polling
- [Quickstart](../../get-started/quickstart-tutorial) — local two-node federation in under 5 minutes
