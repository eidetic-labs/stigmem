# PaaS Deployment Status

The PaaS deployment is deferred for the current alpha artifact set. Platform
recipes exist, but live validation, persistence evidence, secrets review,
scaling/cost review, and ownership are not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `stigmem` |
| Implementation | `experimental/deploy-paas` |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | PaaS deployment source existed as deferred experimental deployment surface. | `experimental/deploy-paas/STATUS.md`; `experimental/deploy-paas/README.md` |
| `0.9.xA` planned | Keep PaaS discoverable while live platform validation, persistence, secrets, scaling/cost review, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Render, Railway, AWS App Runner, and Google Cloud Run guides exist. |
| Feature record | Complete | ADR-020 feature record added under `features/deploy-paas`. |
| Markdown link and docs build | Required per PR | Docs build should pass before migration PR merge. |
| Live platform validation | Open | No current live validation is recorded for the named PaaS platforms. |
| Persistence validation | Open | Platform volume guidance exists, but backup/restore evidence is not recorded. |
| Secrets posture review | Open | Platform-native secret guidance requires release-line review. |
| Scaling and cost review | Open | Platform autoscaling and scale-to-zero guidance is not release-qualified. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- PaaS is not the supported current alpha deployment path.
- Live platform validation is not complete.
- Persistence, backup/restore, secrets, and scaling behavior are not
  release-qualified.
