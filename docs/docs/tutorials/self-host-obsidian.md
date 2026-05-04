---
id: self-host-obsidian
title: "Tutorial: Self-host a stigmem node and sync your Obsidian vault"
sidebar_label: Self-host + Obsidian Sync
description: End-to-end walkthrough — deploy a stigmem node on Fly.io or Docker Compose, connect an Obsidian vault, write your first cross-vault fact, and recall it from a second vault.
---

# Tutorial: Self-host a stigmem node and sync your Obsidian vault

**Audience:** operators running a personal or team stigmem node; Obsidian users who want persistent, recallable memory across vaults.  
**Time:** ~25 min for Fly.io (cloud) or ~10 min for Docker Compose (laptop).

---

By the end you will have:

- A running stigmem node with TLS (Fly.io) or on localhost (Compose).
- An Obsidian vault syncing bidirectionally with that node.
- A fact written in Vault A that is recalled by Vault B with a single `curl`.
- Measured numbers for your own environment: deploy time, first-fact round-trip, and initial sync throughput on a 1k-note vault.

---

## Prerequisites

- Python 3.11+ with `pip` or `uv`
- `curl` and `jq`
- Obsidian 1.4.0+ (two vaults, or two directories of `.md` files on disk)
- **For Fly.io:** [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed and authenticated (`fly auth login`)
- **For Compose:** Docker 24+ with Compose v2 (`docker compose version`)

---

## Step 1 — Choose a backend

This tutorial uses **SQLite with a persistent volume** — zero external dependencies, works identically on Fly.io and Compose. It is the right choice when:

- You are running on a single host.
- You can tolerate the data living on that host's disk.
- You do not need multi-region reads.

If you already run Postgres or want multi-region replication, work through the [Choose Your Backend](/docs/operating/choose-backend) decision tree before continuing. The connection steps in Steps 4–6 below are identical regardless of backend.

---

## Step 2 — Deploy the node

### Option A — Fly.io (cloud, ~3 min)

Clone the repo and run the first-time setup from the repo root:

```bash
# 1. Pick a globally unique app name
export APP=my-stigmem-node

# 2. Create the Fly app (no deploy yet)
fly apps create "$APP"

# 3. Persistent 1 GiB volume in iad (adjust region to suit)
fly volumes create stigmem_data --size 1 --region iad --app "$APP"

# 4. Set the node URL secret
fly secrets set --app "$APP" \
  STIGMEM_NODE_URL="https://$APP.fly.dev"

# 5. Deploy (~3 min; Fly's remote builder handles the image)
fly deploy --config deploy/fly/fly.toml --app "$APP"
```

The deploy compiles the Docker image on Fly's remote builder, pushes it, and starts the Machine. Typical wall-clock time:

| Phase | Typical duration |
|---|---|
| Remote image build (first deploy) | ~2 min |
| Volume attach + machine start | ~30 s |
| Health check passes | ~10 s |
| **Total** | **~3 min** |

Subsequent deploys hit the layer cache and finish in ~60 s.

After deploy, export the node URL for the rest of this tutorial:

```bash
export STIGMEM_URL="https://$APP.fly.dev"
```

### Option B — Docker Compose (laptop, ~1 min)

```bash
cd deploy/compose
cp .env.example .env          # review defaults; no changes needed for SQLite
docker compose up -d
```

Export the local URL:

```bash
export STIGMEM_URL="http://localhost:8765"
```

---

## Step 3 — Verify the node

```bash
curl -s "$STIGMEM_URL/v1/health" | jq .
```

Expected response:

```json
{
  "status": "ok",
  "version": "...",
  "backend": "sqlite"
}
```

Time your first fact round-trip:

```bash
time curl -s -X POST "$STIGMEM_URL/v1/facts" \
  -H 'Content-Type: application/json' \
  -d '{
    "entity": "test://ping",
    "relation": "note:title",
    "value": {"type": "string", "value": "ping"},
    "scope": "local",
    "confidence": 1.0
  }' | jq .id
```

On a Fly.io node in `iad` you should see `< 50 ms` end-to-end. On localhost the same call typically takes `< 5 ms`.

---

## Step 4 — Connect Obsidian Vault A

You have two options. Use the **community plugin** if you want in-process sync inside Obsidian. Use the **CLI adapter** if you prefer a daemon that runs outside Obsidian, or if you are syncing Logseq, Dendron, or a plain folder of Markdown files.

### Option A — Community plugin

> The plugin is pending registry submission. Install manually until it appears in the Community plugin browser.

```bash
cd /path/to/vault-a/.obsidian/plugins/
mkdir stigmem && cd stigmem
curl -LO https://github.com/Eidetic-Labs/stigmem/releases/latest/download/main.js
curl -LO https://github.com/Eidetic-Labs/stigmem/releases/latest/download/manifest.json
```

Reload Obsidian (**Cmd/Ctrl+R**), enable the plugin under **Settings → Community plugins**, then configure it:

1. **Settings → Stigmem → Node URL** — paste your `$STIGMEM_URL`.
2. Leave **API key** empty for now (auth is not required in this tutorial).
3. Click **Test connection** — you should see *"Connected to stigmem node."*
4. Run **Sync vault now** from the command palette (**Cmd+P**).

### Option B — CLI/daemon adapter

```bash
pip install stigmem-obsidian
# or: uv add stigmem-obsidian
```

Add `.stigmem-sync.toml` to your vault root:

```toml
node_url   = "https://my-stigmem-node.fly.dev"   # or http://localhost:8765
vault_name = "vault-a"
scope      = "local"
```

Run a one-shot sync to verify connectivity:

```bash
stigmem-obsidian sync /path/to/vault-a
```

Expected output:

```
vault→stigmem: 42 facts pushed
stigmem→vault: 0 facts pulled (nothing external yet)
conflicts:     0
```

To keep the vault live, start the watch daemon:

```bash
stigmem-obsidian watch /path/to/vault-a
```

The daemon runs an initial full sync, then re-syncs any file within ~2 s of a save event.

---

## Step 5 — Write your first cross-vault fact

Create a note in Vault A called `Alice.md`:

```markdown
---
title: Alice
status: active
---

Alice leads the Loom project.

[[projects/Loom]]
```

Save the file. If you are using the plugin, it syncs automatically on save (within the 1500 ms debounce). If you are using the CLI daemon, it picks up the change within `watch_interval` (default 2 s).

Verify the fact landed in the node:

```bash
curl -s "$STIGMEM_URL/v1/facts?entity=obsidian://vault/Alice" | jq '.facts[] | {relation, value}'
```

You should see:

```json
{ "relation": "note:title",  "value": { "type": "string", "value": "Alice" } }
{ "relation": "note:status", "value": { "type": "string", "value": "active" } }
{ "relation": "references",  "value": { "type": "ref",    "value": "obsidian://vault/projects/Loom" } }
```

---

## Step 6 — Recall it from a second vault

Connect Vault B to the same node (repeat Step 4 with `/path/to/vault-b`). Then run a recall query from Vault B:

```bash
curl -s -X POST "$STIGMEM_URL/v1/recall" \
  -H 'Content-Type: application/json' \
  -d '{"query": "Alice Loom project", "token_budget": 512}' \
  | jq '.facts[] | {entity, relation, value, score}'
```

The fact you wrote from Vault A appears in the recall results — scored by the hybrid pipeline (lexical + semantic + graph). This is the cross-vault recall loop: write anywhere, recall anywhere the same node can reach.

If you have the plugin installed in Vault B, open any note mentioning Alice or Loom and click the 🧠 brain icon in the ribbon. The **Recall sidebar** shows graph neighbors from Stigmem, including `Alice` with her `note:status` and `references` facts.

---

## Step 7 — (Optional) Dry-run a larger vault

To get a realistic throughput number for your own vault before committing to a full sync:

```bash
stigmem-obsidian dry-run /path/to/my-real-vault --verbose
```

The dry run scans every note and prints how many facts would be pushed, without writing anything. A 1,000-note vault produces roughly 3,000–8,000 facts depending on frontmatter density. The real sync runs the same loop sequentially:

| Vault size | Estimated initial sync | Notes |
|---|---|---|
| 100 notes | ~10 s | Localhost |
| 100 notes | ~25 s | Fly.io iad |
| 1,000 notes | ~90 s | Localhost |
| 1,000 notes | ~2 min | Fly.io iad |
| 5,000 notes | ~8 min | Fly.io iad |

These are estimates based on ~50 ms per HTTPS round-trip to a Fly `iad` Machine with SQLite WAL. After the initial sync, the watch daemon only processes changed files — per-save latency stays under 100 ms for a single note with a handful of facts.

---

## What's next

- **Add authentication** — set `STIGMEM_AUTH_REQUIRED=true` and `STIGMEM_API_KEY_HASH` on the node; add `api_key = "sk-..."` to `.stigmem-sync.toml`. See the [Operator's Handbook](/docs/operating).
- **Back up your facts** — the [Backup & Restore runbook](/docs/operating/backup-restore) covers signed snapshots and point-in-time recovery.
- **Add a second node (federation)** — follow the [Two-Org Federated Network tutorial](/docs/tutorials/two-org-federation) to peer two nodes and replicate facts across org boundaries.
- **Switch to libSQL / Turso** — if you need multi-region reads or want off-node durability, see the [Fly.io deploy runbook](/docs/operating/deploy-runbooks) Turso section.
- **Monitor** — `GET /metrics` (Prometheus) is exposed at `:9091`. See the [Monitoring guide](/docs/operating/monitoring).
