---
title: R-MANIFEST-FAILURE
sidebar_label: R-MANIFEST-FAILURE
description: Incident runbook for peer manifest verification or key-rotation failures.
audience: Operator
---

# R-MANIFEST-FAILURE

<p className="stigmem-meta"><span>3 min read</span><span>On-call operator</span><span>Runbook</span></p>

<div className="stigmem-lead">

**When to use**

A peer manifest, pinned key, or manifest rotation cannot be
verified. Trigger alert: `manifest_rotation_failed`. Supporting
signals: `federation_handshake_failed`, `signature_mismatch`,
transparency-log inclusion proof failure, peer public key differs
from the pinned key without prior notice.

</div>

## Identify

Fetch the peer declaration and compare it to your stored peer registration:

```bash
curl -s "https://peer-node.example.com/.well-known/stigmem" | jq .

curl -s "https://your-node.example.com/v1/federation/peers/<peer-id>" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the old key, new key, key ID if available, manifest timestamp, and the verification error.

## Contain

<ol className="stigmem-steps">
<li>Keep the current pin in place.</li>
<li>Pause pulls from the peer until the rotation is explained.</li>
<li>Do not auto-accept the new key from the failing manifest.</li>
<li>Preserve the failing manifest body and audit event.</li>
</ol>

## Investigate

Contact the peer operator out of band. Ask:

<div className="stigmem-grid">

<div><h4>Intentional rotation?</h4><p>Did they intentionally rotate the node key?</p></div>
<div><h4>Expected new key?</h4><p>What is the expected new public key?</p></div>
<div><h4>Deployment time?</h4><p>When did they deploy it?</p></div>
<div><h4>Signing key / CI/CD?</h4><p>Did their signing key or CI/CD pipeline change?</p></div>
<div><h4>Other peers?</h4><p>Are other peers seeing the same manifest?</p></div>

</div>

<div className="stigmem-keypoint">

**If the peer cannot confirm the rotation, treat this as [R-PEER-COMPROMISE](./r-peer-compromise.md).**

</div>

## Recover

**For an expected rotation:**

<ol className="stigmem-steps">
<li>Verify the new public key out of band.</li>
<li>Update the peer pin.</li>
<li>Pull once manually and confirm success.</li>
<li>Watch for <code>federation.pull.ok</code> and absence of signature errors.</li>
</ol>

**For an unexpected or suspicious rotation:**

<ol className="stigmem-steps">
<li>Keep federation disabled for the peer.</li>
<li>Ask the peer to rotate from a known-good environment.</li>
<li>Re-register only after the peer publishes a verified manifest.</li>
</ol>

## Communicate

Tell the peer operator exactly which verification failed and include the audit event timestamp. If multiple peers report the same failure, coordinate a shared incident channel.
