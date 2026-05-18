---
title: Monitoring & Debugging
sidebar_label: Monitoring & Debugging
description: Health checks, log interpretation, recall-latency diagnosis, and operational metrics for Stigmem node operators.
audience: Operator
---

# Monitoring & Debugging

**Audience:** operators and SREs running Stigmem in production.

---

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

| Field | What to watch for |
|---|---|
| `status` | Must be `"ok"`. Any other value means the node is unhealthy. |
| `sync_lag_ms` | libSQL only. High values (> 5 000 ms) suggest a network issue between the replica and the Turso primary. |
| `federation_enabled` | Should be `true` if you've enabled federation. |

**Kubernetes / PaaS:** point your liveness and readiness probes at `/healthz`.

---

## Logs

The node emits structured JSON logs to stdout. Use `LOG_LEVEL` to control verbosity:

```bash
STIGMEM_LOG_LEVEL=debug   # maximum detail; avoid in production at scale
STIGMEM_LOG_LEVEL=info    # default; startup, request/response summaries, federation events
STIGMEM_LOG_LEVEL=warning # only warnings and errors
```

Key log events and what they mean:

| Log message fragment | Meaning |
|---|---|
| `federation.pull.ok` | Successful pull from a peer |
| `federation.pull.signature_mismatch` | Peer's key changed; update the pin |
| `federation.pull.peer_unreachable` | Network or peer-side issue |
| `storage.migration.applied` | Schema migration ran on startup |
| `recall.embedding.provider_error` | Embedding provider unavailable |
| `recall.latency_ms > 1000` | Recall taking > 1 s — see [Recall latency](#recall-latency) |
| `snapshot.create.ok` | Backup snapshot created successfully |
| `snapshot.verify.fail` | Snapshot verification failed — do not restore |

### Tailing logs

```bash
# Docker Compose
docker compose logs -f node
```

---

## Metrics

The node exposes a Prometheus-compatible metrics endpoint at `/metrics`:

```bash
curl -s https://your-node.example.com/metrics | grep stigmem_
```

Key metrics:

| Metric | Description |
|---|---|
| `stigmem_fact_write_total` | Successful fact assertions by principal and tenant |
| `stigmem_fact_read_total` | Fact queries and recall requests by principal and tenant |
| `stigmem_request_latency_seconds` | End-to-end HTTP request latency by route, method, and status |
| `stigmem_recall_ranker_duration_seconds` | Hybrid recall ranker duration by tenant |
| `stigmem_federation_ingress_total` | Facts received via federation pull by peer and status |
| `stigmem_federation_egress_total` | Facts served via federation pull endpoint by peer and status |
| `stigmem_replication_lag_seconds` | Estimated replication lag by peer |
| `stigmem_peer_hlc_anomaly_total` | Inbound federation HLC skew rejections by peer and direction |
| `stigmem_audit_event_total` | Audit events written by event type and tenant |

### Grafana dashboard

A sample Grafana dashboard JSON is available at [`experimental/deploy-grafana/stigmem-dashboard.json`](https://github.com/eidetic-labs/stigmem/blob/main/experimental/deploy-grafana/stigmem-dashboard.json) in the repo. Grafana support is deferred per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md); the dashboard remains buildable for self-import but is unsupported until it passes the [ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). Import it into your Grafana instance and point the data source at your Prometheus scrape target.

---

## Recall latency

Recall (semantic search) combines vector lookup with graph traversal. High latency usually has one of three causes:

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

If using an API provider (OpenAI, Voyage), check for rate limiting or network issues.

**Tip:** switch to the offline default (`STIGMEM_EMBED_PROVIDER=ollama`) during an outage to eliminate provider dependency.

### 2. Vector index not built yet

After a large batch of fact imports, the vector index may not be fully built. Check:

```bash
curl -s https://your-node.example.com/v1/recall/status | jq .
```

If `index_coverage` is below `1.0`, the index is still building. Recall continues to work but may miss recently added facts until indexing catches up.

### 3. Database query slow (high fact volume)

For large nodes (millions of facts), storage query latency may dominate. Diagnose:

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

---

## Federation debugging

If pull replication stops or stalls:

```bash
# Check peer status and last pull time
curl -s https://your-node.example.com/v1/federation/peers | jq '.peers[] | {id, last_pull, pull_lag_ms, error}'

# Check federation audit log
curl -s "https://your-node.example.com/v1/federation/audit?limit=20" | jq .

# Force an immediate pull cycle for a specific peer (skips the interval)
curl -X POST https://your-node.example.com/v1/federation/peers/<peer-id>/pull \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY"
```

Common issues:

| Symptom | Cause | Fix |
|---|---|---|
| `pull_lag_ms` growing | Network latency or peer overloaded | Increase `STIGMEM_FEDERATION_PULL_INTERVAL_S` |
| `error: signature_mismatch` | Peer rotated its key | Update peer pin |
| `error: peer_unreachable` | DNS or firewall | Check `STIGMEM_NODE_URL` and peer's firewall |
| No facts arriving despite healthy pull | Scope filter mismatch | Check `STIGMEM_FEDERATION_ALLOW_TEAM` if team-scoped facts are expected |

---

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
