---
title: R-PEER-COMPROMISE
sidebar_label: R-PEER-COMPROMISE
description: Incident runbook for suspected compromised or malicious federation peers.
audience: Operator
---

# R-PEER-COMPROMISE

<p className="stigmem-meta"><span>3 min read</span><span>On-call operator</span><span>Runbook · critical</span></p>

<div className="stigmem-lead">

**When to use**

A federation peer appears compromised, malicious, or misconfigured in
a way that could affect your node.

</div>

**Trigger alerts:**

<div className="stigmem-grid">

<div><h4><code>peer_capability_violation</code></h4></div>
<div><h4><code>peer_replay_burst</code></h4></div>
<div><h4>Repeated <code>federation_handshake_failed</code></h4></div>
<div><h4>Suspicious <code>manifest_rotation_observed</code></h4></div>
<div><h4>High-volume writes</h4><p>Unexpected high-volume writes or quarantine admissions from one peer.</p></div>

</div>

## Identify

Capture the current evidence before changing state:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .

curl -s "https://your-node.example.com/v1/federation/peers" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the peer entity URI, peer URL, pinned key, recent pull status, and the first timestamp where behavior changed.

## Contain

<div className="stigmem-keypoint">

**Stop new data from the peer first. Do not delete audit events — they are the evidence trail.**

</div>

<ol className="stigmem-steps">
<li>Disable or remove the peer registration.</li>
<li>Revoke capability tokens issued to that peer.</li>
<li>If your deployment supports source-trust rules, lower the peer's trust score so future facts are quarantined.</li>
<li>Pause any automated promotion from quarantine.</li>
</ol>

## Investigate

Review what the peer wrote and what escaped quarantine:

```bash
curl -s "https://your-node.example.com/v1/facts?source=<peer-entity-uri>&limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Check for:

<div className="stigmem-grid">

<div><h4>Sensitive scopes</h4><p>Facts in sensitive scopes.</p></div>
<div><h4>Agent-control relations</h4><p><code>interpret_as=instruction</code> or agent-control relations.</p></div>
<div><h4>Promoted from quarantine</h4></div>
<div><h4>Replays / capability violations</h4><p>Close to the first suspicious write.</p></div>

</div>

## Recover

<ol className="stigmem-steps">
<li>Retract facts that are false, unsafe, or outside the agreed federation contract.</li>
<li>Keep benign facts if you can justify them from audit evidence.</li>
<li>Ask the peer operator to rotate compromised node or issuer keys.</li>
<li>Re-register the peer only after you verify its new manifest/key material out of band.</li>
<li>Run a small test pull and watch quarantine/audit events before restoring full trust.</li>
</ol>

## Communicate

Notify the peer operator with:

<div className="stigmem-grid">

<div><h4>Peer entity URI and URL</h4></div>
<div><h4>Alert names and timestamps</h4></div>
<div><h4>Example fact IDs or audit event IDs</h4></div>
<div><h4>What you disabled locally</h4></div>
<div><h4>Evidence needed before re-enabling</h4></div>

</div>

<div className="stigmem-keypoint">

**If compromised data may have reached downstream peers, notify those operators too.**

</div>
