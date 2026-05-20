---
title: Observability
sidebar_label: Observability
audience: Operator
---

# Observability — Prometheus and OpenTelemetry

<p className="stigmem-meta"><span>4 min read</span><span>SRE · Operator</span><span>v0.9.0aN</span></p>

<div className="stigmem-lead">

**What this page covers**

The observability surface that is implemented in the Stigmem
reference node: a Prometheus `/metrics` endpoint and an OpenTelemetry
SDK for distributed tracing. Grafana dashboards and packaged
observability compose recipes remain experimental repo assets until
they pass the ADR-008 reintroduction gates.

</div>

## What is included

<div className="stigmem-fields">

<div>
<dt>Component</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>/metrics</code> endpoint</dt>
<dt><span className="stigmem-fields__type">always on</span></dt>
<dd>Prometheus text exposition when <code>prometheus-client</code> is installed.</dd>
</div>

<div>
<dt>OpenTelemetry SDK</dt>
<dt><span className="stigmem-fields__type">opt-in</span></dt>
<dd>Distributed traces for assert, recall, subscribe, and federation.</dd>
</div>

<div>
<dt><code>experimental/deploy-grafana/stigmem-dashboard.json</code></dt>
<dt><span className="stigmem-fields__type">unsupported</span></dt>
<dd>Dashboard seed for self-import.</dd>
</div>

</div>

## Quick start — local metrics

```bash
# Start a node, then scrape metrics from the node process.
curl -s http://localhost:8765/metrics | grep '^stigmem_'
```

Prometheus, Grafana, and Tempo deployment topology is operator-owned today. Point your scrape target at `/metrics`, and import the experimental Grafana dashboard manually if it fits your deployment.

## Prometheus metrics reference

Install the optional extra to enable Prometheus exposition:

```bash
pip install "stigmem-node[observability]"
```

<div className="stigmem-keypoint">

**`/metrics` is always available.**

It returns `200 OK` with an empty comment if `prometheus-client` is
not installed, so healthchecks on `/metrics` will not break.

</div>

### Counters

<div className="stigmem-fields">

<div>
<dt>Metric</dt>
<dt><span className="stigmem-fields__type">Labels</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>stigmem_fact_write_total</code></dt>
<dt><span className="stigmem-fields__type">principal, tenant</span></dt>
<dd>Successful fact assertions.</dd>
</div>

<div>
<dt><code>stigmem_fact_read_total</code></dt>
<dt><span className="stigmem-fields__type">principal, tenant</span></dt>
<dd>Fact queries and recall requests.</dd>
</div>

<div>
<dt><code>stigmem_contradiction_total</code></dt>
<dt><span className="stigmem-fields__type">tenant</span></dt>
<dd>Facts that triggered a contradiction on write.</dd>
</div>

<div>
<dt><code>stigmem_audit_event_total</code></dt>
<dt><span className="stigmem-fields__type">event_type, tenant</span></dt>
<dd>Audit events written (<code>Spec-09-Audit-Log</code>).</dd>
</div>

<div>
<dt><code>stigmem_quota_breach_total</code></dt>
<dt><span className="stigmem-fields__type">principal, tenant, dimension</span></dt>
<dd>Rate-limit 429 responses.</dd>
</div>

<div>
<dt><code>stigmem_federation_ingress_total</code></dt>
<dt><span className="stigmem-fields__type">peer_id, status</span></dt>
<dd>Facts received via federation pull.</dd>
</div>

<div>
<dt><code>stigmem_federation_egress_total</code></dt>
<dt><span className="stigmem-fields__type">peer_id, status</span></dt>
<dd>Facts served via federation pull endpoint.</dd>
</div>

<div>
<dt><code>stigmem_peer_hlc_anomaly_total</code></dt>
<dt><span className="stigmem-fields__type">peer_id, direction</span></dt>
<dd>Inbound federation HLC skew rejections.</dd>
</div>

<div>
<dt><code>stigmem_subscription_event_total</code></dt>
<dt><span className="stigmem-fields__type">delivery_type, status</span></dt>
<dd>Subscription delivery events.</dd>
</div>

</div>

### Histograms

<div className="stigmem-fields">

<div>
<dt>Metric</dt>
<dt><span className="stigmem-fields__type">Buckets</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>stigmem_request_latency_seconds</code></dt>
<dt><span className="stigmem-fields__type">5 ms – 2.5 s</span></dt>
<dd>End-to-end HTTP request latency (route, method, status_code).</dd>
</div>

<div>
<dt><code>stigmem_recall_ranker_duration_seconds</code></dt>
<dt><span className="stigmem-fields__type">10 ms – 2.5 s</span></dt>
<dd>Time spent in the hybrid recall ranker (tenant).</dd>
</div>

<div>
<dt><code>stigmem_capability_verify_duration_seconds</code></dt>
<dt><span className="stigmem-fields__type">1 ms – 100 ms</span></dt>
<dd>Capability token verification latency (result).</dd>
</div>

</div>

### Gauges

<div className="stigmem-fields">

<div>
<dt>Metric</dt>
<dt><span className="stigmem-fields__type">Labels</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>stigmem_subscription_connections_active</code></dt>
<dt><span className="stigmem-fields__type">tenant</span></dt>
<dd>Active (non-circuit-open) subscriptions.</dd>
</div>

<div>
<dt><code>stigmem_replication_lag_seconds</code></dt>
<dt><span className="stigmem-fields__type">peer_id</span></dt>
<dd>Estimated lag to each federation peer.</dd>
</div>

</div>

## OpenTelemetry tracing

Enable tracing by setting two environment variables:

```bash
STIGMEM_OTEL_ENABLED=true
STIGMEM_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Requires `stigmem-node[observability]`:

```bash
pip install "stigmem-node[observability]"
```

### Instrumented operations

<div className="stigmem-fields">

<div>
<dt>Span name</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Attributes</dd>
</div>

<div>
<dt><code>stigmem.assert_fact</code></dt>
<dt><span className="stigmem-fields__type">write</span></dt>
<dd><code>stigmem.tenant</code>, <code>stigmem.principal</code>, <code>stigmem.fact_id</code>, <code>stigmem.contradicted</code>.</dd>
</div>

<div>
<dt><code>stigmem.recall</code></dt>
<dt><span className="stigmem-fields__type">read</span></dt>
<dd><code>stigmem.tenant</code>, <code>stigmem.principal</code>, <code>stigmem.scope</code>, <code>stigmem.recall_id</code>, <code>stigmem.total_scored</code>, <code>stigmem.tokens_used</code>, <code>stigmem.truncated</code>.</dd>
</div>

</div>

The OTLP exporter sends traces to the configured endpoint via HTTP/protobuf. Any OpenTelemetry-compatible backend works — Grafana Tempo, Jaeger, Honeycomb, Datadog, etc.

## Alerting rules

Experimental Prometheus alert seeds are available at [`experimental/deploy-grafana/dashboards/prometheus/alerts.yml`](https://github.com/eidetic-labs/stigmem/blob/main/experimental/deploy-grafana/dashboards/prometheus/alerts.yml). Review and adapt them before production use.

<div className="stigmem-fields">

<div>
<dt>Alert</dt>
<dt><span className="stigmem-fields__type">Severity</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt><code>StigmemHighContradictionRate</code></dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>&gt; 0.1 contradictions/s for 5 m.</dd>
</div>

<div>
<dt><code>StigmemReplicationLagHigh</code></dt>
<dt><span className="stigmem-fields__type">critical</span></dt>
<dd>Replication lag &gt; 5 min for 5 m.</dd>
</div>

<div>
<dt><code>StigmemAuditEventsMissing</code></dt>
<dt><span className="stigmem-fields__type">critical</span></dt>
<dd>Writes but no audit events for 2 m.</dd>
</div>

<div>
<dt><code>StigmemQuotaBreachSustained</code></dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>&gt; 0.05 quota breaches/s for 10 m.</dd>
</div>

</div>

To load adapted rules into a standalone Prometheus:

```yaml
# prometheus.yml
rule_files:
  - /path/to/stigmem-alerts.yml
```

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

# 3. Run a recall to populate the ranker histogram
curl -s -X POST http://localhost:8765/v1/recall \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","scope":"local","token_budget":1000}' \
  | jq .total_scored

curl -s http://localhost:8765/metrics | grep stigmem_recall_ranker_duration_seconds_count
```

## Importing dashboards manually

<ol className="stigmem-steps">
<li>Open Grafana at your instance URL.</li>
<li>Go to <strong>Dashboards → Import</strong>.</li>
<li>Upload <code>experimental/deploy-grafana/dashboards/grafana/stigmem-overview.json</code>.</li>
<li>Select your Prometheus datasource when prompted.</li>
<li>Repeat for <code>stigmem-federation.json</code>.</li>
</ol>
