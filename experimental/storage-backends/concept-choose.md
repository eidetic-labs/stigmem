---
title: Choose Your Backend
sidebar_label: Choose Your Backend
description: Decision tree for selecting the right Stigmem storage backend — SQLite, libSQL/Turso, Postgres, or air-gapped options.
audience: Operator
---

# Choose Your Backend

**Audience:** operators making their first backend decision; operators migrating between backends.  
**See also:** [Storage Backends](../backends) for full environment-variable reference.

---

## Decision tree

Work through this tree top-to-bottom to reach a backend recommendation:

```
Are you running local dev or CI?
  ├─ YES → in-memory (tests) or SQLite on a local path (persistent dev)
  └─ NO ↓

Is device-loss tolerable? (Acceptable: test or staging; not acceptable: production)
  ├─ YES (staging/test) → SQLite + persistent volume
  └─ NO (production) ↓

Do you already operate Postgres (RDS, Cloud SQL, Neon, Supabase, etc.)?
  ├─ YES → Postgres + pgvector
  └─ NO ↓

Do you need air-gapped or sovereign deployment (no cloud primary)?
  ├─ YES → SQLite (file) or self-hosted libSQL sqld
  └─ NO → libSQL / Turso embedded replica  ← recommended default
```

---

## Backend comparison

| Backend | Survives reboot | Survives device loss | Multi-region reads | Encryption at rest | When to use |
|---|---|---|---|---|---|
| **SQLite (file, WAL)** | Yes — persistent volume required | No | No | SQLCipher opt-in | Single-host; air-gapped; sovereign |
| **libSQL / Turso** | Yes | Yes (cloud primary) | Yes (embedded replicas) | Yes | **Recommended for hosted operators** |
| **Postgres + pgvector** | Yes | Yes (managed) | Yes (read replicas) | TLS + at-rest | Existing Postgres shops; enterprise |
| **In-memory** | No | N/A | N/A | N/A | Tests only — **never production** |

---

## SQLite

**Best for:** single-host VPS, bare metal, Fly.io with a persistent volume, air-gapped deployments, or any case where you want zero external dependencies.

**Key constraint:** data lives entirely on the node's disk. Disk failure = data loss. If you can't tolerate that, use libSQL.

```bash
STIGMEM_STORAGE_BACKEND=sqlite
STIGMEM_DB_PATH=/app/data/stigmem.db
```

Make sure `STIGMEM_DB_PATH` points to a **persistent volume**, not an ephemeral container filesystem:

```yaml
# docker-compose.yml
volumes:
  stigmem-data:
services:
  node:
    volumes:
      - stigmem-data:/app/data
```

**Add encryption at rest:** install the `encryption,sqlcipher` extras and set `STIGMEM_AT_REST_ENCRYPTION=on`. See the [Key rotation](../../security/key-rotation) runbook for the full setup and rotation procedure.

**Recovery:** use `stigmem snapshot create` to take signed snapshots to durable off-node storage (S3, GCS, SFTP). See [Backup & restore](../runbooks/backup-restore).

---

## libSQL / Turso (recommended)

**Best for:** hosted operators who want SQLite simplicity with cloud-backed durability and optional multi-region reads.

The embedded-replica model means reads are always local (fast), writes go to a Turso cloud primary (durable), and the replica syncs automatically.

```bash
pip install 'stigmem-node[libsql]'

STIGMEM_STORAGE_BACKEND=libsql
STIGMEM_DB_PATH=/app/data/stigmem.db       # local replica file
STIGMEM_LIBSQL_URL=libsql://your-db.turso.io
STIGMEM_LIBSQL_AUTH_TOKEN=<from-secrets-manager>
```

Run migrations after configuring:

```bash
stigmem migrate
```

**Multi-region:** add a Turso replica per region and set `STIGMEM_LIBSQL_REPLICA_URL` on each regional node. Writes always route to the primary.

**Air-gapped or no cloud primary:** use `libsql sqld` self-hosted instead of Turso. Point `STIGMEM_LIBSQL_URL` at your own `sqld` instance.

**Recovery:** Turso provides point-in-time recovery (`turso db snapshot`) for the cloud primary. For the local replica, use `stigmem snapshot create`. See [Backup & restore](../runbooks/backup-restore).

---

## Postgres + pgvector

**Best for:** operators who already run managed Postgres and want a single persistence tier; operations requiring native PITR, read replicas, or enterprise compliance.

```bash
STIGMEM_STORAGE_BACKEND=postgres
STIGMEM_POSTGRES_DSN=postgresql://user:pass@host:5432/stigmem
```

The `pgvector` extension is **required** for Phase 9 vector-embedding recall:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run migrations:

```bash
stigmem migrate
```

**Availability note:** the Postgres backend ships in Phase 11. The conformance test suite (Phase 11) verifies parity with SQLite and libSQL. If you are on an earlier version, pin to libSQL.

**Recovery:** use your managed provider's PITR feature (RDS automated backups, Cloud SQL PITR, Neon branching). No Stigmem-specific snapshot configuration needed. See [Backup & restore](../runbooks/backup-restore) for the hybrid approach.

---

## Switching backends

Switching backends requires:

1. Stop the node.
2. Update env vars (`STIGMEM_STORAGE_BACKEND` and any backend-specific vars).
3. Run `stigmem migrate` — migrations are idempotent.
4. Restart the node.

:::caution Data migration
Switching backends does **not** copy existing data. Take a signed snapshot before switching, then manually migrate the data, or start fresh and re-federate.
:::

---

## Next step

Once you've chosen a backend, follow the [deploy runbook](../runbooks/deploy-runbooks) for your environment.
