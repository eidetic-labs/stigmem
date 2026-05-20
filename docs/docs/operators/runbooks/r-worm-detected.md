---
title: R-WORM-DETECTED
sidebar_label: R-WORM-DETECTED
description: Incident runbook for suspected automated cross-peer or agent-to-agent propagation.
audience: Operator
---

# R-WORM-DETECTED

<p className="stigmem-meta"><span>3 min read</span><span>On-call operator</span><span>Runbook · critical</span></p>

<div className="stigmem-lead">

**When to use**

Writes appear to propagate automatically through agents or peers in
a pattern that resembles a worm. Trigger alert:
`worm_pattern_detected`.

</div>

**Supporting signals:**

<div className="stigmem-grid">

<div><h4>Mirror graphs</h4><p>Agent-read and agent-write graphs mirror each other beyond baseline.</p></div>
<div><h4>Unusual instruction-like facts</h4><p>Sudden instruction-like facts from peers that do not normally write them.</p></div>
<div><h4>Rapid cross-peer growth</h4><p>Rapid growth in facts across multiple peer sources.</p></div>
<div><h4>Repeated quarantine</h4><p>Repeated quarantine admissions for similar payloads.</p></div>

</div>

## Identify

Preserve the graph shape and affected payloads:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=500" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .

curl -s "https://your-node.example.com/v1/facts?limit=500" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the first suspicious fact, the relation names involved, the peers that sent or received related facts, and whether any agent-control or instruction relations are present.

## Contain

<div className="stigmem-keypoint">

**Containment is intentionally broad.**

Restore access only after the propagation path is understood.

</div>

<ol className="stigmem-steps">
<li>Disable federation pulls from affected peers.</li>
<li>Stop or isolate agents that read from the affected scopes.</li>
<li>Disable automated quarantine promotion.</li>
<li>Tighten read/write quotas for affected principals.</li>
<li>If a connector or adapter is involved, disable that connector until payloads are reviewed.</li>
</ol>

## Investigate

Trace the propagation path:

<div className="stigmem-grid">

<div><h4>Read-before-write chain</h4><p>Which fact was read before each suspicious write?</p></div>
<div><h4>Next writer</h4><p>Which agent or peer wrote the next copy?</p></div>
<div><h4>Mutation</h4><p>Did the payload change as it moved?</p></div>
<div><h4>Self-propagation directive</h4><p>Did any fact ask an agent to fetch, write, or forward additional facts?</p></div>
<div><h4>Cross-org spread</h4><p>Did the pattern cross organization boundaries?</p></div>

</div>

Compare findings against [Security Scenarios](../../security/scenarios.md), especially prompt-injection and federation scenarios.

## Recover

<ol className="stigmem-steps">
<li>Retract or quarantine malicious payloads.</li>
<li>Rotate any API keys used by affected agents.</li>
<li>Re-enable agents one at a time with lower quotas.</li>
<li>Re-enable federation one peer at a time.</li>
<li>Add a regression test or detection rule for the payload pattern if it is new.</li>
</ol>

## Communicate

Notify affected peer operators with the payload shape, timestamps, and containment actions. If the incident crossed org boundaries, publish a short public note after containment that states impact, affected versions, and operator actions.
