---
id: security-key-rotation
title: Key Rotation Security Runbook
sidebar_label: Key Rotation
description: Security runbook for rotating Ed25519 node identity and capability issuer keys with dual-trust window management per spec §22.2.
---

# Key Rotation Security Runbook

**Audience:** security engineers and operators managing key lifecycle.  
**Spec reference:** §22.2 Key Rotation, §19.3.2 Max Token TTL.  
**Related:** [Key Rotation Operator Guide](../operating/key-rotation.md) (generation/deployment steps).

---

## Overview

Stigmem nodes use Ed25519 keypairs for two purposes:

| Key type | Purpose | Max rotation cadence (§22.2.4) |
|---|---|---|
| **Node identity key** | Federation peer authentication, snapshot signing, manifest self-signature | ≤ 365 days |
| **Capability issuer key** | Signing capability tokens issued to subjects | ≤ 90 days |

Both key types share the same rotation mechanism (§22.2): a **dual-trust window** keeps the retiring key in the accept-set for at least 90 days — long enough to cover all in-flight tokens signed under the old key (max token TTL is 90 days per §19.3.2).

---

## Security model

### Rotation chain integrity (§19.1.4)

Each rotation is recorded as a `RotationEvent` appended to the org manifest:

```
RotationEvent {
  previous_key_id    # retiring key identifier
  new_key_id         # new key identifier
  new_public_key     # new key bytes (base64url)
  rotated_at         # ISO-8601 UTC timestamp
  signature          # signed by retiring key over canonical body
  previous_public_key  # retiring key bytes (base64url) — §22.2 dual-trust
}
```

The `signature` is an Ed25519 signature by the **retiring** key over the JCS-canonical body of `{new_key_id, new_public_key, previous_key_id, rotated_at}`. This cryptographically anchors the rotation to the prior identity — a peer that trusted key A can verify that key B was legitimately introduced by key A.

`previous_public_key` stores the retiring key's public bytes. Verifiers use it during the dual-trust window without needing an external key registry. The field's authenticity is covered by the manifest's self-signature (signed by the current key over all `rotation_events`).

### Dual-trust window (§22.2.2)

After rotation to key B, tokens previously signed by key A remain valid if:

1. The token's `expiry` is in the future.
2. `now < rotated_at + 90 days` (the dual-trust window is open).
3. The token passes all other checks (C1 subject validation, revocation check).

The verifier (`verify_token`) tries the current key first, then walks `rotation_events` in reverse to find retiring keys still within their windows. This is O(n) in the number of recent rotations but bounded in practice by the 100-event cap per manifest.

### Transparency log entries (§22.2.3)

Each rotation produces **two** transparency-log entries:

1. **Updated manifest** — the full org manifest including the new rotation event and the new self-signature.
2. **`KeyRotationLogEntry`** — a dedicated rotation record:

```json
{
  "event_type": "key_rotation",
  "entity_uri": "https://example.org",
  "old_key_id": "<16-hex>",
  "new_key_id": "<16-hex>",
  "rotated_at": "2026-05-04T12:00:00Z",
  "dual_trust_expires_at": "2026-08-02T12:00:00Z",
  "manifest_log_index": 42,
  "rotation_sig": "<base64url sig by retiring key>"
}
```

`rotation_sig` is signed by the **retiring** key over the JCS-canonical body of all fields except `rotation_sig`. Third parties can independently verify the rotation using only the retiring key's public key — no trust in the submitter required.

---

## Using the CLI

### Basic rotation

```bash
# Rotate the node identity key (dry run first)
stigmem identity rotate-key --kind node --dry-run

# Commit the rotation (writes to TL and DB, prints new private key)
stigmem identity rotate-key --kind node

# Rotate the capability issuer key
stigmem identity rotate-key --kind issuer
```

### Extended dual-trust window

If your deployment issues tokens close to the 90-day maximum TTL, extend the window:

```bash
stigmem identity rotate-key --kind node --dual-trust-days 120
```

The minimum is 90 days (enforced by the CLI and the `rotate_key()` API). Setting it lower raises `ValueError`.

### Custom DB path

```bash
stigmem identity rotate-key --kind node --db /data/stigmem.db
```

---

## Rotation procedure

### Pre-rotation checklist

- [ ] Identify all tokens signed by the current key (`SELECT count(*) FROM capability_tokens WHERE revoked_at IS NULL AND expiry > datetime('now')`)
- [ ] Confirm the dual-trust window (≥ 90 days) covers the maximum expiry of in-flight tokens
- [ ] Ensure the TL backend is reachable (`stigmem identity rotate-key --kind node --dry-run` should show no TL error)
- [ ] Notify peer operators that a manifest update is imminent

### Step 1 — Dry-run

```bash
stigmem identity rotate-key --kind node --dry-run
# Output shows new key_id and dual-trust expiry without committing anything
```

### Step 2 — Commit rotation

```bash
stigmem identity rotate-key --kind node
# Output:
#   Key rotation (node) complete
#   old key_id : a1b2c3d4e5f60001
#   new key_id : 9f8e7d6c5b4a0002
#   dual-trust : 2026-08-02T12:00:00Z
#   manifest TL index  : 43
#   rotation TL index  : 44
#   manifest stored in federation_manifests
#
#   ACTION REQUIRED — update your secrets manager with the new private key:
#     STIGMEM_NODE_PRIVATE_KEY=<base64url seed>
```

### Step 3 — Update secrets manager

```bash
# Fly.io
fly secrets set STIGMEM_NODE_PRIVATE_KEY=<new-seed>

# AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id stigmem/node-private-key \
  --secret-string '<new-seed>'

# systemd EnvironmentFile
sed -i 's|^STIGMEM_NODE_PRIVATE_KEY=.*|STIGMEM_NODE_PRIVATE_KEY=<new-seed>|' /etc/stigmem/env
```

### Step 4 — Restart the node

```bash
systemctl restart stigmem
# or
fly machine restart
# or
docker compose up -d node
```

### Step 5 — Verify new manifest is live

```bash
curl -s https://your-node.example.com/.well-known/stigmem-manifest.json | jq .key_id
# → "<new key_id>"
```

### Step 6 — Notify peers

Peer nodes refresh manifests automatically during their periodic `refresh_peer_manifests()` sweep. For time-sensitive rotations, ask peer operators to force a refresh or re-pin:

```bash
curl -s https://peer.example.com/.well-known/stigmem-manifest.json | jq .key_id
```

### Step 7 — Archive retiring key

Keep the retiring private key seed in a read-only secrets location until `dual_trust_expires_at`. After that date, it can be deleted. Do not destroy it earlier — snapshot verification tools may need it.

---

## Post-rotation checklist

- [ ] New key visible at `/.well-known/stigmem-manifest.json`
- [ ] Node private key updated in secrets manager
- [ ] Node restarted and healthy (`/healthz`)
- [ ] Old tokens (if any) verified successfully via `stigmem capability verify`
- [ ] Peers refreshed their manifest cache (check peer audit logs for `key_rotation` events)
- [ ] Dual-trust expiry date recorded in your key rotation log
- [ ] Retiring private key archived until `dual_trust_expires_at`
- [ ] Reminder set to delete retiring key after `dual_trust_expires_at`

---

## Threat model notes

| Threat | Mitigation |
|---|---|
| Stolen retiring key during window | Revoke all tokens issued under that key immediately via `capability revoke`; rotate again; retire window can be closed early by revoking tokens |
| Forged rotation event | Rotation event signature must verify under the retiring key; forgery requires compromise of the prior key |
| Key reuse / regression attack | `verify_rotation_chain` rejects any `new_key_id` already seen in the chain |
| TL unavailable during rotation | In `trust_mode=strict`, TL failure surfaces as a hard error; use `--dry-run` to pre-check reachability |
| Dual-trust window too short | CLI enforces minimum 90 days; spec §22.2.2 prohibits shorter windows without explicit token revocation |

---

## API reference

### `rotate_key()` (Python)

```python
from stigmem_node.identity import rotate_key

result = rotate_key(
    entity_uri="https://example.org",
    old_manifest=old_manifest,           # OrgManifest, already verified
    old_private_key=old_private_key,     # Ed25519PrivateKey
    dual_trust_days=90,                  # int, must be ≥ 90
    manifest_validity_days=365,          # int
    dry_run=False,                       # bool
)
# result.new_private_key_b64  — store in secrets manager
# result.new_manifest         — OrgManifest with updated key and rotation event
# result.manifest_log_entry   — LogEntry from TL (None if dry_run)
# result.rotation_log_entry   — KeyRotationLogEntry
# result.rotation_tl_entry    — LogEntry for KeyRotationLogEntry (None if dry_run)
```

### `KeyRotationLogEntry` fields

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | Always `"key_rotation"` |
| `entity_uri` | `str` | Rotating org's canonical URI |
| `old_key_id` | `str` | 16-hex retiring key identifier |
| `new_key_id` | `str` | 16-hex new key identifier |
| `rotated_at` | `str` | ISO-8601 UTC rotation timestamp |
| `dual_trust_expires_at` | `str` | ISO-8601 UTC; retiring key accepted until here |
| `manifest_log_index` | `int` | TL index of updated manifest; `-1` on dry-run |
| `rotation_sig` | `str` | base64url Ed25519 sig by retiring key |
