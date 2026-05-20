---
title: Backup & Restore
sidebar_label: Backup & Restore
description: Operator runbook for Stigmem backup and restore — signed snapshots, scheduled backups, verification, and cloud PITR.
audience: Operator
---

# Backup & Restore

<p className="stigmem-meta"><span>5 min read</span><span>Node operator</span><span>DR runbook</span></p>

<div className="stigmem-lead">

**What this runbook covers**

Signed snapshots, scheduled backups, verification, and cloud
point-in-time recovery for libSQL and Postgres.

</div>

**Audience:** node operators running Stigmem in production.
**Spec reference:** snapshot signing uses the node's Ed25519 federation key (`Spec-05-Federation-Trust`).

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

## What a snapshot captures

```
stigmem-snapshot-<timestamp>-<hash>.tar.gz
├── manifest.json          ← SHA-256 hashes of all artifacts + Ed25519 signature
└── artifacts/
    ├── stigmem.db                     ← full database
    └── schema_migration_cursor.json   ← applied migration versions
```

<div className="stigmem-keypoint">

**The signature uses the node's federation private key (`STIGMEM_FEDERATION_PRIVKEY`).**

Verification checks the signature and every artifact hash before
restore proceeds.

</div>

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

The signed `stigmem snapshot` CLI is the canonical backup and restore path. For operators who also want a human-readable markdown export for review, source control, or incident response packets, the repo includes [`scripts/stigmem-snapshot.sh`](https://github.com/eidetic-labs/stigmem/blob/main/scripts/stigmem-snapshot.sh).

```bash
scripts/stigmem-snapshot.sh \
  --node-url http://localhost:8765 \
  --scope team \
  --entities "team:ops,team:eng" \
  --output /var/backups/stigmem/team-export-$(date -u +%Y-%m-%d).md
```

<div className="stigmem-keypoint">

**Treat the markdown export as a secondary operator artifact, not as a restore format.**

Use the signed snapshot commands above for disaster recovery.

</div>

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

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>Use case</dd>
</div>

<div>
<dt>Default (no flags)</dt>
<dt><span className="stigmem-fields__type">self-key OK</span></dt>
<dd>Verifies using the node's own key or the manifest's self-declared key.</dd>
</div>

<div>
<dt><code>--trusted-keys FILE</code></dt>
<dt><span className="stigmem-fields__type">strict</span></dt>
<dd>Only keys in that file are trusted; node key and self-declared key are ignored.</dd>
</div>

<div>
<dt><code>--force-unverified</code></dt>
<dt><span className="stigmem-fields__type">DR only</span></dt>
<dd>Bypasses all checks; always logged at <code>WARNING</code>. Use only for disaster recovery when the signing key is lost.</dd>
</div>

</div>

## Restore procedure

<ol className="stigmem-steps">
<li><strong>Stop the node.</strong></li>
<li><strong>Back up the current database</strong> (belt and suspenders): <code>cp $STIGMEM_DB_PATH "$&#123;STIGMEM_DB_PATH&#125;.pre-restore-backup"</code></li>
<li><strong>Verify the snapshot</strong> (see above).</li>
<li><strong>Run restore:</strong> <code>stigmem snapshot restore /backups/stigmem-20260601.tar.gz</code>. The restore step verifies checksums and signature, writes the database file to <code>STIGMEM_DB_PATH</code>, and replays any migrations newer than the snapshot cursor.</li>
<li><strong>Restart the node.</strong></li>
<li><strong>If the node participates in federation</strong>, verify cursor state: <code>stigmem federation cursor-export --db $STIGMEM_DB_PATH</code>. If cursors were lost, see <a href="./cursor-reset-recovery">Cursor-Reset Recovery</a>.</li>
</ol>

:::caution
Restore overwrites `STIGMEM_DB_PATH` without confirmation. The pre-restore backup in step 2 is your safety net.
:::

## Cloud PITR (libSQL and Postgres)

### libSQL / Turso

```bash
# List available snapshots
turso db snapshot list stigmem-prod

# Restore to a point in time (creates a new Turso database)
turso db restore stigmem-prod --timestamp 2026-06-01T03:00:00Z --name stigmem-restored
```

After restoring to a new Turso database, update `STIGMEM_LIBSQL_URL` in your secrets to point at the restored database and restart the node.

### Postgres

Use your managed provider's PITR feature:

<div className="stigmem-grid">

<div><h4>RDS</h4><p>Automated backups + point-in-time restore in the AWS Console or CLI.</p></div>
<div><h4>Cloud SQL</h4><p><code>gcloud sql instances clone</code> with a <code>--point-in-time</code> flag.</p></div>
<div><h4>Neon</h4><p>Branch from a historical point via the Neon console.</p></div>
<div><h4>Supabase</h4><p>PITR is a Pro feature; contact support.</p></div>

</div>

No Stigmem-specific restore command is needed for Postgres. The node picks up the restored data on restart.

## Retention policy

<div className="stigmem-fields">

<div>
<dt>Backup type</dt>
<dt><span className="stigmem-fields__type">Frequency</span></dt>
<dd>Retention</dd>
</div>

<div>
<dt>Signed snapshot (SQLite)</dt>
<dt><span className="stigmem-fields__type">Daily</span></dt>
<dd>30 days local, 90 days offsite.</dd>
</div>

<div>
<dt>Turso PITR</dt>
<dt><span className="stigmem-fields__type">Continuous</span></dt>
<dd>7 days (Turso default).</dd>
</div>

<div>
<dt>Postgres automated backup</dt>
<dt><span className="stigmem-fields__type">Daily</span></dt>
<dd>7–35 days (provider dependent).</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Test restore from backup at least once per quarter.**

</div>

## Security notes

<div className="stigmem-grid">

<div><h4>Sensitive contents</h4><p>Snapshot tarballs may contain sensitive fact data and secret peer keys. Store with appropriate permissions and encrypt at rest.</p></div>
<div><h4>Signature scope</h4><p>The Ed25519 signature covers the manifest body but not the signer's private key. Rotate the federation keypair and update <code>trusted-backup-keys.json</code> if you suspect compromise.</p></div>
<div><h4>Forced restore audit</h4><p><code>--force-unverified</code> is always logged at <code>WARNING</code> level regardless of the node's configured log level. Audit your logs after any forced restore.</p></div>

</div>
