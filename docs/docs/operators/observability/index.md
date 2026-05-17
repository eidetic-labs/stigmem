---
title: Observability
sidebar_label: Observability
audience: Operator
---

# Observability — Prometheus and OpenTelemetry

This runbook covers the observability surface that is implemented in the
Stigmem reference node. Grafana dashboards and packaged observability compose
recipes remain experimental repo assets until they pass the ADR-008
reintroduction gates.

## What is included

| Component | Purpose |
|---|---|
| `/metrics` endpoint | Prometheus text exposition (always on when `prometheus-client` is installed) |
| OpenTelemetry SDK | Distributed traces for assert, recall, subscribe, and federation operations |
| `experimental/deploy-grafana/stigmem-dashboard.json` | Unsupported dashboard seed for self-import |

---

## Quick start — local metrics

```bash
# Start a node, then scrape metrics from the node process.
curl -s http://localhost:8765/metrics | grep '^stigmem_'
```

Prometheus, Grafana, and Tempo deployment topology is operator-owned today.
Point your scrape target at `/metrics`, and import the experimental Grafana
dashboard manually if it fits your deployment.

---

## Prometheus metrics reference

Install the optional extra to enable Prometheus exposition:

```bash
pip install "stigmem-node[observability]"
```

`/metrics` is always available — it returns a `200 OK` with an empty comment if
`prometheus-client` is not installed, so healthchecks on `/metrics` will not break.

### Counters

| Metric | Labels | Description |
|---|---|---|
| `stigmem_fact_write_total` | `principal`, `tenant` | Successful fact assertions |
| `stigmem_fact_read_total` | `principal`, `tenant` | Fact queries and recall requests |
| `stigmem_contradiction_total` | `tenant` | Facts that triggered a contradiction on write |
| `stigmem_audit_event_total` | `event_type`, `tenant` | Audit events written (`Spec-09-Audit-Log`) |
| `stigmem_quota_breach_total` | `principal`, `tenant`, `dimension` | Rate-limit 429 responses |
| `stigmem_federation_ingress_total` | `peer_id`, `status` | Facts received via federation pull |
| `stigmem_federation_egress_total` | `peer_id`, `status` | Facts served via federation pull endpoint |
| `stigmem_peer_hlc_anomaly_total` | `peer_id`, `direction` | Inbound federation HLC skew rejections |
| `stigmem_subscription_event_total` | `delivery_type`, `status` | Subscription delivery events |

### Histograms

| Metric | Labels | Buckets | Description |
|---|---|---|---|
| `stigmem_request_latency_seconds` | `route`, `method`, `status_code` | 5 ms – 2.5 s | End-to-end HTTP request latency |
| `stigmem_recall_ranker_duration_seconds` | `tenant` | 10 ms – 2.5 s | Time spent in the hybrid recall ranker |
| `stigmem_capability_verify_duration_seconds` | `result` | 1 ms – 100 ms | Capability token verification latency |

### Gauges

| Metric | Labels | Description |
|---|---|---|
| `stigmem_subscription_connections_active` | `tenant` | Active (non-circuit-open) subscriptions |
| `stigmem_replication_lag_seconds` | `peer_id` | Estimated lag to each federation peer |

---

## OpenTelemetry tracing

Enable tracing by setting two environment variables:

```bash
STIGMEM_OTEL_ENABLED=true
STIGMEM_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Or in `.env`:

```
STIGMEM_OTEL_ENABLED=true
STIGMEM_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
STIGMEM_OTEL_SERVICE_NAME=stigmem-node-prod
```

Requires `stigmem-node[observability]`:

```bash
pip install "stigmem-node[observability]"
```

### Instrumented operations

| Span name | Attributes |
|---|---|
| `stigmem.assert_fact` | `stigmem.tenant`, `stigmem.principal`, `stigmem.fact_id`, `stigmem.contradicted` |
| `stigmem.recall` | `stigmem.tenant`, `stigmem.principal`, `stigmem.scope`, `stigmem.recall_id`, `stigmem.total_scored`, `stigmem.tokens_used`, `stigmem.truncated` |

The OTLP exporter sends traces to the configured endpoint via HTTP/protobuf.  Any
OpenTelemetry-compatible backend works — Grafana Tempo, Jaeger, Honeycomb, Datadog, etc.

---

## Alerting rules

Experimental Prometheus alert seeds are available at
[`experimental/deploy-grafana/dashboards/prometheus/alerts.yml`](https://github.com/Eidetic-Labs/stigmem/blob/main/experimental/deploy-grafana/dashboards/prometheus/alerts.yml).
Review and adapt them before production use.

| Alert | Condition | Severity |
|---|---|---|
| `StigmemHighContradictionRate` | > 0.1 contradictions/s for 5 m | warning |
| `StigmemReplicationLagHigh` | Replication lag > 5 min for 5 m | critical |
| `StigmemAuditEventsMissing` | Writes but no audit events for 2 m | critical |
| `StigmemQuotaBreachSustained` | > 0.05 quota breaches/s for 10 m | warning |

To load adapted rules into a standalone Prometheus:

```yaml
# prometheus.yml
rule_files:
  - /path/to/stigmem-alerts.yml
```

---

## Smoke test

After the node is running, run a quick smoke workload to verify the metric set:

```bash
# 1. Write a fact
curl -s -X POST http://localhost:8765/v1/facts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity":"stigmem://test/thing/1","relation":"test:label","value":{"type":"text","v":"hello"},"source":"stigmem://test/agent/1","scope":"local"}' \
  | jq .id

# 2. Scrape metrics and verify counters are non-zero
curl -s http://localhost:8765/metrics | grep stigmem_fact_write_total
# Expected: stigmem_fact_write_total{...} 1.0 (or higher)

# 3. Run a recall to populate the ranker histogram
curl -s -X POST http://localhost:8765/v1/recall \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","scope":"local","token_budget":1000}' \
  | jq .total_scored

curl -s http://localhost:8765/metrics | grep stigmem_recall_ranker_duration_seconds_count
```

---

## Importing dashboards manually

The Grafana dashboard seeds live under
`experimental/deploy-grafana/dashboards/grafana/`. To try them manually:

1. Open Grafana at your instance URL.
2. Go to **Dashboards → Import**.
3. Upload `experimental/deploy-grafana/dashboards/grafana/stigmem-overview.json`.
4. Select your Prometheus datasource when prompted.
5. Repeat for `experimental/deploy-grafana/dashboards/grafana/stigmem-federation.json`.
