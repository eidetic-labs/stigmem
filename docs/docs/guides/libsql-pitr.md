---
id: libsql-pitr
title: libSQL / Turso Point-in-Time Restore (PITR)
sidebar_label: libSQL PITR Runbook
---

# libSQL / Turso — Point-in-Time Restore (PITR)

**Audience:** Operators running Stigmem with `STIGMEM_STORAGE_BACKEND=libsql` and
a Turso cloud database.  
**Applies to:** Stigmem Phase 8 (libSQL/Turso adapter)

---

## Overview

When Stigmem runs in **embedded-replica mode** (local `libSQL` file +
`STIGMEM_LIBSQL_URL` sync to Turso), Turso manages point-in-time restore on the
cloud side.  The local replica is a read/write cache; the authoritative copy
lives in Turso's storage.

PITR lets you roll back to any second within your retention window without
needing a Stigmem snapshot — though the two mechanisms complement each other:

| Mechanism | Use case |
|---|---|
| **Turso PITR** | Fast rollback to a known-good timestamp (seconds); no Stigmem binary needed |
| **Stigmem signed snapshot** | Portable, integrity-verified backup; works offline and across providers |

---

## Prerequisites

- Turso Pro or Enterprise plan (PITR is not available on the free tier).
- Turso CLI installed: `curl -sSfL https://get.tur.so/install.sh | bash`
- The Stigmem node stopped or in read-only mode before any restore.

---

## Step 1 — Identify the restore target

List available PITR timestamps for your database:

```bash
turso db show <your-db-name> --pitr
```

Note the latest **healthy** timestamp (ISO-8601 UTC) before the incident.

---

## Step 2 — Stop the Stigmem node

```bash
# systemd
systemctl stop stigmem

# Fly.io
fly machine stop <machine-id>
```

The local replica file at `STIGMEM_DB_PATH` will be abandoned; the cloud copy
is authoritative.

---

## Step 3 — Restore the Turso database to the target timestamp

```bash
turso db restore <your-db-name> \
    --timestamp "2026-05-04T11:45:00Z" \
    --wait
```

`--wait` blocks until the restore is complete.  Turso creates a new branch (or
in-place restore depending on plan) that now serves data as of the given
timestamp.

---

## Step 4 — Delete or move the stale local replica

The local embedded-replica file is now out of sync with the restored cloud
database.  Delete it so libSQL re-syncs on next startup:

```bash
rm "$STIGMEM_DB_PATH"
# or
mv "$STIGMEM_DB_PATH" "${STIGMEM_DB_PATH}.pre-pitr-$(date +%Y%m%d%H%M%S)"
```

---

## Step 5 — Restart Stigmem

```bash
# systemd
systemctl start stigmem

# Fly.io
fly machine start <machine-id>
```

On startup, `LibSQLBackend._connect()` calls `conn.sync()` which pulls the
restored cloud state into the fresh local replica file.  Migrations are applied
idempotently via `apply_migrations()`.

---

## Step 6 — Verify

```bash
# Check the node is healthy
curl http://localhost:8765/.well-known/stigmem | jq .backend_name

# Verify schema migration cursor matches expectations
stigmem federation cursor-export | jq .cursors

# Spot-check fact counts
curl -s http://localhost:8765/v1/facts \
    -H "X-API-Key: $STIGMEM_API_KEY" | jq length
```

---

## Recovery from local-replica corruption only

If the **cloud database is healthy** but the local replica file is corrupted
(e.g., filesystem fault on the Fly.io volume):

1. Delete or rename `$STIGMEM_DB_PATH` (the local replica file only).
2. Restart the node — libSQL re-syncs from Turso automatically.

No Turso PITR or Stigmem snapshot restore is needed in this case.

---

## Combining PITR with Stigmem snapshots

For maximum durability, run both:

```bash
# Before any planned maintenance, take a Stigmem snapshot
stigmem snapshot create --out /backups/pre-maintenance.tar.gz

# ... maintenance window ...

# If Turso PITR fails or exceeds retention, fall back to the Stigmem snapshot
stigmem snapshot restore --from /backups/pre-maintenance.tar.gz
```

The Stigmem snapshot gives you a verifiable, portable backup that is independent
of Turso's retention policy or availability.

---

## Turso PITR retention

| Turso plan | Retention window |
|---|---|
| Free | No PITR |
| Pro | 24 hours |
| Enterprise | Configurable (30 days default) |

Check your plan limits at `turso db show <db-name>` or the Turso dashboard.

---

## References

- [Turso PITR documentation](https://docs.turso.tech/features/point-in-time-restore)
- [Turso CLI reference](https://docs.turso.tech/cli/introduction)
- [Stigmem libSQL/Turso setup](../backends.md)
- [Stigmem signed snapshots](./backup-restore.md)
- [Cursor-reset recovery](./cursor-reset-recovery.md)
