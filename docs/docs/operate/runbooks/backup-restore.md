---
id: backup-restore
title: Backup & Restore
sidebar_label: Backup & Restore
description: Operator runbook for Stigmem backup and restore — signed snapshots, scheduled backups, verification, and cloud PITR.
---

# Backup & Restore

**Audience:** node operators running Stigmem in production.  
**Spec reference:** snapshot signing uses the node's Ed25519 federation key (§6).  
**Full reference:** [Backup & Restore guide](../guides/backup-restore) for detailed CLI options and advanced scenarios.

---

## Quick reference

```bash
# Create a snapshot (content-addressed filename)
stigmem snapshot create

# Create with an explicit output path
stigmem snapshot create --out /backups/stigmem-$(date +%Y%m%d-%H%M%S).tar.gz

# Verify before restoring
stigmem snapshot verify /backups/stigmem-20260601.tar.gz

# Restore (stops required; overwrites STIGMEM_DB_PATH)
stigmem snapshot restore /backups/stigmem-20260601.tar.gz
```

---

## What a snapshot captures

Every snapshot is a signed tarball:

```
stigmem-snapshot-<timestamp>-<hash>.tar.gz
├── manifest.json          ← SHA-256 hashes of all artifacts + Ed25519 signature
└── artifacts/
    ├── stigmem.db                     ← full database
    └── schema_migration_cursor.json   ← applied migration versions
```

The signature uses the node's federation private key (`STIGMEM_FEDERATION_PRIVKEY`). Verification checks the signature and every artifact hash before restore proceeds.

---

## Scheduling backups

### Daily cron (systemd or bare metal)

```bash
# /etc/cron.d/stigmem-backup
0 3 * * * stigmem /usr/local/bin/stigmem snapshot create \
  --out /backups/stigmem-$(date +\%Y\%m\%d).tar.gz >> /var/log/stigmem-backup.log 2>&1
```

### Fly.io scheduled machine

```bash
# Run a one-off machine daily at 03:00 UTC to snapshot and upload to S3
fly machine run ghcr.io/eidetic-labs/stigmem:latest \
  --schedule daily \
  --env STIGMEM_DB_PATH=/app/data/stigmem.db \
  --command "stigmem snapshot create --out /backups/snap.tar.gz && \
             aws s3 cp /backups/snap.tar.gz s3://your-bucket/stigmem/"
```

### Upload to S3-compatible storage

```bash
SNAP=$(stigmem snapshot create --out /tmp/snap.tar.gz && echo /tmp/snap.tar.gz)
aws s3 cp "$SNAP" "s3://your-bucket/stigmem/$(basename $SNAP)"
```

---

## Verifying a snapshot

**Always verify before restoring.** The verify step checks SHA-256 hashes and the Ed25519 manifest signature:

```bash
stigmem snapshot verify /backups/stigmem-20260601.tar.gz
# OK: sha256 checksums valid, signature verified (key: stigmem:node:<uuid>)

# Verify against a specific trusted key (e.g. restoring to a different node)
stigmem snapshot verify /backups/stigmem-20260601.tar.gz \
  --trusted-key <base64url-ed25519-pubkey>
```

If verify fails with `signature_mismatch` or `checksum_error`, do not restore — the snapshot may be corrupt or tampered.

---

## Restore procedure

1. **Stop the node.**
2. **Back up the current database** (belt and suspenders):

   ```bash
   cp $STIGMEM_DB_PATH "${STIGMEM_DB_PATH}.pre-restore-backup"
   ```

3. **Verify the snapshot** (see above).
4. **Run restore:**

   ```bash
   stigmem snapshot restore /backups/stigmem-20260601.tar.gz
   ```

   The restore step:
   - Verifies checksums and signature.
   - Writes the database file to `STIGMEM_DB_PATH`.
   - Replays any migrations newer than the snapshot cursor.

5. **Restart the node.**

:::caution
Restore overwrites `STIGMEM_DB_PATH` without confirmation. The pre-restore backup in step 2 is your safety net.
:::

---

## Cloud PITR (libSQL and Postgres)

### libSQL / Turso

Turso provides point-in-time recovery on the cloud primary without node downtime:

```bash
# List available snapshots
turso db snapshot list stigmem-prod

# Restore to a point in time (creates a new Turso database)
turso db restore stigmem-prod --timestamp 2026-06-01T03:00:00Z --name stigmem-restored
```

After restoring to a new Turso database, update `STIGMEM_LIBSQL_URL` in your secrets to point at the restored database and restart the node.

### Postgres

Use your managed provider's PITR feature:

- **RDS:** automated backups + point-in-time restore in the AWS Console or CLI
- **Cloud SQL:** `gcloud sql instances clone` with a `--point-in-time` flag
- **Neon:** branch from a historical point via the Neon console
- **Supabase:** contact support — PITR is a Pro feature

No Stigmem-specific restore command is needed for Postgres. The node picks up the restored data on restart.

---

## Retention policy

Decide on a retention window before production traffic arrives. A reasonable starting point:

| Backup type | Frequency | Retention |
|---|---|---|
| Signed snapshot (SQLite) | Daily | 30 days local, 90 days offsite |
| Turso PITR | Continuous | 7 days (Turso default) |
| Postgres automated backup | Daily | 7–35 days (provider dependent) |

Test restore from backup at least once per quarter.
