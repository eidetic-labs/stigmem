---
title: Audit Log & Per-Principal Quotas
sidebar_label: Audit & Quotas
description: Operator guide for the audit.read capability, the GET /v1/admin/audit endpoint, and per-principal token-bucket quota tuning (Spec-09-Audit-Log–Spec-10-Hardening rate limits).
audience: Operator
---

# Audit Log & Per-Principal Quotas

This guide covers two pre-reset hardening security hardening features (Spec-09-Audit-Log and Spec-10-Hardening rate limits):

- **Audit log surface** — how to mint an `audit.read` API key and query the structured audit log.
- **Per-principal quotas** — the 7 token-bucket dimensions, their defaults, and how to tune them via environment variables.

**Audience:** node operators, SIEM/monitoring integrators.

---

## Audit log surface (Spec-09-Audit-Log)

### The audit.read capability

Access to `/v1/admin/audit` is gated on the `audit.read` capability.  It is a permission string in the API key's `permissions` array — not a separate admin role.  A key can hold any combination of `read`, `write`, and `audit.read`.

```python
# Mint a dedicated audit key (Python SDK)
from stigmem_client import StigmemClient

client = StigmemClient(base_url="https://node.example.com", api_key=ADMIN_KEY)
audit_key = client.create_api_key(
    entity_uri="stigmem://your-org.example.com/siem-reader",
    permissions=["audit.read"],   # read/write not required for audit access
)
print(audit_key.key)   # store securely
```

```bash
# Equivalent curl — POST /v1/admin/api-keys
curl -s -X POST https://node.example.com/v1/admin/api-keys \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_uri": "stigmem://your-org.example.com/siem-reader",
    "permissions": ["audit.read"]
  }' | jq '.key'
```

Requests to `GET /v1/admin/audit` without `audit.read` return **403**:

```json
{"detail": "audit.read capability required"}
```

### Querying the audit log

```
GET /v1/admin/audit
Authorization: Bearer <audit.read key>
```

#### Query parameters

| Parameter | Type | Description |
|---|---|---|
| `since` | RFC3339 | Include events with `ts >= since` (inclusive) |
| `until` | RFC3339 | Include events with `ts <= until` (inclusive) |
| `principal` | string | Filter by `entity_uri` of the acting principal |
| `event_type` | string | Filter to one event type (e.g. `quota_breach`) |
| `cursor` | integer | Opaque seq-based cursor for forward pagination |
| `limit` | integer | Page size — range 1–1000, default 200 |

#### Response schema

```json
{
  "entries": [
    {
      "seq":             12345,
      "id":              "018f1a2b-...",
      "event_type":      "quota_breach",
      "entity_uri":      "stigmem://your-org.example.com/my-agent",
      "oidc_sub":        "108...",
      "fact_id":         null,
      "source":          "API caller",
      "attested_key_id": null,
      "ts":              "2026-05-03T12:00:00Z",
      "tenant_id":       "default",
      "detail":          "{\"dimension\": \"fact_write\", \"retry_after\": 3.2}"
    }
  ],
  "total":       200,
  "next_cursor": 12346
}
```

- **`seq`** — monotonically increasing integer per database; use it as the `cursor` value for the next page.
- **`next_cursor`** — absent when the current page is the last page.
- **`detail`** — JSON-encoded map of event-specific fields; schema varies by `event_type` (see Spec-09-Audit-Log event types).

#### Tenant isolation

The API automatically scopes results to the caller's `tenant_id`.  Cross-tenant entries are never returned regardless of credentials.

#### Pagination example

```bash
AUDIT_KEY="<your audit.read key>"
BASE="https://node.example.com/v1/admin/audit"
CURSOR=""

while true; do
  PARAMS="limit=500&event_type=quota_breach"
  [[ -n "$CURSOR" ]] && PARAMS="${PARAMS}&cursor=${CURSOR}"

  RESP=$(curl -s "${BASE}?${PARAMS}" -H "Authorization: Bearer $AUDIT_KEY")
  echo "$RESP" | jq '.entries[] | {seq, ts, principal: .entity_uri}'

  NEXT=$(echo "$RESP" | jq -r '.next_cursor // empty')
  [[ -z "$NEXT" ]] && break
  CURSOR="$NEXT"
done
```

### Audit event types (Spec-09-Audit-Log event types)

Sixteen event types are emitted to `fact_audit_log`.  All are returned by `GET /v1/admin/audit` unless filtered by `event_type`.

| Event type | Trigger |
|---|---|
| `fact_write` | Fact assertion or retraction |
| `fact_read` | Recall / query returning ≥ 1 fact |
| `capability_token_issue` | Capability token issued |
| `capability_token_revoke` | Capability token revoked |
| `manifest_publish` | Org manifest updated |
| `key_rotation` | API key rotated |
| `federation_connect` | Federation peer connection attempt |
| `quarantine_admit` | Fact held in quarantine |
| `quarantine_release` | Quarantined fact accepted or rejected |
| `quota_breach` | Per-principal quota ceiling hit |
| `admin_action` | Admin API call |
| `replay_rejected` | Token replay nonce collision |
| `instruction_audit` | Lazy instruction chunk loaded |
| `instruction_quarantined` | Instruction-namespace fact placed in quarantine pending approval |
| `instruction_promoted` | Quarantined instruction-namespace fact promoted by an operator |
| `api_key_rehashed` | Legacy SHA-256 API key row migrated to Argon2id after successful authentication |

### Write-ahead ordering (Spec-09-Audit-Log write-ahead ordering)

Audit events are persisted **before** the HTTP response is sent.  If the node crashes after writing the event but before responding, the event is still in the log.

### Retention (Spec-09-Audit-Log retention)

- **Minimum:** 90 days
- **Recommended for forensics:** 1 year
- The `fact_audit_log` table is append-only; rows are never modified by the node

---

## Per-principal quotas (Spec-10-Hardening rate limits) {#per-principal-quotas}

### Model

Stigmem uses a **token-bucket** rate limiter, one bucket per `(entity_uri, tenant_id, dimension)` triple (Spec-10-Hardening token-bucket model).  Every inbound request consumes one token from the relevant dimension bucket.  Tokens refill continuously at a fixed rate up to the bucket capacity.

### The 7 dimensions and their defaults (Spec-10-Hardening quota dimensions)

| Dimension | Capacity | Refill rate | Covers |
|---|---|---|---|
| `fact_write` | 100 tokens | 10 tokens/sec | `POST /v1/facts`, `DELETE /v1/facts/*` |
| `fact_read` | 500 tokens | 50 tokens/sec | `GET /v1/facts/*`, `GET /v1/recall*` |
| `token_issue` | 20 tokens | 0.33 tokens/sec | `POST /v1/federation/capability-tokens` |
| `federation_pull` | 30 tokens | 0.5 tokens/sec | Outbound pull replication |
| `admin_action` | 10 tokens | 0.17 tokens/sec | `POST /v1/admin/*` |
| `subscription_event` | 200 tokens | 20 tokens/sec | Outbound subscription deliveries |
| `audit_export` | 10,000 tokens | 167 tokens/sec | Rows returned by `GET /v1/admin/audit` |

Federation peer requests (using peer-token auth) and unauthenticated health-check paths are exempt from quota.

### Tuning via environment variables

The legacy per-hour env vars control the effective rate for `fact_write` and `fact_read`.  At startup they are converted to token-bucket parameters:

```
rate_per_second = ceiling / 3600
```

| Variable | Default | Effect |
|---|---|---|
| `STIGMEM_RATE_LIMIT_WRITE_PER_HOUR` | `1000` | Sets `fact_write` refill rate |
| `STIGMEM_RATE_LIMIT_READ_PER_HOUR` | `5000` | Sets `fact_read` refill rate |

```bash
# Example: allow 10 000 writes/hour for a high-throughput ingest node
STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=10000

# Disable quotas entirely (dev/test only — do not use in production)
STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=0
STIGMEM_RATE_LIMIT_READ_PER_HOUR=0
```

> Setting either variable to `0` disables the token-bucket check for that dimension globally (all principals).  Never do this in production — it removes the per-principal backpressure that protects the node from noisy neighbours and credential misuse.

Bucket state (current tokens, last refill timestamp) is stored in the `quota_buckets` SQLite table.  It persists across restarts.

### 429 response shape and Retry-After semantics (Spec-10-Hardening 429 backpressure)

When a request exceeds the bucket:

**HTTP 429 Too Many Requests**

```json
{
  "error": "quota_exceeded",
  "dimension": "fact_write",
  "principal": "stigmem://your-org.example.com/my-agent",
  "retry_after": 3.2
}
```

The `Retry-After` header is set to the integer ceiling of `retry_after` (seconds).  Clients should honour it and not immediately retry.

### quota_breach audit events

Every 429 response generates a `quota_breach` audit event **before** the response is sent (write-ahead).  The `detail` field contains:

```json
{
  "dimension":   "fact_write",
  "path":        "/v1/facts",
  "method":      "POST",
  "retry_after": 3.2
}
```

Query recent quota breaches across all principals:

```bash
curl -s "https://node.example.com/v1/admin/audit?event_type=quota_breach&limit=100" \
  -H "Authorization: Bearer $AUDIT_KEY" \
  | jq '.entries[] | {ts, principal: .entity_uri, detail: (.detail | fromjson)}'
```

---

## Operator checklist

### Audit key management

- [ ] **Mint a dedicated `audit.read` key** for each monitoring or SIEM consumer.  Never reuse application keys for audit access — a compromised app key would also expose the audit trail.
- [ ] Store audit keys in your secrets manager (Vault, AWS Secrets Manager, 1Password) with a rotation schedule.
- [ ] If your SIEM supports it, configure it to pull from `/v1/admin/audit` on a schedule and forward `quota_breach` and `replay_rejected` events to your alerting pipeline.

### Retention

- [ ] Verify that `fact_audit_log` rows older than 90 days have not been deleted.  The node does not auto-purge; implement retention via your own SQLite maintenance job or by exporting to cold storage.

  ```sql
  -- Check oldest event in the log
  SELECT min(ts), count(*) FROM fact_audit_log;
  ```

- [ ] For compliance use cases, export audit log rows to an immutable store (S3 Object Lock, GCS object versioning, Worm-enabled storage) before the 90-day window.

### Prometheus metrics

When `prometheus_client` is installed, the node exposes a `/metrics` endpoint with quota and audit counters.  Useful metrics:

| Metric | Description |
|---|---|
| `stigmem_quota_breaches_total` | Counter by `(dimension, entity_uri)` |
| `stigmem_audit_events_total` | Counter by `event_type` |
| `stigmem_audit_log_rows` | Current row count in `fact_audit_log` |

Install the optional dependency:

```bash
pip install prometheus_client
```

No additional configuration is required — the endpoint is registered automatically if the package is importable at startup.

### Quota baselines

- [ ] After 24 hours of representative traffic, query `quota_breach` events and identify principals that breach repeatedly.  Increase `STIGMEM_RATE_LIMIT_WRITE_PER_HOUR` / `STIGMEM_RATE_LIMIT_READ_PER_HOUR` if the defaults are too tight for legitimate workloads, or investigate the offending principal.
- [ ] Set a Prometheus alert on `stigmem_quota_breaches_total` to catch runaway clients before they degrade the node for other principals.

---

## Related

- [mTLS Federation Transport](./mtls.md) — Spec-10-Hardening
- [Key Rotation](./key-rotation.md) — Spec-10-Hardening
- [Monitoring](../operators/observability/monitoring.md) — Prometheus metrics, structured logs, health endpoints
