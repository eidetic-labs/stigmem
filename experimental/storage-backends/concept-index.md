---
title: Storage Backends
sidebar_label: Storage Backends
description: Storage backend options for the Stigmem reference node — SQLite, libSQL/Turso, Postgres, and the Obsidian vault adapter explained.
audience: Operator
---

# Storage Backends

*Audience: node operators, deployment engineers.*

:::tip Operator handbook
Looking for a guided decision tree and step-by-step runbooks? See **[Operating Stigmem → Choose your backend](./choose-backend)**.
:::

---

The Stigmem reference node is storage-backend agnostic from the pre-reset attestation-chain work onward. A `StorageBackend` adapter trait separates the protocol logic from the persistence layer. The backend you choose depends on your durability, multi-region, and operational requirements.

---

## Backend matrix

| Backend | Survives reboot | Survives device loss | Multi-region read | Encryption at rest | When to use |
|---|---|---|---|---|---|
| **SQLite (file, WAL)** | Yes — with persistent volume | No | No | SQLCipher opt-in | Default; local dev; single-host deployments |
| **libSQL / Turso embedded replica** | Yes | Yes (cloud primary) | Yes (embedded replicas) | Yes | **Recommended for hosted operators** |
| **Postgres + pgvector** | Yes | Yes (managed) | Yes (read replicas) | TLS + at-rest | Enterprise; existing Postgres shops |
| **In-memory** | No | N/A | N/A | N/A | Tests only — never use in production |

---

## Configuring the backend

Set `STIGMEM_STORAGE_BACKEND` to select the active backend. The default is `sqlite`; no extra packages are required.

```bash
# SQLite (default) — no additional setup needed
STIGMEM_STORAGE_BACKEND=sqlite
STIGMEM_DB_PATH=/app/data/stigmem.db   # defaults to stigmem.db in the working directory

# libSQL / Turso embedded-replica — install the extra first
pip install 'stigmem-node[libsql]'

STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_DB_PATH=/app/data/stigmem.db          # local replica file path
STIGMEM_LIBSQL_URL=libsql://your-db.turso.io  # Turso endpoint
STIGMEM_LIBSQL_AUTH_TOKEN=<from-secrets-manager>
```

Run migrations after switching backends:

```bash
stigmem migrate
```

Migrations are idempotent — they skip already-applied versions.

### Running the conformance suite against libSQL

```bash
pip install 'stigmem-node[libsql]'
cd node
pytest --backend=libsql
```

The `--backend` flag redirects every test fixture to use `LibSQLBackend` in local mode (no sync). Tests skip automatically when `libsql-experimental` is not installed.

---

## SQLite (default)

SQLite in WAL mode is the default backend. It is persistent across reboots as long as the database file lives on a real disk or persistent volume — not an ephemeral container filesystem.

For single-host deployments on a VPS, bare metal, or a Fly.io persistent volume, SQLite is sufficient. The main failure mode is device loss (disk failure, volume deletion); if that matters, use libSQL.

```bash
# Docker / Compose: mount a named volume so the DB survives container restarts
volumes:
  - stigmem-data:/app/data

# Fly.io: attach a persistent volume
# fly volumes create stigmem_data --region iad --size 10
# Then mount under [mounts] in fly.toml:
# [mounts]
#   source = "stigmem_data"
#   destination = "/app/data"
```

**SQLCipher (at-rest encryption):** available as a one-flag opt-in. Install the
`encryption` and `sqlcipher` extras, set `STIGMEM_AT_REST_ENCRYPTION=on`, and
point to your passphrase or raw key via env var. See the
[Encryption at Rest guide](../../security/encryption-at-rest.md) for the full setup,
existing-database migration, and key-rotation runbook.

```bash
pip install 'stigmem-node[encryption,sqlcipher]'

STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_PASSPHRASE_VAR   # name of the env var holding the passphrase
```

---

## libSQL / Turso (recommended for hosted)

libSQL is a SQLite fork with an embedded-replica model: a Turso-hosted cloud primary holds the authoritative copy; each node runs an embedded replica that syncs from the primary and serves reads locally. Writes go to the primary; reads are local.

This gives you SQLite's operational simplicity with:
- Durability against device loss (primary is cloud-backed)
- Multi-region read scaling via regional embedded replicas
- Native at-rest encryption
- Point-in-time recovery via Turso's cloud service

### Step-by-step: Fly.io + Turso setup

**Prerequisites:** `flyctl` installed; Turso CLI installed (`curl -sSfL https://get.tur.so/install.sh | bash`).

```bash
# 1. Create a Turso database
turso db create stigmem-prod

# 2. Retrieve the database URL and auth token
TURSO_URL=$(turso db show stigmem-prod --url)
TURSO_TOKEN=$(turso db tokens create stigmem-prod)

# 3. Install the libsql extra
pip install 'stigmem-node[libsql]'

# 4. Set environment variables (Fly.io secrets or local .env)
fly secrets set \
  STIGMEM_STORAGE_BACKEND=libsql \
  STIGMEM_LIBSQL_URL="$TURSO_URL" \
  STIGMEM_LIBSQL_AUTH_TOKEN="$TURSO_TOKEN" \
  STIGMEM_DB_PATH=/app/data/stigmem.db

# 5. Run migrations (idempotent — safe to run on every deploy)
stigmem migrate
```

**Verifying the connection:**

```bash
# From inside the running container or locally with env vars set:
stigmem healthcheck
# → { "status": "ok", "backend": "libsql", "sync_lag_ms": 0 }
```

**Multi-region read replicas (optional):**

To serve reads from a second region, create a Turso replica and point it at the same group:

```bash
turso db replicate stigmem-prod --location fra
# Then add STIGMEM_LIBSQL_REPLICA_URL=<fra-replica-url> for that region's node.
```

Writes always route to the primary regardless of which replica is configured. The node automatically falls back to the primary if the replica is unavailable.

For air-gapped or sovereign deployments where a cloud primary is not acceptable, self-hosted `libsql sqld` is an option — see the Operator's Handbook (the pre-reset multi-backend work).

### Encrypt the local replica (optional)

The Turso cloud primary uses server-side encryption. To also encrypt the local replica file:

```bash
STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_PASSPHRASE_VAR   # name of the env var holding your passphrase
```

See [Encrypted at Rest](#encrypted-at-rest) below for the full setup and key-rotation runbook.

---

## Postgres + pgvector (enterprise)

The Postgres backend is recommended for operators who already run managed Postgres (RDS, Cloud SQL, Neon, Supabase, etc.) and want to avoid a second persistence tier. It also enables the pre-reset graph & recall design vector-embedding recall features without a separate vector store.

```bash
STIGMEM_STORAGE_BACKEND=postgres
STIGMEM_POSTGRES_DSN=postgresql://user:pass@host:5432/stigmem
```

The `pgvector` extension is required for vector-embedding features:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Point-in-time recovery and read-replica failover use native Postgres features — no Stigmem-specific configuration beyond the DSN.

:::note the pre-reset multi-backend work availability
The Postgres backend ships in the pre-reset multi-backend work. The conformance test suite (the pre-reset multi-backend work) verifies Postgres parity with SQLite and libSQL.
:::

---

## In-memory (tests only)

The in-memory backend provides clean-slate state per test run without touching disk. It is explicitly excluded from the conformance test suite and should never be used in production.

```python
# pytest fixture example
@pytest.fixture
def node():
    return StigmemNode(backend="memory")
```

---

## Choosing a backend

```
Local dev or CI?
  → in-memory (tests) or SQLite on a local path (persistent dev)

Single-host hosted deployment (Fly.io, VPS, bare metal)?
  → libSQL/Turso embedded replica  [recommended]
  → SQLite + persistent volume  [acceptable if you can tolerate device-loss risk]

Multi-region or existing Postgres infrastructure?
  → Postgres + pgvector

Air-gapped or sovereign deployment?
  → SQLite (file)  or  self-hosted libSQL sqld
  → Avoid Turso cloud — it's a network-dependent service
```

Once you have chosen a backend, pick a **[deploy recipe](https://github.com/Eidetic-Labs/stigmem/blob/main/deploy/README.md)**
that matches your environment (Fly.io, Compose, Helm, systemd, or PaaS), or follow the
step-by-step **[deploy runbooks](../runbooks/deploy-runbooks)** in the Operator Handbook.
Each recipe ships a ready-to-use `STIGMEM_STORAGE_BACKEND` env-var template.

---

## Encrypted at Rest

At-rest encryption is an opt-in layer on top of any file-based backend (SQLite or libSQL local replica). The encryption key never touches the database file — it is derived from an environment-injected passphrase at runtime.

### Initial setup

```bash
# Install the extras
pip install 'stigmem-node[encryption,sqlcipher]'

# Point to the env var that holds your passphrase (don't put the passphrase inline)
export MY_DB_PASSPHRASE="my-strong-passphrase"

STIGMEM_AT_REST_ENCRYPTION=on
STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_DB_PASSPHRASE
```

On first start with encryption enabled, Stigmem converts an existing plain-text database to encrypted format in place. A backup is written to `<db_path>.pre-encryption-backup` before the conversion.

### Migrating an existing database to encryption

If you are enabling encryption on a node that already has data:

```bash
# Stop the node, then run the migration helper
stigmem db encrypt --passphrase-env MY_DB_PASSPHRASE

# Start the node — it will open the now-encrypted file transparently
```

The helper re-encrypts the WAL and then issues a `VACUUM` to reclaim freed pages in the plaintext WAL file.

### Key rotation

To rotate the encryption passphrase without downtime:

```bash
stigmem db rekey \
  --old-passphrase-env OLD_PASSPHRASE_VAR \
  --new-passphrase-env NEW_PASSPHRASE_VAR
```

The node must be stopped before rekeying. After rekeying, update your secrets manager and restart with the new env var name in `STIGMEM_AT_REST_KEY_PASSPHRASE_ENV`.

:::caution
If you lose the passphrase, the database file is irrecoverable. Store the passphrase in a secrets manager (Fly.io secrets, AWS Secrets Manager, Vault, etc.) — not in the `fly.toml` or Dockerfile.
:::

---

## Backup and Restore

All production backends support signed snapshot backup and restore via the `stigmem snapshot` CLI tool. Snapshots are content-addressed and signed with the node's Ed25519 federation keypair.

### Create a snapshot

```bash
# Create a signed snapshot (writes to the specified path)
stigmem snapshot create --output /backups/stigmem-$(date +%Y%m%d-%H%M%S).snap

# Snapshot includes:
#   artifacts/stigmem.db                   — copy of the database file
#   artifacts/schema_migration_cursor.json — applied migration versions
#   manifest.json                          — SHA-256 hashes + Ed25519 signature
```

Automate daily snapshots with cron or a Fly.io machine cron target:

```bash
# Example: daily backup via cron (add to crontab or a scheduled Fly Machine)
0 3 * * * stigmem snapshot create --output /backups/stigmem-$(date +%Y%m%d).snap
```

### Verify a snapshot before restoring

Always verify before applying a snapshot to a live node:

```bash
stigmem snapshot verify /backups/stigmem-20260601.snap
# → OK: sha256 checksums valid, signature verified (key: stigmem:node:<uuid>)
# → ERROR: signature mismatch — possible tampering; abort restore

# Verify against a specific trusted public key (e.g. when restoring to a different node)
stigmem snapshot verify /backups/stigmem-20260601.snap \
  --trusted-key <base64url-ed25519-pubkey>
```

### Restore

```bash
# Stop the node first
stigmem snapshot restore /backups/stigmem-20260601.snap

# The restore step:
#   1. Verifies SHA-256 checksums for all artifacts
#   2. Verifies the Ed25519 manifest signature
#   3. Writes the database file to STIGMEM_DB_PATH
#   4. Replays any migrations newer than the snapshot cursor

# Restart the node
stigmem serve
```

:::caution
Restore overwrites `STIGMEM_DB_PATH`. Ensure you have a pre-restore backup of the current database before running this command.
:::

### libSQL / Postgres: cloud-native point-in-time recovery

For libSQL (Turso), use `turso db snapshot` for point-in-time recovery — it operates on the cloud primary without requiring node downtime. For Postgres, use your managed provider's PITR feature. Both are documented in the Operator's Handbook (the pre-reset multi-backend work).

---

## Recall and embedding configuration (pre-reset graph & recall design — §20)

:::note pre-reset graph & recall design — draft
The following environment variables are part of spec §20, currently a draft. Variable names and defaults are stable in the draft spec; they may change before §20 is promoted to normative.
:::

pre-reset graph & recall design adds vector embedding and recall capabilities. Configure these variables alongside your storage backend settings.

### Embedding provider

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_EMBED_PROVIDER` | `ollama` | Embedding backend. Options: `ollama` (offline, default), `openai` (requires `OPENAI_API_KEY`), `voyage` (requires `VOYAGE_API_KEY`). |
| `STIGMEM_EMBED_MODEL` | `nomic-embed-text` | Model name for the selected provider. See the table below for supported combinations. |
| `STIGMEM_EMBED_DIMENSIONS` | `768` | Embedding vector dimensions. **Changing this after facts have been indexed is a fatal error** — re-index by draining and re-inserting all `vec_facts` rows. |

Supported model combinations:

| `STIGMEM_EMBED_PROVIDER` | `STIGMEM_EMBED_MODEL` | Dimensions | Notes |
|---|---|---|---|
| `ollama` (default) | `nomic-embed-text` (default) | 768 | Offline; Matryoshka — truncate to 256 with `STIGMEM_EMBED_DIMENSIONS=256` |
| `ollama` | `mxbai-embed-large` | 1024 | Higher recall; larger memory footprint |
| `openai` | `text-embedding-3-small` | 1536 | Cloud; requires `OPENAI_API_KEY` |
| `voyage` | `voyage-3-lite` | 512 | Cloud; requires `VOYAGE_API_KEY` |

**Local setup (default, no API key required):**

```bash
# Install Ollama and pull the default model
ollama pull nomic-embed-text

# No additional env vars needed — the node uses ollama at localhost:11434 by default
STIGMEM_EMBED_PROVIDER=ollama
STIGMEM_EMBED_MODEL=nomic-embed-text
```

**OpenAI cloud opt-in:**

```bash
STIGMEM_EMBED_PROVIDER=openai
STIGMEM_EMBED_MODEL=text-embedding-3-small
STIGMEM_EMBED_DIMENSIONS=1536
OPENAI_API_KEY=<from-secrets-manager>
```

:::caution
Changing `STIGMEM_EMBED_PROVIDER` or `STIGMEM_EMBED_DIMENSIONS` after the node has indexed facts will cause a startup error:

```
FATAL: vec_facts dimensionality mismatch: stored=768 configured=1536. Re-index required.
```

To re-index, drain and re-insert all `vec_facts` rows with the new model. The node will not silently truncate existing embeddings.
:::

### Memory card and subscription tuning

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_CARD_MAX_AGE_S` | `86400` | Seconds before a memory card is considered stale and queued for background refresh. Stale cards are served with `card_stale: true` until refresh completes. |
| `STIGMEM_SUBSCRIPTION_REPLAY_S` | `3600` | Event replay window for subscriptions. Subscribers may request missed events within this window via `GET /v1/subscriptions/:id/events?after={event_id}`. Events older than this window are not recoverable. |
| `STIGMEM_CURSOR_TTL_S` | `300` | Lifetime of pagination cursors issued by `GET /v1/graph/neighbors`. A request with an expired cursor returns HTTP 400 `cursor_expired`; re-issue the query to get a fresh cursor. |

---

## Obsidian — adapter, not a backend

**Obsidian is not a storage backend for Stigmem.** Obsidian stores knowledge as plain markdown files with YAML frontmatter and `[[wikilinks]]` in a user-owned vault. It is not a transactional database and cannot host federation HLC ordering, indices, or attestation tables.

Stigmem treats Obsidian as a **bidirectional sync adapter**: the underlying storage backend remains SQLite, libSQL, or Postgres. The Obsidian adapter reflects facts into the vault as markdown notes and reads vault content back as facts.

This distinction matters because:

| Requirement | Storage backend | Obsidian vault |
|---|---|---|
| Write ordering (HLC timestamps, WAL) | ✓ Guaranteed | ✗ Not supported |
| Federation (HLC cursors, signed PeerDeclarations) | ✓ Native | ✗ Not expressible in vault files |
| Source attestation (§18 entity-URI binding) | ✓ Enforced | ✗ Requires adapter layer |
| Conflict retention (§6.3 first-class records) | ✓ Retained | ✗ Overwritten by vault edits |

The vault is a *projection and write surface* — a great UX for vibe-coders and memory-first workflows — not the source of truth.

### Obsidian adapter (the pre-reset multi-backend work)

Two distribution forms ship in the pre-reset multi-backend work:

**CLI/daemon** (`adapters/obsidian/`) — a sync process that watches a vault path and reflects changes both ways:
- **Vault → Stigmem:** each note becomes an entity. Frontmatter fields → typed facts. `[[wikilinks]]` → relations (default: `references`). Inline `key:: value` (Dataview syntax) → typed facts.
- **Stigmem → vault:** new facts about a known entity are appended to the entity's note (frontmatter or a managed `## Stigmem` section). New entities get auto-created notes in a configurable folder.

**Obsidian community plugin** (`adapters/obsidian-plugin/`) — same sync engine inside Obsidian's process, plus:
- Command-palette `Recall related memories`
- Sidebar showing graph neighbors from Stigmem
- Inline rendering of synced facts

### Logseq / Dendron generalization

The Obsidian adapter is generic enough to handle other markdown-based knowledge tools with a single config flag:

| Vault format | `adapter.vault_format` value |
|---|---|
| Obsidian | `obsidian` (default) |
| Logseq | `logseq` |
| Dendron | `dendron` |
| Plain markdown folder | `plain` |

All four modes use the same bidirectional sync engine. No separate codebase is needed per tool.

See the [Features](../../concepts/features) page for the current status of all Stigmem capabilities including the Obsidian adapter.
