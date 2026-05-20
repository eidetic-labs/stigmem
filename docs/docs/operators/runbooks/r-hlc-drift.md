---
title: R-HLC-DRIFT
sidebar_label: R-HLC-DRIFT
description: Incident runbook for federation peers sending Hybrid Logical Clock timestamps outside expected bounds.
audience: Operator
---

# R-HLC-DRIFT

<p className="stigmem-meta"><span>2 min read</span><span>On-call operator</span><span>Runbook</span></p>

<div className="stigmem-lead">

**When to use**

A peer sends Hybrid Logical Clock timestamps outside your allowed
skew window. Trigger alerts: `peer_hlc_drift_high`,
`peer_hlc_drift_critical`. Default critical threshold: one peer
sends a timestamp more than 300 seconds in the future.

</div>

## Identify

Gather recent HLC anomaly events:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  | jq '.[] | select(.event_type == "peer_hlc_anomaly")'
```

Record peer entity URI, observed HLC, local HLC, drift seconds, and whether the fact was rejected or admitted.

## Contain

<ol className="stigmem-steps">
<li>If drift is critical or repeated, pause pulls from the peer.</li>
<li>Do not relax skew limits for normal live federation traffic.</li>
<li>If you are running an intentional archival backfill, isolate that backfill from normal peer traffic and restore the skew bound afterward.</li>
</ol>

## Investigate

Determine whether this is honest clock skew or malicious/manipulated input:

<div className="stigmem-grid">

<div><h4>NTP status</h4><p>Ask the peer operator for current NTP status and system time.</p></div>
<div><h4>Drift direction</h4><p>Future skew is higher risk than old backfill data.</p></div>
<div><h4>Relation patterns</h4><p>Check whether facts around the anomaly share unusual relations or scopes.</p></div>
<div><h4>Concurrent violations</h4><p>Look for concurrent replay or capability-violation events.</p></div>

</div>

## Recover

**For honest clock skew:**

<ol className="stigmem-steps">
<li>Ask the peer operator to fix NTP/system time.</li>
<li>Resume pulls after their clock is stable.</li>
<li>Manually pull a small batch and confirm no new anomalies.</li>
</ol>

**For suspicious drift:**

<ol className="stigmem-steps">
<li>Keep the peer disabled.</li>
<li>Retract any admitted facts whose ordering could affect decisions.</li>
<li>Treat the peer as compromised until the operator proves control of the node.</li>
</ol>

## Communicate

<div className="stigmem-keypoint">

**Send the peer operator the drift seconds, timestamps, and affected fact IDs.**

If your deployment uses HLC order for compliance/audit workflows,
notify affected internal stakeholders before relying on time-ordered
reports from the incident window.

</div>
