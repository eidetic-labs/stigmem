# Grafana Deployment Status

The Grafana deployment is deferred for the current alpha artifact set.
Dashboard JSON, Prometheus alert seeds, Grafana provisioning, Prometheus
scrape config, and Tempo config exist, but live stack validation, metric
contract review, alert review, packaging guidance, and ownership are not
complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `none` |
| Implementation | `experimental/deploy-grafana` |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Grafana deployment source existed as deferred experimental deployment and observability surface. | `experimental/deploy-grafana/STATUS.md`; `experimental/deploy-grafana/dashboards/grafana/stigmem-overview.json` |
| `0.9.xA` planned | Keep Grafana discoverable while live stack validation, metric contract review, alert review, packaging guidance, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Dashboard JSON, Prometheus alert seeds, provisioning files, scrape config, and Tempo config exist. |
| Feature record | Complete | ADR-020 feature record added under `features/deploy-grafana`. |
| Static config syntax | Required per PR | Grafana JSON and YAML config files should parse before migration PR merge. |
| Live stack validation | Open | No current Grafana/Prometheus/Tempo stack validation is recorded. |
| Metric contract review | Open | Dashboard panels and alert expressions need review against the current node metrics contract. |
| Alert review | Open | Alert thresholds are seeds, not production SLO commitments. |
| Packaging guidance | Open | No supported compose overlay, Helm overlay, or hosted stack guidance is published. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- Grafana is not the supported current alpha deployment path.
- Live stack validation is not complete.
- Dashboard panels and alert thresholds have not completed release-line review.
