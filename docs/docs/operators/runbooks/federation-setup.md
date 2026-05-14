---
title: Federation Peer Setup
sidebar_label: Federation Peer Setup
description: Generate keypairs, register peers, pin public keys, and tune source-trust scores for Stigmem federation.
audience: Operator
---

# Federation Peer Setup

**Audience:** operators setting up cross-node federation for the first time; operators adding or removing peers.  
**Spec reference:** `Spec-03-HTTP-API` for route shape, `Spec-05-Federation-Trust` for peer registration and pull replication, and `Spec-04-Manifests` for signed peer declarations.  
**See also:** [Federation guide](../../concepts/federation/), [Federation trust](../../concepts/federation/federation-trust).

---

## Concepts

**Federation** lets Stigmem nodes replicate facts from peers. Each peer must:
1. Expose a `/.well-known/stigmem` discovery endpoint.
2. Present a valid Ed25519 public key in its `PeerDeclaration`.
3. Be registered (pinned) by the receiving node before replication starts.

Source-trust scoring (`Spec-05-Federation-Trust`) lets you weight incoming facts by source. Untrusted sources land in the quarantine garden until you promote them.

---

## Step 1 — Generate your federation keypair

If you didn't generate a keypair during deployment, do it now:

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes_raw()
pub_bytes  = priv.public_key().public_bytes_raw()
print('STIGMEM_FEDERATION_PRIVKEY=' + base64.urlsafe_b64encode(priv_bytes).decode())
print('STIGMEM_FEDERATION_PUBKEY='  + base64.urlsafe_b64encode(pub_bytes).decode())
"
```

Store both values in your secrets manager. **Never commit them to version control.**

Set them on your node before starting:

```bash
# Docker Compose — add to deploy/compose/.env (or the environment: block of your compose file)
STIGMEM_FEDERATION_PUBKEY=...
STIGMEM_FEDERATION_PRIVKEY=...
```

Enable federation:

```bash
STIGMEM_FEDERATION_ENABLED=true
```

---

## Step 2 — Verify your well-known endpoint

Once the node is running, confirm it announces its identity correctly:

```bash
curl -s https://your-node.example.com/.well-known/stigmem | jq .
```

Expected `PeerDeclaration` response (`Spec-05-Federation-Trust`):

```json
{
  "node_id":   "stigmem:node:abc123...",
  "node_url":  "https://your-node.example.com",
  "public_key": "<base64url-ed25519-pubkey>",
  "pull_interval_s": 30,
  "spec_version": "1.1"
}
```

If `public_key` is missing or `node_id` changes across restarts, your keypair is not being persisted — check that `STIGMEM_FEDERATION_PUBKEY` and `STIGMEM_FEDERATION_PRIVKEY` are set.

---

## Step 3 — Register a peer

To receive facts from a peer, register it on your node:

```bash
curl -X POST https://your-node.example.com/v1/federation/peers \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_url": "https://peer-node.example.com",
    "trusted_public_key": "<base64url-ed25519-pubkey-of-peer>"
  }'
```

The `trusted_public_key` is the value from the peer's `/.well-known/stigmem` response. Pinning it means your node will reject any `PeerDeclaration` signed with a different key — this prevents impersonation after a key rotation on the peer side.

Verify the peer was registered:

```bash
curl -s https://your-node.example.com/v1/federation/peers | jq .
```

---

## Step 4 — Confirm replication is running

After registering a peer, the pull loop starts within one `STIGMEM_FEDERATION_PULL_INTERVAL_S` cycle (default: 30 s). Confirm:

```bash
# Check peer status
curl -s https://your-node.example.com/v1/federation/peers/<peer-id> | jq '{last_pull, pull_lag_ms, error}'

# Check audit log for pull events
curl -s "https://your-node.example.com/v1/federation/audit?limit=10" | jq .
```

---

## Step 5 — Pin public keys

Pinning locks a peer to its current keypair. If the peer rotates its key without you updating the pin, pull attempts fail with a signature error — this is intentional.

To update a pinned key after a legitimate peer key rotation:

```bash
# Fetch the peer's new public key
NEW_KEY=$(curl -s https://peer-node.example.com/.well-known/stigmem | jq -r .public_key)

# Update the pin
curl -X PATCH https://your-node.example.com/v1/federation/peers/<peer-id> \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"trusted_public_key\": \"$NEW_KEY\"}"
```

---

## Step 6 — Tune source-trust scores

Each source gets a scalar trust score `t ∈ [0, 1]`. At recall time, effective confidence is weighted by the trust score. Facts from sources below the quarantine threshold land in the quarantine garden.

### View current scores

```bash
curl -s https://your-node.example.com/v1/federation/trust-scores | jq .
```

### Set a score

```bash
curl -X PUT https://your-node.example.com/v1/federation/trust-scores/<source-id> \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"score": 0.8}'
```

### Quarantine threshold

The default quarantine threshold is `0.3`. Facts from sources with `t < 0.3` are routed to the quarantine garden and excluded from standard recall. Set the threshold:

```bash
# In environment variables
STIGMEM_TRUST_QUARANTINE_THRESHOLD=0.3
```

### Promote facts from quarantine

After reviewing quarantined facts:

```bash
# List quarantined facts
curl -s "https://your-node.example.com/v1/facts?garden=quarantine&limit=50" | jq .

# Promote a batch to the default garden
curl -X POST https://your-node.example.com/v1/federation/quarantine/promote \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"fact_ids": ["<id1>", "<id2>"]}'
```

---

## Removing a peer

```bash
curl -X DELETE https://your-node.example.com/v1/federation/peers/<peer-id> \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY"
```

Removing a peer stops the pull loop immediately. Facts already replicated are retained.

---

## Federation env-var reference

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_FEDERATION_ENABLED` | `false` | Enable the pull-replication loop |
| `STIGMEM_FEDERATION_PUBKEY` | `""` | Base64url Ed25519 public key. Persist across restarts |
| `STIGMEM_FEDERATION_PRIVKEY` | `""` | Base64url Ed25519 private key. Persist across restarts |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | Seconds between pull cycles |
| `STIGMEM_FEDERATION_NONCE_WINDOW_S` | `300` | Nonce replay-protection window (`Spec-11-Replay-Protection`) |
| `STIGMEM_FEDERATION_ALLOW_TEAM` | `false` | Allow `team`-scoped facts across federation boundaries |
| `STIGMEM_TRUST_QUARANTINE_THRESHOLD` | `0.3` | Trust score below which facts land in quarantine garden |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pull loop never starts | `STIGMEM_FEDERATION_ENABLED=false` | Set to `true` and restart |
| `signature_mismatch` in audit log | Peer key rotated; pin stale | Update pin (Step 5) |
| Facts arrive in quarantine only | Source trust score too low | Raise score or quarantine threshold |
| `node_id` changes across restarts | Keypair not persisted | Set `STIGMEM_FEDERATION_PUBKEY/PRIVKEY` env vars |
| Peer unreachable errors | Network / firewall | Confirm `STIGMEM_NODE_URL` is reachable from the peer |
