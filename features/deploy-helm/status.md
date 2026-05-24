# Helm Deployment Status

The Helm deployment is deferred for the current alpha artifact set. Chart
source and operator guidance exist, but chart publication, production
validation, and ownership are not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `stigmem` |
| Implementation | `experimental/deploy-helm` |
| Publication state | `defer` - deployment chart, not a standalone plugin artifact; live cluster validation remains open. |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Helm deployment source existed as deferred experimental deployment surface. | `experimental/deploy-helm/STATUS.md`; `experimental/deploy-helm/helm/stigmem/Chart.yaml` |
| `0.9.xA` planned | Keep Helm discoverable while chart publication, production validation, hardening review, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Chart, templates, values, README, and concept doc exist. |
| Feature record | Complete | ADR-020 feature record added under `features/deploy-helm`. |
| Helm lint | Required per PR | `helm lint experimental/deploy-helm/helm/stigmem` should pass before migration PR merge. |
| Production hardening review | Open | Chart security contexts and secret handling need release-line review before support. |
| Chart publication | Open | No supported Helm repository artifact is published for current alpha. |
| Live cluster validation | Open | No current live Kubernetes validation is recorded. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- Helm is not the supported current alpha deployment path.
- Live cluster validation is not complete.
- Chart publication and upgrade compatibility are not complete.
