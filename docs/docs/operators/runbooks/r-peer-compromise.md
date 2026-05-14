---
title: R-PEER-COMPROMISE
sidebar_label: R-PEER-COMPROMISE
description: Incident runbook for suspected compromised or malicious federation peers.
audience: Operator
---

# R-PEER-COMPROMISE

Use this runbook when a federation peer appears compromised, malicious, or
misconfigured in a way that could affect your node.

Trigger alerts:

- `peer_capability_violation`
- `peer_replay_burst`
- Repeated `federation_handshake_failed`
- Suspicious `manifest_rotation_observed`
- Unexpected high-volume writes or quarantine admissions from one peer

## Identify

Capture the current evidence before changing state:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .

curl -s "https://your-node.example.com/v1/federation/peers" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the peer entity URI, peer URL, pinned key, recent pull status, and the
first timestamp where behavior changed.

## Contain

Stop new data from the peer first.

1. Disable or remove the peer registration.
2. Revoke capability tokens issued to that peer.
3. If your deployment supports source-trust rules, lower the peer's trust score
   so future facts are quarantined.
4. Pause any automated promotion from quarantine.

Do not delete audit events. They are the evidence trail.

## Investigate

Review what the peer wrote and what escaped quarantine:

```bash
curl -s "https://your-node.example.com/v1/facts?source=<peer-entity-uri>&limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Check for:

- Facts in sensitive scopes.
- `interpret_as=instruction` or agent-control relations.
- Facts promoted from quarantine.
- Replays or capability violations close to the first suspicious write.

## Recover

1. Retract facts that are false, unsafe, or outside the agreed federation
   contract.
2. Keep benign facts if you can justify them from audit evidence.
3. Ask the peer operator to rotate compromised node or issuer keys.
4. Re-register the peer only after you verify its new manifest/key material out
   of band.
5. Run a small test pull and watch quarantine/audit events before restoring full
   trust.

## Communicate

Notify the peer operator with:

- Peer entity URI and URL.
- Alert names and timestamps.
- Example fact IDs or audit event IDs.
- What you disabled locally.
- What evidence you need before re-enabling.

If compromised data may have reached downstream peers, notify those operators
too.
