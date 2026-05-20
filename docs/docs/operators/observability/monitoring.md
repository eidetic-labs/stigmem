---
title: Monitoring & Debugging
sidebar_label: Monitoring & Debugging
description: Health checks, log interpretation, recall-latency diagnosis, and operational metrics for Stigmem node operators.
audience: Operator
---

# Monitoring & Debugging

<p className="stigmem-meta"><span>5 min read</span><span>SRE · Operator</span><span>Day-two operations</span></p>

<div className="stigmem-lead">

**What this page covers**

Health checks, log interpretation, recall-latency diagnosis, and
operational metrics for Stigmem node operators.

</div>

**Audience:** operators and SREs running Stigmem in production.

## Health check

The `/healthz` endpoint is the canonical liveness probe:

```bash
curl -s https://your-node.example.com/healthz | jq .
```

```json
{
  "status": "ok",
  "backend": "libsql",
  "sync_lag_ms": 12,
  "federation_enabled": true,
  "version": "1.0.0"
}
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Watch for</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>status</code></dt>
<dt><span className="stigmem-fields__type">must be "ok"</span></dt>
<dd>Any other value means the node is unhealthy.</dd>
</div>

<div>
<dt><code>sync_lag_ms</code></dt>
<dt><span className="stigmem-fields__type">&lt; 5000 ms</span></dt>
<dd>libSQL only. High values suggest a network issue between the replica and the Turso primary.</dd>
</div>

<div>
<dt><code>federation_enabled</code></dt>
<dt><span className="stigmem-fields__type">true if enabled</span></dt>
<dd>Should match your configuration.</dd>
</div>

</div>

**Kubernetes / PaaS:** point your liveness and readiness probes at `/healthz`.

## Logs

The node emits structured JSON logs to stdout. Use `LOG_LEVEL` to control verbosity:

```bash
STIGMEM_LOG_LEVEL=debug   # maximum detail; avoid in production at scale
STIGMEM_LOG_LEVEL=info    # default
STIGMEM_LOG_LEVEL=warning # only warnings and errors
```

**Key log events:**

<div className="stigmem-fields">

<div>
<dt>Message fragment</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>federation.pull.ok</code></dt>
<dt><span className="stigmem-fields__type">success</span></dt>
<dd>Successful pull from a peer.</dd>
</div>

<div>
<dt><code>federation.pull.signature_mismatch</code></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>Peer's key changed; update the pin.</dd>
</div>

<div>
<dt><code>federation.pull.peer_unreachable</code></dt>
<dt><span className="stigmem-fields__type">network</span></dt>
<dd>Network or peer-side issue.</dd>
</div>

<div>
<dt><code>storage.migration.applied</code></dt>
<dt><span className="stigmem-fields__type">startup</span></dt>
<dd>Schema migration ran on startup.</dd>
</div>

<div>
<dt><code>recall.embedding.provider_error</code></dt>
<dt><span className="stigmem-fields__type">degraded</span></dt>
<dd>Embedding provider unavailable.</dd>
</div>

<div>
<dt><code>recall.latency_ms &gt; 1000</code></dt>
<dt><span className="stigmem-fields__type">performance</span></dt>
<dd>Recall taking &gt; 1 s — see Recall latency below.</dd>
</div>

<div>
<dt><code>snapshot.create.ok</code></dt>
<dt><span className="stigmem-fields__type">backup</span></dt>
<dd>Backup snapshot created successfully.</dd>
</div>

<div>
<dt><code>snapshot.verify.fail</code></dt>
<dt><span className="stigmem-fields__type">critical</span></dt>
<dd>Snapshot verification failed — do not restore.</dd>
</div>

</div>

```bash
# Docker Compose
docker compose logs -f node
```

## Metrics

```bash
curl -s https://your-node.example.com/metrics | grep stigmem_
```

**Key metrics** (see [Observability](./index.md) for the full reference):

<div className="stigmem-grid">

<div><h4><code>stigmem_fact_write_total</code></h4></div>
<div><h4><code>stigmem_fact_read_total</code></h4></div>
<div><h4><code>stigmem_request_latency_seconds</code></h4></div>
<div><h4><code>stigmem_recall_ranker_duration_seconds</code></h4></div>
<div><h4><code>stigmem_federation_ingress_total</code></h4></div>
<div><h4><code>stigmem_federation_egress_total</code></h4></div>
<div><h4><code>stigmem_replication_lag_seconds</code></h4></div>
<div><h4><code>stigmem_peer_hlc_anomaly_total</code></h4></div>
<div><h4><code>stigmem_audit_event_total</code></h4></div>

</div>

A sample Grafana dashboard JSON is available at [`experimental/deploy-grafana/stigmem-dashboard.json`](https://github.com/eidetic-labs/stigmem/blob/main/experimental/deploy-grafana/stigmem-dashboard.json). Grafana support is deferred per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md); the dashboard remains buildable for self-import but is unsupported until it passes the ADR-008 reintroduction gates.

## Recall latency

Recall (semantic search) combines vector lookup with graph traversal. High latency usually has one of three causes.

### 1. Embedding provider slow or unavailable

```bash
# Check if the embedding provider is reachable
curl -s http://localhost:11434/api/tags   # Ollama default
```

If using Ollama, ensure the model is pulled and running:

```bash
ollama pull nomic-embed-text
ollama serve &
```

<div className="stigmem-keypoint">

**Switch to the offline default (`STIGMEM_EMBED_PROVIDER=ollama`) during an outage to eliminate provider dependency.**

</div>

### 2. Vector index not built yet

After a large batch of fact imports, the vector index may not be fully built. Check:

```bash
curl -s https://your-node.example.com/v1/recall/status | jq .
```

If `index_coverage` is below `1.0`, the index is still building. Recall continues to work but may miss recently added facts until indexing catches up.

### 3. Database query slow (high fact volume)

```bash
# Check storage backend latency from metrics
curl -s https://your-node.example.com/metrics \
  | grep stigmem_storage_query_latency_seconds

# Enable query explain for debugging (SQLite and libSQL only — do not use in production)
STIGMEM_STORAGE_EXPLAIN_QUERIES=true stigmem serve
```

For Postgres at scale, ensure `pgvector` index is created:

```sql
-- Check vector index
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'vec_facts';

-- Create IVFFlat index if missing (adjust lists based on fact count)
CREATE INDEX ON vec_facts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## Federation debugging

```bash
# Check peer status and last pull time
curl -s https://your-node.example.com/v1/federation/peers | jq '.peers[] | {id, last_pull, pull_lag_ms, error}'

# Check federation audit log
curl -s "https://your-node.example.com/v1/federation/audit?limit=20" | jq .

# Force an immediate pull cycle for a specific peer (skips the interval)
curl -X POST https://your-node.example.com/v1/federation/peers/<peer-id>/pull \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY"
```

**Common issues:**

<div className="stigmem-fields">

<div>
<dt>Symptom</dt>
<dt><span className="stigmem-fields__type">Cause</span></dt>
<dd>Fix</dd>
</div>

<div>
<dt><code>pull_lag_ms</code> growing</dt>
<dt><span className="stigmem-fields__type">network / overload</span></dt>
<dd>Increase <code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code>.</dd>
</div>

<div>
<dt><code>signature_mismatch</code></dt>
<dt><span className="stigmem-fields__type">key rotated</span></dt>
<dd>Update peer pin.</dd>
</div>

<div>
<dt><code>peer_unreachable</code></dt>
<dt><span className="stigmem-fields__type">DNS / firewall</span></dt>
<dd>Check <code>STIGMEM_NODE_URL</code> and peer's firewall.</dd>
</div>

<div>
<dt>No facts despite healthy pull</dt>
<dt><span className="stigmem-fields__type">scope filter</span></dt>
<dd>Check <code>STIGMEM_FEDERATION_ALLOW_TEAM</code> if team-scoped facts are expected.</dd>
</div>

</div>

## Alerts

Recommended alert rules (Prometheus / Alertmanager notation):

```yaml
groups:
  - name: stigmem
    rules:
      - alert: StigmemDown
        expr: up{job="stigmem"} == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Stigmem node is down"

      - alert: StigmemHighRecallLatency
        expr: histogram_quantile(0.99, stigmem_recall_ranker_duration_seconds_bucket) > 5
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "99th-percentile recall ranker latency > 5s"

      - alert: StigmemFederationIngressErrors
        expr: sum by (peer_id) (increase(stigmem_federation_ingress_total{status!="accepted"}[5m])) > 3
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Federation ingress errors spiking"

      - alert: StigmemPeerHlcAnomaly
        expr: sum by (peer_id) (increase(stigmem_peer_hlc_anomaly_total[1h])) > 5
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Peer HLC anomaly events above threshold"

      - alert: StigmemLibSQLHighSyncLag
        expr: stigmem_libsql_sync_lag_ms > 10000
        for: 2m
        labels: { severity: warning }
        annotations:
          summary: "libSQL sync lag > 10s — replica falling behind primary"
```
