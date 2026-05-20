---
title: Federation Peer Setup
sidebar_label: Federation Peer Setup
description: Generate keypairs, register peers, pin public keys, and tune source-trust scores for Stigmem federation.
audience: Operator
---

# Federation Peer Setup

<p className="stigmem-meta"><span>5 min read</span><span>Node operator</span><span>v0.9.0aN</span></p>

<div className="stigmem-lead">

**What this runbook covers**

Generate keypairs, register peers, pin public keys, and tune
source-trust scores for Stigmem federation.

</div>

**Audience:** operators setting up cross-node federation for the first time; operators adding or removing peers.
**Spec reference:** `Spec-03-HTTP-API` for route shape, `Spec-05-Federation-Trust` for peer registration and pull replication, and `Spec-04-Manifests` for signed peer declarations.
**See also:** [Federation guide](../../concepts/federation/), [Federation trust](../../concepts/federation/federation-trust).

## Concepts

Federation lets Stigmem nodes replicate facts from peers. Each peer must:

<ol className="stigmem-steps">
<li>Expose a <code>/.well-known/stigmem</code> discovery endpoint.</li>
<li>Present a valid Ed25519 public key in its <code>PeerDeclaration</code>.</li>
<li>Be registered (pinned) by the receiving node before replication starts.</li>
</ol>

Source-trust scoring (`Spec-05-Federation-Trust`) lets you weight incoming facts by source. Untrusted sources land in the quarantine garden until you promote them.

## Step 1 — Generate your federation keypair

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

<div className="stigmem-keypoint">

**Store both values in your secrets manager. Never commit them to version control.**

</div>

Set them on your node before starting:

```bash
# Docker Compose — add to deploy/compose/.env
STIGMEM_FEDERATION_PUBKEY=...
STIGMEM_FEDERATION_PRIVKEY=...
STIGMEM_FEDERATION_ENABLED=true
```

## Step 2 — Verify your well-known endpoint

```bash
curl -s https://your-node.example.com/.well-known/stigmem | jq .
```

Expected `PeerDeclaration` response:

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

## Step 3 — Register a peer

```bash
curl -X POST https://your-node.example.com/v1/federation/peers \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_url": "https://peer-node.example.com",
    "trusted_public_key": "<base64url-ed25519-pubkey-of-peer>"
  }'
```

<div className="stigmem-keypoint">

**Pinning the `trusted_public_key` means your node will reject any `PeerDeclaration` signed with a different key.**

This prevents impersonation after a key rotation on the peer side.

</div>

Verify the peer was registered:

```bash
curl -s https://your-node.example.com/v1/federation/peers | jq .
```

## Step 4 — Confirm replication is running

```bash
# Check peer status
curl -s https://your-node.example.com/v1/federation/peers/<peer-id> | jq '{last_pull, pull_lag_ms, error}'

# Check audit log for pull events
curl -s "https://your-node.example.com/v1/federation/audit?limit=10" | jq .
```

## Step 5 — Pin public keys

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

The default quarantine threshold is `0.3`. Facts from sources with `t < 0.3` are routed to the quarantine garden and excluded from standard recall.

```bash
STIGMEM_TRUST_QUARANTINE_THRESHOLD=0.3
```

### Promote facts from quarantine

```bash
# List quarantined facts
curl -s "https://your-node.example.com/v1/facts?garden=quarantine&limit=50" | jq .

# Promote a batch to the default garden
curl -X POST https://your-node.example.com/v1/federation/quarantine/promote \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"fact_ids": ["<id1>", "<id2>"]}'
```

## Removing a peer

```bash
curl -X DELETE https://your-node.example.com/v1/federation/peers/<peer-id> \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY"
```

Removing a peer stops the pull loop immediately. Facts already replicated are retained.

## Federation env-var reference

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Enable the pull-replication loop.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PUBKEY</code></dt>
<dt><span className="stigmem-fields__type">""</span></dt>
<dd>Base64url Ed25519 public key. Persist across restarts.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PRIVKEY</code></dt>
<dt><span className="stigmem-fields__type">""</span></dt>
<dd>Base64url Ed25519 private key. Persist across restarts.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code></dt>
<dt><span className="stigmem-fields__type">30</span></dt>
<dd>Seconds between pull cycles.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_NONCE_WINDOW_S</code></dt>
<dt><span className="stigmem-fields__type">300</span></dt>
<dd>Nonce replay-protection window (<code>Spec-11-Replay-Protection</code>).</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ALLOW_TEAM</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Allow <code>team</code>-scoped facts across federation boundaries.</dd>
</div>

<div>
<dt><code>STIGMEM_TRUST_QUARANTINE_THRESHOLD</code></dt>
<dt><span className="stigmem-fields__type">0.3</span></dt>
<dd>Trust score below which facts land in quarantine garden.</dd>
</div>

</div>

## Troubleshooting

<div className="stigmem-fields">

<div>
<dt>Symptom</dt>
<dt><span className="stigmem-fields__type">Likely cause</span></dt>
<dd>Fix</dd>
</div>

<div>
<dt>Pull loop never starts</dt>
<dt><span className="stigmem-fields__type">disabled</span></dt>
<dd><code>STIGMEM_FEDERATION_ENABLED=false</code>. Set to <code>true</code> and restart.</dd>
</div>

<div>
<dt><code>signature_mismatch</code> in audit log</dt>
<dt><span className="stigmem-fields__type">stale pin</span></dt>
<dd>Peer key rotated; update pin (Step 5).</dd>
</div>

<div>
<dt>Facts arrive in quarantine only</dt>
<dt><span className="stigmem-fields__type">low trust</span></dt>
<dd>Source trust score too low. Raise score or quarantine threshold.</dd>
</div>

<div>
<dt><code>node_id</code> changes across restarts</dt>
<dt><span className="stigmem-fields__type">no persistence</span></dt>
<dd>Keypair not persisted. Set <code>STIGMEM_FEDERATION_PUBKEY/PRIVKEY</code> env vars.</dd>
</div>

<div>
<dt>Peer unreachable errors</dt>
<dt><span className="stigmem-fields__type">network</span></dt>
<dd>Confirm <code>STIGMEM_NODE_URL</code> is reachable from the peer.</dd>
</div>

</div>
