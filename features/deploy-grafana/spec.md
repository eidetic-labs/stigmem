# Grafana Deployment Spec

The Grafana deployment feature packages observability seed material for
Prometheus, Grafana, and Tempo. It is intended for operators who want example
dashboards and alert rules while the supported alpha observability contract
remains the node metrics endpoint and OpenTelemetry export surface.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `dashboards/grafana/stigmem-overview.json` | Grafana dashboard for fact throughput, recall latency, request latency, audit events, quota breaches, and subscription metrics. |
| `dashboards/grafana/stigmem-federation.json` | Grafana dashboard for federation ingress, egress, replication lag, contradiction rate, and audit events. |
| `dashboards/prometheus/alerts.yml` | Prometheus alert seeds for contradiction rate, replication lag, missing audit events, and quota breaches. |
| `grafana/provisioning/dashboards/dashboards.yml` | Grafana file-provider configuration for dashboards. |
| `grafana/provisioning/datasources/datasources.yml` | Grafana datasource provisioning for Prometheus and Tempo. |
| `prometheus/prometheus.yml` | Prometheus scrape configuration for two sample Stigmem nodes. |
| `tempo.yml` | Local Tempo configuration for OTLP HTTP/gRPC trace ingest and local trace storage. |
| `STATUS.md` | Legacy status pointer; this feature record owns lifecycle truth after migration. |

## Configuration Areas

| Area | Values |
| --- | --- |
| Metrics source | Prometheus scrapes `node-a:8765` and `node-b:8765` at `/metrics`. |
| Dashboards | Grafana JSON uses a Prometheus datasource variable and dashboard UIDs `stigmem-overview` and `stigmem-federation`. |
| Alerts | Alert seeds classify high replication lag and missing audit events as critical; contradiction rate and quota breaches as warning. |
| Datasources | Grafana provisioning defines Prometheus and Tempo datasources. |
| Tracing | Tempo accepts OTLP HTTP on `4318` and OTLP gRPC on `4317` with local storage. |

## Out of Scope

- Treating Grafana dashboards as the supported alpha deployment path.
- Claiming alert thresholds as production SLOs before operator review.
- Guaranteeing dashboard panel compatibility before metric contract review.
- Packaging a full observability compose overlay or hosted stack for current
  alpha support.

## Spec Assignment

There is no Spec-X assignment for Grafana deployment. It is an experimental
deployment and observability recipe rather than a protocol-bearing feature.
