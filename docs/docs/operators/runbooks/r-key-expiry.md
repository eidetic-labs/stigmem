---
title: R-KEY-EXPIRY
sidebar_label: R-KEY-EXPIRY
description: Incident runbook for production operations blocked by expired API, issuer, or federation keys.
audience: Operator
---

# R-KEY-EXPIRY

<p className="stigmem-meta"><span>3 min read</span><span>On-call operator</span><span>Runbook</span></p>

<div className="stigmem-lead">

**When to use**

Production traffic is blocked because a key expired before rotation
completed. Trigger alerts: `key_expired_blocked`, repeated
authentication failures for a known production caller. Supporting
signal: `/v1/auth/keys/expiring-soon` showed the key inside the
operator's alert window and was not acted on.

</div>

## Identify

Find which key class is affected:

<div className="stigmem-fields">

<div>
<dt>Class</dt>
<dt><span className="stigmem-fields__type">Symptom</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>API key</dt>
<dt><span className="stigmem-fields__type">auth failures</span></dt>
<dd>Callers receive authentication failures.</dd>
</div>

<div>
<dt>Capability issuer key</dt>
<dt><span className="stigmem-fields__type">issuance/verification fail</span></dt>
<dd>Federation/capability tokens cannot be issued or verified.</dd>
</div>

<div>
<dt>Node federation key</dt>
<dt><span className="stigmem-fields__type">manifest rejected</span></dt>
<dd>Peers reject your manifest or pull responses.</dd>
</div>

<div>
<dt>Encryption passphrase</dt>
<dt><span className="stigmem-fields__type">db won't open</span></dt>
<dd>Node cannot open the database after a secrets change.</dd>
</div>

</div>

Capture recent auth and admin audit events:

```bash
curl -s "https://your-node.example.com/v1/audit/events?limit=200" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

## Contain

<ol className="stigmem-steps">
<li>Do not extend an expired key by editing the database by hand.</li>
<li>Keep the failed key material for audit, but stop issuing new tokens with it.</li>
<li>If admin access is still available, create a replacement key immediately.</li>
<li>If admin access is unavailable, use your documented break-glass procedure.</li>
</ol>

## Investigate

Determine why the rotation was missed:

<div className="stigmem-grid">

<div><h4>Alert configured?</h4><p>Was a <code>key_expiring_soon</code> alert configured?</p></div>
<div><h4>Backed by query?</h4><p>Was the alert backed by <code>/v1/auth/keys/expiring-soon</code> or an equivalent database/SIEM query?</p></div>
<div><h4>Right owner?</h4><p>Did the alert route to the right owner?</p></div>
<div><h4>Missing owner</h4><p>Did the key lack an owner or rotation date?</p></div>
<div><h4>Peer coordination</h4><p>Was the rotation procedure blocked by peer coordination?</p></div>

</div>

## Recover

**For API keys:**

<ol className="stigmem-steps">
<li>Create a new key with the least required permissions.</li>
<li>Redeploy the caller with the new secret.</li>
<li>Revoke the expired key if it remains in storage.</li>
</ol>

**For federation or issuer keys:**

<ol className="stigmem-steps">
<li>Follow <a href="../../security/key-rotation.md">Key Rotation</a>.</li>
<li>Notify peer operators of the new public key or manifest.</li>
<li>Ask peers to re-pin if automatic refresh is unavailable.</li>
<li>Confirm federation pulls resume.</li>
</ol>

**For encryption passphrases:**

<ol className="stigmem-steps">
<li>Restore the last known-good secret from your secrets manager.</li>
<li>Bring the node healthy.</li>
<li>Schedule a controlled rekey rather than improvising during outage.</li>
</ol>

## Communicate

<div className="stigmem-keypoint">

**After recovery, add or fix the rotation reminder that should have prevented the outage.**

Tell affected callers or peers which key expired, when replacement
credentials will be available, and whether any data integrity risk
exists.

</div>
