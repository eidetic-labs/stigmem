# Grafana Deployment Changelog

## Unreleased

- Added ADR-020 feature record for Grafana deployment.
- Moved Grafana lifecycle, evidence, security posture, and release-line gates
  into the feature record.
- Kept the experimental Grafana dashboards, Prometheus alert seeds, provisioning
  files, Prometheus config, and Tempo config as implementation source.

## v0.9.0a1

- Tracked Grafana deployment as deferred experimental deployment and
  observability surface.
- Preserved overview dashboard, federation dashboard, Prometheus alert seeds,
  Grafana provisioning, Prometheus scrape config, and Tempo local trace config
  under `experimental/deploy-grafana`.
