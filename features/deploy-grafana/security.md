# Grafana Deployment Security

The Grafana deployment recipe is an experimental observability surface. Its
security posture depends on safe operator deployment, datasource access
control, metric and trace data classification, and review of alerting behavior
before production use.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Datasource locality | Prometheus and Tempo datasources point at internal service names in the seed config. | `experimental/deploy-grafana/grafana/provisioning/datasources/datasources.yml` |
| Metrics scrape scope | Prometheus seed config scrapes two named node targets at `/metrics`. | `experimental/deploy-grafana/prometheus/prometheus.yml` |
| Alert seeds | Alert rules focus on contradiction rate, replication lag, missing audit events, and quota breaches. | `experimental/deploy-grafana/dashboards/prometheus/alerts.yml` |
| Trace storage | Tempo seed config uses local trace storage paths. | `experimental/deploy-grafana/tempo.yml` |
| Dashboard import | Dashboard JSON contains dashboard definitions, not credentials. | `experimental/deploy-grafana/dashboards/grafana/stigmem-overview.json`; `experimental/deploy-grafana/dashboards/grafana/stigmem-federation.json` |

## Security References

No dedicated R-* audit item is assigned to Grafana deployment. Related
observability, federation, audit, and quota risks live in the public security
docs and threat model.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Live stack validation has not been recorded.
- Metrics and traces may expose tenant, peer, route, latency, or operational
  metadata depending on node configuration and labels.
- Alert thresholds are seed values, not production SLOs.
- Grafana authentication, dashboard sharing, datasource permissions, retention,
  and network exposure are operator-owned in the current alpha line.
- Tempo local trace retention and disk use need operator review before use.

## Operator Guidance

- Do not expose Grafana, Prometheus, or Tempo without authentication and network
  controls.
- Review metric labels and traces for sensitive metadata before exporting them
  outside a trusted environment.
- Treat alert rules as examples until production thresholds are reviewed for
  the deployment.
- Treat Grafana deployment as unsupported until future-alpha promotion gates
  complete.
