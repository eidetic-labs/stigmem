---
id: backends
title: Storage Backends
sidebar_label: Storage Backends
description: Storage backend options for the Stigmem reference node — SQLite, libSQL/Turso, Postgres, and the Obsidian vault adapter explained.
---

# Storage Backends

*Audience: node operators, deployment engineers.*

---

The Stigmem reference node is storage-backend agnostic from Phase 8 onward. A `StorageBackend` adapter trait separates the protocol logic from the persistence layer. The backend you choose depends on your durability, multi-region, and operational requirements.

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

**SQLCipher (at-rest encryption):** available as a build flag. Enable with `STIGMEM_SQLITE_ENCRYPT=true` and provide the key via `STIGMEM_SQLITE_KEY`. Inject the key through your secrets manager — do not commit it.

```bash
STIGMEM_SQLITE_ENCRYPT=true
STIGMEM_SQLITE_KEY=<inject-from-secrets-manager>
```

---

## libSQL / Turso (recommended for hosted)

libSQL is a SQLite fork with an embedded-replica model: a Turso-hosted cloud primary holds the authoritative copy; each node runs an embedded replica that syncs from the primary and serves reads locally. Writes go to the primary; reads are local.

This gives you SQLite's operational simplicity with:
- Durability against device loss (primary is cloud-backed)
- Multi-region read scaling via regional embedded replicas
- Native at-rest encryption
- Point-in-time recovery via Turso's cloud service

```bash
# Install the libsql extra, then configure:
pip install 'stigmem-node[libsql]'

STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_DB_PATH=/app/data/stigmem.db          # local replica file
STIGMEM_LIBSQL_URL=libsql://your-db.turso.io  # Turso endpoint
STIGMEM_LIBSQL_AUTH_TOKEN=<inject-from-secrets-manager>
```

Turso has a free tier suitable for single-operator nodes. For multi-region read replicas, configure per-region embedded replica URLs in `fly.toml` or your PaaS config.

For air-gapped or sovereign deployments where a cloud primary is not acceptable, self-hosted libSQL sqld is an option — see the Operator's Handbook (Phase 11).

---

## Postgres + pgvector (enterprise)

The Postgres backend is recommended for operators who already run managed Postgres (RDS, Cloud SQL, Neon, Supabase, etc.) and want to avoid a second persistence tier. It also enables the Phase 9 vector-embedding recall features without a separate vector store.

```bash
STIGMEM_STORAGE_BACKEND=postgres
STIGMEM_POSTGRES_DSN=postgresql://user:pass@host:5432/stigmem
```

The `pgvector` extension is required for vector-embedding features:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Point-in-time recovery and read-replica failover use native Postgres features — no Stigmem-specific configuration beyond the DSN.

:::note Phase 11 availability
The Postgres backend ships in Phase 11. The conformance test suite (Phase 11) verifies Postgres parity with SQLite and libSQL.
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

---

## Backup and restore

All production backends support signed snapshot backup and restore via the `stigmem snapshot` CLI tool (ships in Phase 8):

```bash
# Create a signed snapshot
stigmem snapshot create --output /backups/stigmem-$(date +%Y%m%d).snap

# Verify snapshot integrity before restoring
stigmem snapshot verify /backups/stigmem-20260601.snap

# Restore
stigmem snapshot restore /backups/stigmem-20260601.snap
```

Snapshots are signed with the node's Ed25519 keypair. The restore step validates the signature before applying. For libSQL and Postgres, cloud-native point-in-time recovery is also available and documented in the Operator's Handbook (Phase 11).

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

### Obsidian adapter (Phase 11)

Two distribution forms ship in Phase 11:

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

See the [Roadmap](./roadmap.md) page — Phase 11 — for the full Obsidian adapter delivery plan.
