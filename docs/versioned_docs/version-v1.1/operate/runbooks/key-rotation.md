---
id: key-rotation
title: Key Rotation
sidebar_label: Key Rotation
description: Runbooks for rotating Stigmem encryption passphrases and federation keypairs with minimal disruption.
audience: Operator
---

# Key Rotation

**Audience:** operators and security engineers managing key lifecycle in production.  
**Spec reference:** §22.2 Key Rotation, §19.3.2 Max Token TTL; encryption key derivation in storage hardening; federation keys §5.3, §6.

There are three distinct key types to rotate:

| Key type | Purpose | Rotation impact | Max rotation cadence (§22.2.4) |
|---|---|---|---|
| **Encryption passphrase** | At-rest encryption of the database file | Node must stop; no peer impact | — |
| **Node identity key** (Ed25519) | Federation peer authentication, snapshot signing, manifest self-signature | All pinned peers must re-pin or auto-refresh | ≤ 365 days |
| **Capability issuer key** (Ed25519) | Signing capability tokens issued to subjects | In-flight tokens valid during dual-trust window | ≤ 90 days |

Both Ed25519 key types use a **dual-trust window** (§22.2.2): the retiring key remains in the accept-set for at least 90 days — long enough to cover all in-flight tokens (max TTL is 90 days per §19.3.2).

---

## Rotating the encryption passphrase

:::caution Node must be stopped
At-rest re-encryption requires exclusive database access. Stop the node before rekeying.
:::

### Prerequisites

- `stigmem-node[encryption,sqlcipher]` installed
- Old and new passphrases in separate environment variables

### Procedure

```bash
# 1. Stop the node
systemctl stop stigmem        # systemd
fly scale count 0             # Fly.io (or pause/stop the machine)
docker compose stop node      # Docker Compose

# 2. Export the old and new passphrases into env vars
export OLD_PASSPHRASE_VAR=STIGMEM_OLD_KEY
export NEW_PASSPHRASE_VAR=STIGMEM_NEW_KEY
export STIGMEM_OLD_KEY="old-strong-passphrase"
export STIGMEM_NEW_KEY="new-strong-passphrase"

# 3. Run rekey
stigmem db rekey \
  --old-passphrase-env OLD_PASSPHRASE_VAR \
  --new-passphrase-env NEW_PASSPHRASE_VAR

# Expected output:
# → Rekeying stigmem.db ... done.
# → WAL checkpoint complete.
# → VACUUM complete.

# 4. Update your secrets manager with the new passphrase
#    (Fly secrets, AWS Secrets Manager, Vault, etc.)
fly secrets set STIGMEM_DB_PASSPHRASE="new-strong-passphrase"

# 5. Update the env var name in STIGMEM_AT_REST_KEY_PASSPHRASE_ENV if it changed
#    and remove the old passphrase from secrets

# 6. Restart the node
systemctl start stigmem
fly scale count 1
docker compose start node

# 7. Verify
curl -s https://your-node.example.com/healthz
# → {"status":"ok","backend":"sqlite"}
```

:::caution Passphrase loss = data loss
If you lose the passphrase, the database file is irrecoverable. Store it only in a secrets manager — never in `fly.toml`, `docker-compose.yml`, or version control.
:::

---

## Rotating the federation keypair

Rotating the federation keypair changes your node's cryptographic identity. All peers that have pinned your current public key will stop trusting pull responses signed by the new key — you must coordinate the rotation with each peer operator.

### Step 1 — Generate a new keypair

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes_raw()
pub_bytes  = priv.public_key().public_bytes_raw()
print('NEW_STIGMEM_FEDERATION_PRIVKEY=' + base64.urlsafe_b64encode(priv_bytes).decode())
print('NEW_STIGMEM_FEDERATION_PUBKEY='  + base64.urlsafe_b64encode(pub_bytes).decode())
"
```

### Step 2 — Announce the rotation to peer operators

Share your new public key with each operator who has your node pinned. They must update the pin **after** you restart with the new key. Coordinate a maintenance window if you have many peers.

### Step 3 — Update your secrets and restart

```bash
# Fly.io
fly secrets set \
  STIGMEM_FEDERATION_PUBKEY="<new-pub>" \
  STIGMEM_FEDERATION_PRIVKEY="<new-priv>"
fly deploy   # or fly machine restart

# systemd — edit /etc/stigmem/env, then:
systemctl restart stigmem

# Docker Compose — edit .env, then:
docker compose up -d node
```

### Step 4 — Verify new key is live

```bash
curl -s https://your-node.example.com/.well-known/stigmem | jq .public_key
# → "<new-base64url-pub>"
```

### Step 5 — Ask peer operators to re-pin

Each peer operator runs:

```bash
# On each peer that had your old key pinned:
NEW_KEY=$(curl -s https://your-node.example.com/.well-known/stigmem | jq -r .public_key)

curl -X PATCH https://their-node.example.com/v1/federation/peers/<your-peer-id> \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"trusted_public_key\": \"$NEW_KEY\"}"
```

Until they update the pin, pull attempts from their node to yours will fail with `signature_mismatch` in their audit log.

### Step 6 — Update snapshot signing

Snapshots taken after the rotation are signed with the new key. Snapshots taken before the rotation can only be verified with the old public key — keep the old public key on record for snapshot archival verification.

```bash
# Verify an old snapshot with the old public key
stigmem snapshot verify /backups/old-snap.tar.gz --trusted-key <old-base64url-pubkey>
```

---

## CLI-based rotation (spec §22.2)

The `stigmem identity rotate-key` command handles key generation, dual-trust window setup, and transparency-log entries in a single step:

```bash
# Dry-run first — shows new key_id and dual-trust expiry without committing
stigmem identity rotate-key --kind node --dry-run

# Commit the rotation
stigmem identity rotate-key --kind node
# Output:
#   old key_id : a1b2c3d4e5f60001
#   new key_id : 9f8e7d6c5b4a0002
#   dual-trust : 2026-08-02T12:00:00Z
#   ACTION REQUIRED — update your secrets manager with the new private key

# Rotate the capability issuer key
stigmem identity rotate-key --kind issuer

# Extend dual-trust window beyond the 90-day minimum
stigmem identity rotate-key --kind node --dual-trust-days 120
```

Each rotation writes a `RotationEvent` to the org manifest (signed by the **retiring** key, anchoring trust to the prior identity) and two transparency-log entries: the updated manifest and a `KeyRotationLogEntry`.

After committing, update your secrets manager and restart the node — the same steps as the manual procedure in [Step 3](#step-3--update-your-secrets-and-restart) above. Peers refresh manifests automatically during their `refresh_peer_manifests()` sweep.

---

## Threat model

| Threat | Mitigation |
|---|---|
| Stolen retiring key during window | Revoke all tokens issued under that key via `capability revoke`; rotate again |
| Forged rotation event | Rotation event signature must verify under the retiring key |
| Key reuse / regression attack | `verify_rotation_chain` rejects any `new_key_id` already seen in the chain |
| TL unavailable during rotation | In `trust_mode=strict`, TL failure surfaces as a hard error; use `--dry-run` to pre-check |
| Dual-trust window too short | CLI enforces minimum 90 days; spec §22.2.2 prohibits shorter windows |

---

## Rotation checklist

### Encryption passphrase rotation

- [ ] Node stopped
- [ ] `stigmem db rekey` ran successfully
- [ ] New passphrase stored in secrets manager
- [ ] Old passphrase removed from secrets manager
- [ ] Node restarted and healthy
- [ ] Health check passes

### Federation keypair rotation

- [ ] New keypair generated (manual or `stigmem identity rotate-key`)
- [ ] New key shared with all peer operators
- [ ] Node secrets updated
- [ ] Node restarted
- [ ] New key visible at `/.well-known/stigmem` or `/.well-known/stigmem-manifest.json`
- [ ] All peers updated their pins (or confirmed auto-refresh)
- [ ] Pull replication confirmed healthy on all peers
- [ ] Old public key archived for snapshot verification
- [ ] Dual-trust expiry date recorded in key rotation log
- [ ] Reminder set to delete retiring key after `dual_trust_expires_at`

---

## See also

- [Backup & Restore](./backup-restore) — snapshot signing uses the same Ed25519 keys
- [Per-Agent Keypair Registration](../../build/guides/agent-keypairs) — C1 attestation key lifecycle (separate from node/issuer keys)
- [Audit & Quotas](../security/audit-and-quotas) — `key_rotation` audit events
