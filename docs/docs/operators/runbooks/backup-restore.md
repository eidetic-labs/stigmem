---
title: Backup & Restore
sidebar_label: Backup & Restore
description: Operator runbook for Stigmem backup and restore — signed snapshots, scheduled backups, verification, and cloud PITR.
audience: Operator
---

# Backup & Restore

**Audience:** node operators running Stigmem in production.  
**Spec reference:** snapshot signing uses the node's Ed25519 federation key (`Spec-05-Federation-Trust`).

---

## Quick reference

```bash
# Create a snapshot (content-addressed filename)
stigmem snapshot create

# Create with an explicit output path
stigmem snapshot create --out /backups/stigmem-$(date +%Y%m%d-%H%M%S).tar.gz

# Use an offline signing key instead of the node's built-in key
stigmem snapshot create --sign-with /secure/offline.key --out /backups/offline.tar.gz

# Verify before restoring
stigmem snapshot verify /backups/stigmem-20260601.tar.gz

# Restore (stops required; overwrites STIGMEM_DB_PATH)
stigmem snapshot restore /backups/stigmem-20260601.tar.gz

# Restore with explicit trusted-keys list (cross-node restore)
stigmem snapshot restore /backups/snap.tar.gz \
    --trusted-keys /etc/stigmem/trusted-backup-keys.json

# Emergency restore — bypass verification (LOUD WARNING logged)
stigmem snapshot restore /backups/snap.tar.gz --force-unverified
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

### Daily cron (host-side)

```bash
# /etc/cron.d/stigmem-backup
0 3 * * * stigmem docker exec stigmem-node-a stigmem snapshot create \
  --out /backups/stigmem-$(date +\%Y\%m\%d).tar.gz >> /var/log/stigmem-backup.log 2>&1
```

### Upload to S3-compatible storage

```bash
SNAP=$(stigmem snapshot create --out /tmp/snap.tar.gz && echo /tmp/snap.tar.gz)
aws s3 cp "$SNAP" "s3://your-bucket/stigmem/$(basename $SNAP)"
```

### Markdown export helper

The signed `stigmem snapshot` CLI is the canonical backup and restore path. For
operators who also want a human-readable markdown export for review, source
control, or incident response packets, the repo includes
[`scripts/stigmem-snapshot.sh`](https://github.com/Eidetic-Labs/stigmem/blob/main/scripts/stigmem-snapshot.sh).

The helper queries the HTTP API for a chosen scope and entity list, writes a
markdown report grouped by entity, and can include contradiction metrics. It
expects `curl`, `jq`, and either `STIGMEM_API_KEY` or `--api-key` when the node
requires auth.

```bash
scripts/stigmem-snapshot.sh \
  --node-url http://localhost:8765 \
  --scope team \
  --entities "team:ops,team:eng" \
  --output /var/backups/stigmem/team-export-$(date -u +%Y-%m-%d).md
```

Treat this export as a secondary operator artifact, not as a restore format. Use
the signed snapshot commands above for disaster recovery.

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

### Offline (secondary) signing key

For air-gapped or HSM-backed workflows, generate an Ed25519 offline key once:

```bash
python3 -c "
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
priv = Ed25519PrivateKey.generate()
raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub = priv.public_key().public_bytes_raw()
print('priv:', base64.urlsafe_b64encode(raw).rstrip(b'=').decode())
print('pub: ', base64.urlsafe_b64encode(pub).rstrip(b'=').decode())
"
```

Save `priv` to a file (e.g., `/secure/offline.key`, mode `0400`) and add `pub` to your trusted-keys file:

```json
["<base64url Ed25519 public key>", "<another key>"]
```

### Verification modes

| Mode | Behavior |
|---|---|
| Default (no flags) | Verifies using the node's own key or the manifest's self-declared key |
| `--trusted-keys FILE` | **Strict mode** — only keys in that file are trusted; node key and self-declared key are ignored |
| `--force-unverified` | Bypasses all checks; always logged at `WARNING`. Use only for disaster recovery when the signing key is lost |

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
6. **If the node participates in federation**, verify cursor state was captured in the snapshot:

   ```bash
   stigmem federation cursor-export --db $STIGMEM_DB_PATH
   ```

   If cursors were lost, see [Cursor-Reset Recovery](./cursor-reset-recovery) to import a checkpoint and avoid a full re-pull.

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

After restoring to a new Turso database, update `STIGMEM_LIBSQL_URL` in your secrets to point at the restored database and restart the node. For detailed libSQL point-in-time restore via the Turso replica protocol, see the [libSQL PITR guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/storage-libsql).

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

---

## Security notes

- Snapshot tarballs may contain sensitive fact data and secret peer keys. Store them with appropriate permissions and encrypt at rest.
- The Ed25519 signature covers the manifest body (artifact names + SHA-256 hashes + metadata) but not the signer's private key. Compromise of the private key lets an attacker forge future snapshots. Rotate the federation keypair and update your `trusted-backup-keys.json` if you suspect compromise — see [Key Rotation](../../security/key-rotation).
- `--force-unverified` is always logged at `WARNING` level regardless of the node's configured log level. Audit your logs after any forced restore.
