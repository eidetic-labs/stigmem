---
id: key-rotation
title: Key Rotation
sidebar_label: Key Rotation
description: Runbooks for rotating Stigmem encryption passphrases and federation keypairs with minimal disruption.
---

# Key Rotation

**Audience:** operators managing key lifecycle in production.  
**Spec reference:** encryption key derivation in storage hardening; federation keys §5.3, §6.

There are two distinct key types to rotate:

| Key type | Purpose | Rotation impact |
|---|---|---|
| **Encryption passphrase** | At-rest encryption of the database file | Node must stop; no peer impact |
| **Federation keypair** (Ed25519) | Node identity, peer token signing, snapshot signing | All pinned peers must re-pin new key |

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

## Rotation checklist

### Encryption passphrase rotation

- [ ] Node stopped
- [ ] `stigmem db rekey` ran successfully
- [ ] New passphrase stored in secrets manager
- [ ] Old passphrase removed from secrets manager
- [ ] Node restarted and healthy
- [ ] Health check passes

### Federation keypair rotation

- [ ] New keypair generated
- [ ] New key shared with all peer operators
- [ ] Node secrets updated
- [ ] Node restarted
- [ ] New key visible at `/.well-known/stigmem`
- [ ] All peers updated their pins
- [ ] Pull replication confirmed healthy on all peers
- [ ] Old public key archived for snapshot verification
