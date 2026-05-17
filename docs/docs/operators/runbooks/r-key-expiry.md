---
title: R-KEY-EXPIRY
sidebar_label: R-KEY-EXPIRY
description: Incident runbook for production operations blocked by expired API, issuer, or federation keys.
audience: Operator
---

# R-KEY-EXPIRY

Use this runbook when production traffic is blocked because a key expired before
rotation completed.

Trigger alerts:

- `key_expired_blocked`
- Repeated authentication failures for a known production caller

Supporting signals:

- `/v1/auth/keys/expiring-soon` showed the key inside the operator's alert
  window and was not acted on.
- Federation pulls fail after a peer key or manifest expiry.

## Identify

Find which key class is affected:

- API key: callers receive authentication failures.
- Capability issuer key: federation/capability tokens cannot be issued or
  verified.
- Node federation key: peers reject your manifest or pull responses.
- Encryption passphrase: node cannot open the database after a secrets change.

Capture recent auth and admin audit events:

```bash
curl -s "https://your-node.example.com/v1/audit/events?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

## Contain

1. Do not extend an expired key by editing the database by hand.
2. Keep the failed key material for audit, but stop issuing new tokens with it.
3. If admin access is still available, create a replacement key immediately.
4. If admin access is unavailable, use your documented break-glass procedure.

## Investigate

Determine why the rotation was missed:

- Was a `key_expiring_soon` alert configured?
- Was the alert backed by `/v1/auth/keys/expiring-soon` or an equivalent
  database/SIEM query?
- Did the alert route to the right owner?
- Did the key lack an owner or rotation date?
- Was the rotation procedure blocked by peer coordination?

## Recover

For API keys:

1. Create a new key with the least required permissions.
2. Redeploy the caller with the new secret.
3. Revoke the expired key if it remains in storage.

For federation or issuer keys:

1. Follow [Key Rotation](../../security/key-rotation.md).
2. Notify peer operators of the new public key or manifest.
3. Ask peers to re-pin if automatic refresh is unavailable.
4. Confirm federation pulls resume.

For encryption passphrases:

1. Restore the last known-good secret from your secrets manager.
2. Bring the node healthy.
3. Schedule a controlled rekey rather than improvising during outage.

## Communicate

Tell affected callers or peers which key expired, when replacement credentials
will be available, and whether any data integrity risk exists. After recovery,
add or fix the rotation reminder that should have prevented the outage.
