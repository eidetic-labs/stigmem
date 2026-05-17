---
title: R-REKOR-UNAVAILABLE
sidebar_label: R-REKOR-UNAVAILABLE
description: Incident runbook for delayed fact-chain transparency-log checkpoints.
audience: Operator
---

# R-REKOR-UNAVAILABLE

Use this runbook when fact writes continue locally but chain checkpoints cannot
be submitted to the configured transparency log.

Trigger signals:

- `fact_chain_checkpoints.status = 'pending'` for longer than your alert window.
- `fact_chain_checkpoints.last_error` mentions Rekor, transparency-log, network,
  or signing-package availability.
- Full recall proofs show a pending checkpoint while recent writes continue.

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

1. Keep fact writes enabled unless your deployment policy requires fail-closed
   external witnessing. Facts remain locally chained while checkpoints retry.
2. Preserve the pending checkpoint rows and application logs.
3. Avoid rebuilding or truncating `fact_chain` while checkpoint submission is
   pending.
4. If the outage is caused by a bad Rekor URL or missing Sigstore dependency,
   correct configuration before restarting the node.

## Investigate

Determine whether the failure is local or external:

- For local configuration failures, verify the configured backend, Rekor URL,
  package extras, and outbound egress policy.
- For public Rekor outages, check the Sigstore status page and retry later.
- For private Rekor deployments, contact the log operator and preserve the last
  successful `tl_log_index`.

## Recover

After the transparency log is reachable again, allow the node to retry pending
checkpoints. A healthy checkpoint has:

- `status = 'submitted'`
- non-null `submitted_at`
- non-null `tl_log_id`
- non-null `tl_leaf_hash`
- non-null `tl_log_index`

Run a full recall verification request and confirm the returned `chain_proof`
includes the latest submitted checkpoint metadata.

## Communicate

Tell peer operators and auditors the affected tenant, the highest locally
covered chain sequence, the first pending checkpoint timestamp, and whether the
gap was local configuration, network reachability, or Rekor service
availability.
