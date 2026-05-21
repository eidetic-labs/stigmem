# Async Jobs Security

## Security Posture

Async jobs do not grant a new authorization surface by themselves. The caller
must already be authorized for the operation that creates the job. The job
polling endpoint must keep operation-type isolation so a job id from one surface
does not expose another surface's results.

## Threat Model Deltas

| Risk | Current mitigation |
| --- | --- |
| Cross-type result disclosure | Polling looks up jobs by both id and job type; lint job ids are not visible through decay endpoints, and vice versa. |
| Large-scope resource exhaustion | The async threshold moves long-running work out of the request path, but broader queue quotas and cancellation controls remain open. |
| Result instability or tampering | Terminal results are stored and returned consistently for repeated polls in the reference tests. |
| Unauthorized operation execution | Authorization remains owned by the operation route before async job creation. |

## Advisories and Findings

No public GHSA is currently owned by this feature record.

## Security Gaps

- Queue depth limits are not documented as a feature-level control.
- Job cancellation is not defined.
- Retention, purge, and visibility rules for completed jobs need an operator
  policy before this surface can be considered stable.
