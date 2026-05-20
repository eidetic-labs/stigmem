---
title: R-REKOR-UNAVAILABLE
sidebar_label: R-REKOR-UNAVAILABLE
description: Incident runbook for delayed fact-chain transparency-log checkpoints.
audience: Operator
---

# R-REKOR-UNAVAILABLE

<p className="stigmem-meta"><span>3 min read</span><span>On-call operator</span><span>Runbook</span></p>

<div className="stigmem-lead">

**When to use**

Fact writes continue locally but chain checkpoints cannot be
submitted to the configured transparency log.

</div>

**Trigger signals:**

<div className="stigmem-grid">

<div><h4>Pending checkpoint</h4><p><code>fact_chain_checkpoints.status = 'pending'</code> for longer than your alert window.</p></div>
<div><h4>Rekor in last_error</h4><p><code>fact_chain_checkpoints.last_error</code> mentions Rekor, transparency-log, network, or signing-package availability.</p></div>
<div><h4>Stale chain proofs</h4><p>Full recall proofs show a pending checkpoint while recent writes continue.</p></div>

</div>

## Identify

Check the latest checkpoint state:

```sql
SELECT tenant_id,
       covered_chain_seq,
       status,
       attempt_count,
       created_at,
       submitted_at,
       next_retry_at,
       last_error
FROM fact_chain_checkpoints
ORDER BY covered_chain_seq DESC
LIMIT 10;
```

Confirm the node's transparency-log configuration:

```bash
echo "$STIGMEM_TL_BACKEND"
echo "$STIGMEM_TL_REKOR_URL"
```

## Contain

<ol className="stigmem-steps">
<li>Keep fact writes enabled unless your deployment policy requires fail-closed external witnessing. Facts remain locally chained while checkpoints retry.</li>
<li>Preserve the pending checkpoint rows and application logs.</li>
<li>Avoid rebuilding or truncating <code>fact_chain</code> while checkpoint submission is pending.</li>
<li>If the outage is caused by a bad Rekor URL or missing Sigstore dependency, correct configuration before restarting the node.</li>
</ol>

## Investigate

<div className="stigmem-grid">

<div><h4>Local config failure</h4><p>Verify backend, Rekor URL, package extras, and outbound egress policy.</p></div>
<div><h4>Public Rekor outage</h4><p>Check the Sigstore status page and retry later.</p></div>
<div><h4>Private Rekor</h4><p>Contact the log operator and preserve the last successful <code>tl_log_index</code>.</p></div>

</div>

## Recover

After the transparency log is reachable again, allow the node to retry pending checkpoints.

<div className="stigmem-keypoint">

**A healthy checkpoint has all of:**

`status = 'submitted'`, non-null `submitted_at`, non-null `tl_log_id`,
non-null `tl_leaf_hash`, non-null `tl_log_index`.

</div>

Run a full recall verification request and confirm the returned `chain_proof` includes the latest submitted checkpoint metadata.

## Communicate

Tell peer operators and auditors:

<div className="stigmem-grid">

<div><h4>Affected tenant</h4></div>
<div><h4>Highest locally covered chain sequence</h4></div>
<div><h4>First pending checkpoint timestamp</h4></div>
<div><h4>Root cause class</h4><p>Local configuration, network reachability, or Rekor service availability.</p></div>

</div>
