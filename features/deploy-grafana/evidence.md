# Grafana Deployment Evidence

This file records evidence for the Grafana deployment feature. The current
record is source-inventory and static syntax evidence only; it does not claim
live Grafana/Prometheus/Tempo stack support.

## Source Inventory

| Path | Evidence |
| --- | --- |
| `experimental/deploy-grafana/dashboards/grafana/stigmem-overview.json` | Grafana overview dashboard for node, recall, audit, quota, and subscription metrics. |
| `experimental/deploy-grafana/dashboards/grafana/stigmem-federation.json` | Grafana federation dashboard for replication and federation metrics. |
| `experimental/deploy-grafana/dashboards/prometheus/alerts.yml` | Prometheus alert seeds. |
| `experimental/deploy-grafana/grafana/provisioning/dashboards/dashboards.yml` | Grafana dashboard provisioning config. |
| `experimental/deploy-grafana/grafana/provisioning/datasources/datasources.yml` | Grafana datasource provisioning config. |
| `experimental/deploy-grafana/prometheus/prometheus.yml` | Prometheus scrape config. |
| `experimental/deploy-grafana/tempo.yml` | Tempo local trace config. |
| `experimental/deploy-grafana/STATUS.md` | Legacy pointer after ADR-020 migration. |

## Validation

| Check | Status | Notes |
| --- | --- | --- |
| Feature record validation | Required per PR | `python3 scripts/check_feature_records.py`. |
| Feature projection validation | Required per PR | `python3 scripts/check_feature_projections.py`. |
| Security projection validation | Required per PR | `python3 scripts/check_feature_security_projection.py`. |
| Changelog projection validation | Required per PR | `python3 scripts/check_feature_changelog_projection.py`. |
| Compatibility projection validation | Required per PR | `python3 scripts/check_feature_compatibility_projection.py`. |
| Protocol projection validation | Required per PR | `python3 scripts/check_feature_protocol_projection.py`. |
| Static JSON syntax | Required per PR | Parse Grafana dashboard JSON files with Python `json`. |
| Static YAML syntax | Required per PR | Parse Prometheus, Grafana provisioning, and Tempo YAML files with a local YAML parser. |

## Open Evidence

- No live Grafana/Prometheus/Tempo stack validation is recorded.
- No dashboard screenshot or rendered-panel validation is recorded.
- No production alert-threshold review is recorded.
- No operator ownership evidence is recorded.
