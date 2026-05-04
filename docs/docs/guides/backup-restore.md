---
id: backup-restore
title: Backup & Restore (Signed Snapshots)
sidebar_label: Backup & Restore
---

# Backup & Restore — Signed Snapshots

**Audience:** Node operators running Stigmem in production.  
**Spec reference:** Phase 8 storage hardening  
**CLI:** `stigmem snapshot create` / `stigmem snapshot restore`

---

## Overview

Stigmem ships first-class backup/restore tooling that produces **signed,
content-addressed tarballs**.  Every snapshot includes a `manifest.json` whose
body is signed with the node's Ed25519 federation identity key (the same key
used for peer tokens and peer declarations — spec §6).  Before any restore
completes, the node verifies the signature and the SHA-256 hash of every
artifact, refusing to proceed on mismatch.

### What a snapshot captures

| Artifact | Description |
|---|---|
| `artifacts/stigmem.db` | Full online backup of the SQLite database (all facts, ACLs, gardens, audit log, peer metadata) |
| `artifacts/schema_migration_cursor.json` | List of applied schema migration versions |

### Tarball structure

```
stigmem-snapshot-20260504T120000Z-abc123def456.tar.gz
├── manifest.json          ← signed manifest with artifact hashes
└── artifacts/
    ├── stigmem.db
    └── schema_migration_cursor.json
```

---

## Quick start

### Create a snapshot

```bash
# Automatic content-addressed filename in the current directory
stigmem snapshot create

# Explicit output path
stigmem snapshot create --out /backups/stigmem-2026-05-04.tar.gz

# Use a secondary (offline) signing key instead of the node's built-in key
stigmem snapshot create --sign-with /secure/offline.key --out /backups/offline.tar.gz

# Custom database path
stigmem snapshot create --db /data/stigmem.db --out /backups/snap.tar.gz
```

### Restore a snapshot

```bash
# Restore in place (verifies using local node key + self-declared key)
stigmem snapshot restore --from /backups/stigmem-2026-05-04.tar.gz

# Restore to a different database path
stigmem snapshot restore --from /backups/snap.tar.gz --db /data/stigmem.db

# Restrict verification to an explicit trusted-keys list
stigmem snapshot restore --from /backups/snap.tar.gz \
    --trusted-keys /etc/stigmem/trusted-backup-keys.json

# Emergency restore — bypass verification (LOUD WARNING logged)
stigmem snapshot restore --from /backups/snap.tar.gz --force-unverified
```

---

## Signing & verification

### Default: node federation key

When `--sign-with` is omitted, `snapshot create` reads (or generates) the
node's Ed25519 federation keypair from `node_meta` in the local database.  This
is the same key published in `/.well-known/stigmem` and used to sign peer
declarations.

On restore, if no `--trusted-keys` file is given, the node tries:

1. Its own federation public key from the local `node_meta` table.
2. The public key declared in the manifest itself (self-attesting mode —
   convenient for single-operator setups where you're restoring the same node
   from one of its own snapshots).

### Secondary (offline) signing key

For air-gapped or HSM-backed offline backup workflows, generate an offline
signing key once and store it securely:

```bash
# Generate a raw Ed25519 private key (32 bytes, base64url-encoded)
python3 - <<'EOF'
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

priv = Ed25519PrivateKey.generate()
raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub = priv.public_key().public_bytes_raw()
print("priv:", base64.urlsafe_b64encode(raw).rstrip(b"=").decode())
print("pub: ", base64.urlsafe_b64encode(pub).rstrip(b"=").decode())
EOF
```

Save `priv` to a file (e.g., `/secure/offline.key`, mode `0400`) and add `pub`
to your trusted-keys file.

**trusted-backup-keys.json** format:

```json
["<base64url Ed25519 public key>", "<another key>"]
```

### When `--trusted-keys` is provided

Providing `--trusted-keys` puts the restore into **strict mode**: only the keys
in that file are trusted.  The node's own key and the self-declared manifest key
are **not** consulted.  Use this when restoring snapshots signed by a different
node or an offline key.

### `--force-unverified`

Bypasses all signature and hash checks.  Always logged at `WARNING` level with
a prominent security notice.  Only use this for disaster recovery when the
signing key has been lost and you have no other option.

---

## Scheduled backups

Use `cron` or Fly.io's Machine scheduled runs to automate snapshots:

```bash
# /etc/cron.d/stigmem-backup
0 2 * * * stigmem-node stigmem snapshot create --out /backups/stigmem-$(date +\%Y\%m\%d).tar.gz
```

Rotate the backups directory with your preferred policy (e.g., `logrotate` or
object-storage lifecycle rules).

---

## Restore after full DB loss

1. Stop the Stigmem node (to prevent writes during restore).
2. Run the restore command against the destination DB path:
   ```bash
   stigmem snapshot restore --from /backups/stigmem-latest.tar.gz --db /data/stigmem.db
   ```
3. Restart the node.  The server will detect the restored schema and start
   serving traffic immediately.
4. If the node was participating in federation: resume cursor positions.
   ```bash
   # Optional: verify cursor state was captured in the snapshot
   stigmem federation cursor-export --db /data/stigmem.db
   ```

For libSQL / Turso deployments, see the [libSQL PITR Runbook](./libsql-pitr.md)
which covers point-in-time restore via the Turso replica protocol.

---

## Security notes

- Snapshot tarballs may contain sensitive fact data and secret peer keys.
  Store them with appropriate permissions and encrypt at rest.
- The Ed25519 signature covers the manifest body (artifact names + SHA-256
  hashes + metadata) but not the signer's private key.  Compromise of the
  private key lets an attacker forge future snapshots.  Rotate the federation
  keypair and update your `trusted-backup-keys.json` if you suspect compromise.
- `--force-unverified` is always logged at `WARNING` level regardless of the
  node's configured log level.  Audit your logs after any forced restore.
