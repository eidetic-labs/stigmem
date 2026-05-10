# Cursor-Reset-on-DB-Loss Recovery Procedure

**Failure mode:** FM-3 edge case — [failure-modes-4node.md § FM-3](./failure-modes-4node.md)  
**Track:** F (pre-GA hardening)  
**Protocol version:** stigmem spec pre-reset-draft (§6)

---

## Problem

When a node loses its `replication_cursors` table — through DB corruption, an
accidental `DROP TABLE`, or a bare-DB restore from backup — the next federation
pull resets every peer's cursor to `NULL` (the beginning of replication time).
The pull loop then re-fetches every fact from every peer from scratch.

This is **safe** (ingestion is idempotent on fact ID) but **expensive**:

```
re-pull cost ≈ total_facts_per_peer × (pull_interval / page_size)
              = e.g. 500 000 facts × (10s / 100) = ~13 hours per peer
```

On a busy multi-peer mesh the compounding effect can delay convergence for
many hours and produce unusually high I/O and network load.

The procedures below bound this cost.

---

## Cursor-Checkpoint Workflow

### Before a DB operation (export)

Run this on the live node before any planned DB maintenance (backup restore,
migration, schema change):

```bash
# Export to a timestamped file alongside the DB
stigmem federation cursor-export --out /var/lib/stigmem/cursors-$(date +%Y%m%dT%H%M%S).json

# Or export to stdout and pipe to a safe location
stigmem federation cursor-export | tee /backup/stigmem-cursors-latest.json
```

Checkpoint format:

```json
{
  "checkpoint_timestamp": "2026-05-02T18:30:00Z",
  "db_path": "/var/lib/stigmem/stigmem.db",
  "cursors": [
    {
      "peer_id": "a1b2c3d4-...",
      "peer_node_id": "stigmem://node-b",
      "peer_url": "http://node-b:8765",
      "peer_status": "active",
      "direction": "inbound",
      "cursor": "1725349500000.005",
      "updated_at": "2026-05-02T18:25:00Z"
    }
  ]
}
```

**Recommendation:** schedule `cursor-export` as a cron job alongside your
SQLite backup so you always have a recent checkpoint:

```cron
# every 15 minutes, write a cursor checkpoint next to the DB backup
*/15 * * * * stigmem federation cursor-export \
    --out /backup/stigmem-cursors-latest.json 2>>/var/log/stigmem/cursor-export.log
```

---

### After DB loss (import)

Follow these steps in order. Each step is idempotent — you can re-run safely.

#### Step 1 — Stop the node

```bash
systemctl stop stigmem-node   # or: kill $(cat /run/stigmem.pid)
```

The pull loop must not be running while you restore the DB or import cursors.

#### Step 2 — Restore the DB (or start fresh)

If you have a DB backup, restore it:

```bash
cp /backup/stigmem-YYYYMMDD.db /var/lib/stigmem/stigmem.db
```

If the DB is wholly lost and you are starting from scratch, the node will
create a new empty DB on first startup; apply migrations before importing:

```bash
stigmem migrate normalize-entities --dry-run   # triggers migration apply
```

#### Step 3 — Re-register peers (if peer table is lost)

If the peer table is also lost (fresh DB or DB pre-migration 002), re-register
each peer before importing cursors — the FK constraint on `replication_cursors`
requires the peer row to exist:

```bash
stigmem federation register-peer \
    --remote-url http://node-b:8765 \
    --local-url  http://this-node:8765 \
    --scopes company,public
# repeat for each peer
```

Peers whose `peer_id` is absent from the `peers` table are **skipped with a
warning** during import; re-register them first, then re-run `cursor-import`.

#### Step 4 — Import the checkpoint

```bash
stigmem federation cursor-import /backup/stigmem-cursors-latest.json
```

Expected output (stderr):

```
cursor import complete: 3 restored, 0 skipped (peer not found), 0 skipped (already set)
```

If some peers were already present in the restored DB with non-null cursors
(e.g., from the DB backup), the import skips them by default to avoid
regressing a newer cursor to an older checkpoint value. Use `--force` to
override:

```bash
stigmem federation cursor-import --force /backup/stigmem-cursors-latest.json
```

#### Step 5 — Start the node

```bash
systemctl start stigmem-node
```

The pull loop reads the restored cursors and resumes from the checkpointed
positions rather than from the beginning.

#### Step 6 — Verify

Watch logs for re-pull activity. A healthy resume looks like:

```
INFO  pull from stigmem://node-b: cursor=1725349500000.005, got 12 facts, has_more=false
```

A cursor-reset full-re-pull looks like:

```
INFO  pull from stigmem://node-b: cursor=None, got 100 facts, has_more=true
```

If you see `cursor=None` for a peer after import, that peer was skipped
(not found or not yet re-registered). Re-register the peer and re-run
`cursor-import --force`.

---

## Recovery without a Checkpoint

If no checkpoint file is available, the node will perform a full re-pull.
This is safe. To minimize impact:

1. Start the node during off-peak hours.
2. Consider temporarily reducing `STIGMEM_FEDERATION_PULL_INTERVAL_S` (e.g.,
   to 5s) to saturate bandwidth and complete the re-pull faster, then restore
   the original interval.
3. Monitor the `facts` table row count; re-pull is complete when it stabilizes
   near the pre-loss count.

**PACELC note:** During re-pull, the node is available for local writes and
reads but facts from peers that have not yet been re-fetched are temporarily
absent. This matches the system's existing PA/EL (availability over consistency,
eventual convergence) contract. The full re-pull does not violate any protocol
invariant — idempotent ingestion ensures no duplicates.

---

## Operational Recommendations

| Practice | Rationale |
|---|---|
| Schedule `cursor-export` every 15 min alongside DB backup | Bounds re-pull to at most 15 min of missed incremental facts |
| Keep `replication_cursors` rows in DB backup validation checks | Detects silent table loss before an incident |
| Store checkpoint file outside the node's DB directory | Survives disk corruption that takes the DB file |
| Run `cursor-export` before any planned DB maintenance | Zero-cost re-pull resume even for planned operations |

---

## CLI Reference

### `stigmem federation cursor-export`

```
usage: stigmem federation cursor-export [--out FILE] [--db PATH]

  --out FILE   Output path. Use "-" or omit for stdout. (default: stdout)
  --db PATH    Path to stigmem.db. (default: STIGMEM_DB_PATH or settings default)
```

Exits 0 on success. Checkpoint JSON written to FILE or stdout.

### `stigmem federation cursor-import`

```
usage: stigmem federation cursor-import FILE [--force] [--db PATH]

  FILE         Checkpoint JSON produced by cursor-export (required).
  --force      Overwrite cursors that are already non-null. (default: skip)
  --db PATH    Path to stigmem.db. (default: STIGMEM_DB_PATH or settings default)
```

Exits 0 on success. Prints a summary of restored / skipped entries to stderr.

Entries whose `peer_id` is absent from the `peers` table are skipped with a
warning — re-register the peer first and re-run.

---

## Invariants Preserved

- Ingest is idempotent: if the node re-pulls facts it already has, they are
  silently discarded (no duplicates, no extra contradiction records).
- The recovered cursor is a lower bound: if the checkpoint is older than the
  actual last-seen HLC, the node re-fetches a small window of already-seen
  facts (harmless) rather than missing any.
- `cursor-import` without `--force` never regresses a live cursor — it only
  fills in `NULL` slots, so it cannot cause data loss even if run on a
  partially-intact DB.
