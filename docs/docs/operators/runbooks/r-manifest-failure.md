---
title: R-MANIFEST-FAILURE
sidebar_label: R-MANIFEST-FAILURE
description: Incident runbook for peer manifest verification or key-rotation failures.
audience: Operator
---

# R-MANIFEST-FAILURE

Use this runbook when a peer manifest, pinned key, or manifest rotation cannot
be verified.

Trigger alert:

- `manifest_rotation_failed`

Supporting signals:

- `federation_handshake_failed`
- `signature_mismatch`
- Transparency-log inclusion proof failure
- Peer public key differs from the pinned key without prior notice

## Identify

Fetch the peer declaration and compare it to your stored peer registration:

```bash
curl -s "https://peer-node.example.com/.well-known/stigmem" | jq .

curl -s "https://your-node.example.com/v1/federation/peers/<peer-id>" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the old key, new key, key ID if available, manifest timestamp, and the
verification error.

## Contain

1. Keep the current pin in place.
2. Pause pulls from the peer until the rotation is explained.
3. Do not auto-accept the new key from the failing manifest.
4. Preserve the failing manifest body and audit event.

## Investigate

Contact the peer operator out of band. Ask:

- Did they intentionally rotate the node key?
- What is the expected new public key?
- When did they deploy it?
- Did their signing key or CI/CD pipeline change?
- Are other peers seeing the same manifest?

If the peer cannot confirm the rotation, treat this as
[R-PEER-COMPROMISE](./r-peer-compromise.md).

## Recover

For an expected rotation:

1. Verify the new public key out of band.
2. Update the peer pin.
3. Pull once manually and confirm success.
4. Watch for `federation.pull.ok` and absence of signature errors.

For an unexpected or suspicious rotation:

1. Keep federation disabled for the peer.
2. Ask the peer to rotate from a known-good environment.
3. Re-register only after the peer publishes a verified manifest.

## Communicate

Tell the peer operator exactly which verification failed and include the audit
event timestamp. If multiple peers report the same failure, coordinate a shared
incident channel.
