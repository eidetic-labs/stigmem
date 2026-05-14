---
title: R-HLC-DRIFT
sidebar_label: R-HLC-DRIFT
description: Incident runbook for federation peers sending Hybrid Logical Clock timestamps outside expected bounds.
audience: Operator
---

# R-HLC-DRIFT

Use this runbook when a peer sends Hybrid Logical Clock timestamps outside your
allowed skew window.

Trigger alerts:

- `peer_hlc_drift_high`
- `peer_hlc_drift_critical`

Default critical threshold: one peer sends a timestamp more than 300 seconds in
the future.

## Identify

Gather recent HLC anomaly events:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  | jq '.[] | select(.event_type == "peer_hlc_anomaly")'
```

Record peer entity URI, observed HLC, local HLC, drift seconds, and whether the
fact was rejected or admitted.

## Contain

1. If drift is critical or repeated, pause pulls from the peer.
2. Do not relax skew limits for normal live federation traffic.
3. If you are running an intentional archival backfill, isolate that backfill
   from normal peer traffic and restore the skew bound afterward.

## Investigate

Determine whether this is honest clock skew or malicious/manipulated input:

- Ask the peer operator for current NTP status and system time.
- Compare drift direction: future skew is higher risk than old backfill data.
- Check whether facts around the anomaly share unusual relations or scopes.
- Look for concurrent replay or capability-violation events.

## Recover

For honest clock skew:

1. Ask the peer operator to fix NTP/system time.
2. Resume pulls after their clock is stable.
3. Manually pull a small batch and confirm no new anomalies.

For suspicious drift:

1. Keep the peer disabled.
2. Retract any admitted facts whose ordering could affect decisions.
3. Treat the peer as compromised until the operator proves control of the node.

## Communicate

Send the peer operator the drift seconds, timestamps, and affected fact IDs. If
your deployment uses HLC order for compliance/audit workflows, notify affected
internal stakeholders before relying on time-ordered reports from the incident
window.
