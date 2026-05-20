---
title: Cursor-Reset-on-DB-Loss Recovery
sidebar_label: DB-Loss Recovery
audience: Operator
---

# Cursor-Reset-on-DB-Loss Recovery

<p className="stigmem-meta"><span>5 min read</span><span>Federation operator</span><span>F2 hardening</span></p>

<div className="stigmem-lead">

**What this runbook covers**

When a node loses its `replication_cursors` table — through DB
corruption, an accidental `DROP TABLE`, or a bare-DB restore from
backup — the next federation pull resets every peer's cursor to
`NULL`. The pull loop re-fetches every fact from every peer from
scratch.

</div>

**Audience:** Node operators managing Stigmem federation in production.
**Spec reference:** `Spec-05-Federation-Trust` (federation pull loop, cursor semantics).
**Track:** F2 — pre-GA hardening.

## Problem

<div className="stigmem-keypoint">

**Cursor reset is safe (ingestion is idempotent on fact ID) but expensive.**

```
re-pull cost ≈ total_facts_per_peer × (pull_interval / page_size)
              = e.g. 500 000 facts × (10s / 100) = ~13 hours per peer
```

On a busy multi-peer mesh the compounding effect can delay
convergence for many hours and produce unusually high I/O and
network load. The `cursor-export` / `cursor-import` commands bound
this cost.

</div>

## Cursor-Checkpoint Workflow

### Export (before any DB operation)

Run this before planned DB maintenance (backup restore, migration, schema change):

```bash
# Timestamped checkpoint alongside the DB backup
stigmem federation cursor-export \
  --out /var/lib/stigmem/cursors-$(date +%Y%m%dT%H%M%S).json

# Or pipe to stdout
stigmem federation cursor-export | tee /backup/stigmem-cursors-latest.json
```

**Checkpoint format:**

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

**Recommended cron setup** — schedule `cursor-export` alongside your SQLite backup:

```cron
# every 15 minutes, write a cursor checkpoint next to the DB backup
*/15 * * * * stigmem federation cursor-export \
    --out /backup/stigmem-cursors-latest.json 2>>/var/log/stigmem/cursor-export.log
```

<div className="stigmem-keypoint">

**This bounds the re-pull window to at most 15 minutes of incremental facts after any DB loss event.**

</div>

## Recovery procedure (after DB loss)

Each step is idempotent — you can re-run safely.

### Step 1 — Stop the node

```bash
systemctl stop stigmem-node   # or: kill $(cat /run/stigmem.pid)
```

The pull loop must not be running while you restore the DB or import cursors.

### Step 2 — Restore the DB (or start fresh)

```bash
# If you have a DB backup:
cp /backup/stigmem-YYYYMMDD.db /var/lib/stigmem/stigmem.db

# If the DB is wholly lost, apply migrations before importing:
stigmem migrate normalize-entities --dry-run
```

### Step 3 — Re-register peers (if peer table is lost)

The FK constraint on `replication_cursors` requires each peer row to exist. If the peer table is gone (fresh DB or pre-migration 002), re-register peers first:

```bash
stigmem federation register-peer \
    --remote-url http://node-b:8765 \
    --local-url  http://this-node:8765 \
    --scopes company,public
# repeat for each peer
```

Peers absent from the `peers` table are **skipped with a warning** during import — re-register them, then re-run `cursor-import`.

### Step 4 — Import the checkpoint

```bash
stigmem federation cursor-import /backup/stigmem-cursors-latest.json
```

Expected output:

```
cursor import complete: 3 restored, 0 skipped (peer not found), 0 skipped (already set)
```

<div className="stigmem-keypoint">

**Default import skips cursors that already have non-null values.**

If the restored DB already has non-null cursors from the backup,
import skips them by default to avoid regressing a newer cursor. Use
`--force` to override.

</div>

### Step 5 — Start the node

```bash
systemctl start stigmem-node
```

The pull loop reads restored cursors and resumes from the checkpointed positions rather than from `NULL` (the beginning of replication time).

### Step 6 — Verify

Watch logs for resume vs. full-re-pull patterns:

```
# Healthy cursor resume — expected after import
INFO  pull from stigmem://node-b: cursor=1725349500000.005, got 12 facts, has_more=false

# Full re-pull — import was skipped or peer not found
INFO  pull from stigmem://node-b: cursor=None, got 100 facts, has_more=true
```

If you see `cursor=None` for a peer after import, that peer was not found in the peers table. Re-register it and re-run `cursor-import --force`.

## Recovery without a Checkpoint

If no checkpoint is available, the node performs a full re-pull. This is safe. To minimize impact:

<ol className="stigmem-steps">
<li>Start the node during off-peak hours.</li>
<li>Temporarily reduce <code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code> (e.g., to <code>5</code>) to complete the re-pull faster, then restore the original value.</li>
<li>Monitor the <code>facts</code> table row count; re-pull is complete when it stabilizes.</li>
</ol>

<div className="stigmem-keypoint">

**PACELC contract: during re-pull the node is available for local writes and reads.**

Facts from peers not yet re-fetched are temporarily absent. This is
the system's existing PA/EL contract — idempotent ingestion ensures
no duplicates.

</div>

## Operational Recommendations

<div className="stigmem-fields">

<div>
<dt>Practice</dt>
<dt><span className="stigmem-fields__type">Cadence</span></dt>
<dd>Rationale</dd>
</div>

<div>
<dt>Schedule <code>cursor-export</code> every 15 min</dt>
<dt><span className="stigmem-fields__type">15 min</span></dt>
<dd>Bounds re-pull to ≤15 min of missed incremental facts.</dd>
</div>

<div>
<dt>Validate <code>replication_cursors</code> in DB backups</dt>
<dt><span className="stigmem-fields__type">per backup</span></dt>
<dd>Detects silent table loss before an incident.</dd>
</div>

<div>
<dt>Store checkpoint file outside DB directory</dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>Survives disk corruption that takes the DB file.</dd>
</div>

<div>
<dt>Run <code>cursor-export</code> before planned DB maintenance</dt>
<dt><span className="stigmem-fields__type">pre-change</span></dt>
<dd>Zero-cost re-pull resume even for planned operations.</dd>
</div>

</div>

## CLI Reference

### `stigmem federation cursor-export`

```
usage: stigmem federation cursor-export [--out FILE] [--db PATH]

  --out FILE   Output path. Use "-" or omit for stdout. (default: stdout)
  --db PATH    Path to stigmem.db. (default: STIGMEM_DB_PATH or settings default)
```

Exits 0 on success. Checkpoint JSON written to `FILE` or stdout.

### `stigmem federation cursor-import`

```
usage: stigmem federation cursor-import FILE [--force] [--db PATH]

  FILE         Checkpoint JSON produced by cursor-export (required).
  --force      Overwrite cursors that are already non-null. (default: skip)
  --db PATH    Path to stigmem.db. (default: STIGMEM_DB_PATH or settings default)
```

Entries whose `peer_id` is absent from the `peers` table are skipped with a warning — re-register the peer first and re-run.

## Invariants Preserved

<div className="stigmem-grid">

<div><h4>Idempotent ingest</h4><p>Re-pulled facts already in the DB are silently discarded (no duplicates).</p></div>
<div><h4>Lower-bound cursor</h4><p>If the checkpoint is older than the actual last-seen HLC, the node re-fetches a small window of already-seen facts (harmless) rather than missing any.</p></div>
<div><h4>No regression without --force</h4><p><code>cursor-import</code> only fills <code>NULL</code> slots by default, so it cannot cause data loss on a partially-intact DB.</p></div>

</div>

## See also

<div className="stigmem-grid">

<div><h4><a href="../../concepts/federation/">Federation guide</a></h4><p>Peer registration, pull loop, and scope enforcement.</p></div>
<div><h4><a href="../../concepts/federation/#soak-results">4-node soak results</a></h4><p>Cursor-resume behavior verified under failure injection.</p></div>

</div>
