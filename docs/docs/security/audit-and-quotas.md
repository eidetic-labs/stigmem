---
title: Audit Log & Per-Principal Quotas
sidebar_label: Audit & Quotas
description: Operator guide for the audit.read capability, the GET /v1/admin/audit endpoint, and per-principal token-bucket quota tuning (Spec-09-Audit-Log--Spec-10-Hardening rate limits).
audience: Operator
---

# Audit Log & Per-Principal Quotas

<p className="stigmem-meta"><span>6 min read</span><span>Operator · SIEM integrator</span><span>Spec-09 + Spec-10</span></p>

<div className="stigmem-lead">

**What this page covers**

Two pre-reset hardening security features: how to mint an
`audit.read` API key and query the structured audit log (Spec-09),
and the 7 token-bucket quota dimensions, their defaults, and how to
tune them via environment variables (Spec-10).

</div>

## Audit log surface (Spec-09-Audit-Log)

### The `audit.read` capability

<div className="stigmem-keypoint">

**`audit.read` is a permission string, not a separate admin role.**

A key can hold any combination of <code>read</code>, <code>write</code>,
and <code>audit.read</code>. Access to <code>/v1/admin/audit</code> is
gated on <code>audit.read</code>.

</div>

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

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>since</code></dt>
<dt><span className="stigmem-fields__type">RFC3339</span></dt>
<dd>Include events with <code>ts &gt;= since</code> (inclusive).</dd>
</div>

<div>
<dt><code>until</code></dt>
<dt><span className="stigmem-fields__type">RFC3339</span></dt>
<dd>Include events with <code>ts &lt;= until</code> (inclusive).</dd>
</div>

<div>
<dt><code>principal</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter by <code>entity_uri</code> of the acting principal.</dd>
</div>

<div>
<dt><code>event_type</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter to one event type (e.g. <code>quota_breach</code>).</dd>
</div>

<div>
<dt><code>cursor</code></dt>
<dt><span className="stigmem-fields__type">integer</span></dt>
<dd>Opaque seq-based cursor for forward pagination.</dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">integer</span></dt>
<dd>Page size — range 1–1000, default 200.</dd>
</div>

</div>

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

<div className="stigmem-grid">

<div><h4><code>seq</code></h4><p>Monotonically increasing integer per database; use it as the <code>cursor</code> value for the next page.</p></div>
<div><h4><code>next_cursor</code></h4><p>Absent when the current page is the last page.</p></div>
<div><h4><code>detail</code></h4><p>JSON-encoded map of event-specific fields; schema varies by <code>event_type</code> (see Spec-09 event types).</p></div>

</div>

#### Tenant isolation

The API automatically scopes results to the caller's `tenant_id`.
Cross-tenant entries are never returned regardless of credentials.

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

### Audit event types

Sixteen event types are emitted to `fact_audit_log`. All are returned
by `GET /v1/admin/audit` unless filtered by `event_type`.

<div className="stigmem-fields">

<div>
<dt>Event type</dt>
<dt><span className="stigmem-fields__type">Trigger</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>fact_write</code></dt>
<dt><span className="stigmem-fields__type">mutation</span></dt>
<dd>Fact assertion or retraction.</dd>
</div>

<div>
<dt><code>fact_read</code></dt>
<dt><span className="stigmem-fields__type">query</span></dt>
<dd>Recall / query returning ≥ 1 fact.</dd>
</div>

<div>
<dt><code>capability_token_issue</code></dt>
<dt><span className="stigmem-fields__type">capability</span></dt>
<dd>Capability token issued.</dd>
</div>

<div>
<dt><code>capability_token_revoke</code></dt>
<dt><span className="stigmem-fields__type">capability</span></dt>
<dd>Capability token revoked.</dd>
</div>

<div>
<dt><code>manifest_publish</code></dt>
<dt><span className="stigmem-fields__type">federation</span></dt>
<dd>Org manifest updated.</dd>
</div>

<div>
<dt><code>key_rotation</code></dt>
<dt><span className="stigmem-fields__type">lifecycle</span></dt>
<dd>API key rotated.</dd>
</div>

<div>
<dt><code>federation_connect</code></dt>
<dt><span className="stigmem-fields__type">federation</span></dt>
<dd>Federation peer connection attempt.</dd>
</div>

<div>
<dt><code>quarantine_admit</code></dt>
<dt><span className="stigmem-fields__type">quarantine</span></dt>
<dd>Fact held in quarantine.</dd>
</div>

<div>
<dt><code>quarantine_release</code></dt>
<dt><span className="stigmem-fields__type">quarantine</span></dt>
<dd>Quarantined fact accepted or rejected.</dd>
</div>

<div>
<dt><code>quota_breach</code></dt>
<dt><span className="stigmem-fields__type">rate limit</span></dt>
<dd>Per-principal quota ceiling hit.</dd>
</div>

<div>
<dt><code>admin_action</code></dt>
<dt><span className="stigmem-fields__type">admin</span></dt>
<dd>Admin API call.</dd>
</div>

<div>
<dt><code>replay_rejected</code></dt>
<dt><span className="stigmem-fields__type">replay</span></dt>
<dd>Token replay nonce collision.</dd>
</div>

<div>
<dt><code>instruction_audit</code></dt>
<dt><span className="stigmem-fields__type">instruction</span></dt>
<dd>Lazy instruction chunk loaded.</dd>
</div>

<div>
<dt><code>instruction_quarantined</code></dt>
<dt><span className="stigmem-fields__type">instruction</span></dt>
<dd>Instruction-namespace fact placed in quarantine pending approval.</dd>
</div>

<div>
<dt><code>instruction_promoted</code></dt>
<dt><span className="stigmem-fields__type">instruction</span></dt>
<dd>Quarantined instruction-namespace fact promoted by an operator.</dd>
</div>

<div>
<dt><code>api_key_rehashed</code></dt>
<dt><span className="stigmem-fields__type">key migration</span></dt>
<dd>Legacy SHA-256 API key row migrated to Argon2id after successful authentication.</dd>
</div>

</div>

### Write-ahead ordering

<div className="stigmem-keypoint">

**Audit events are persisted before the HTTP response is sent.**

If the node crashes after writing the event but before responding, the
event is still in the log.

</div>

### Retention

<div className="stigmem-grid">

<div><h4>Operator minimum target</h4><p>90 days.</p></div>
<div><h4>Recommended for forensics</h4><p>1 year.</p></div>
<div><h4>Table is append-only</h4><p>Rows are never modified or purged by the node.</p></div>
<div><h4>No local 90-day enforcement</h4><p>Operators who must prove a retention window should keep the local database, signed snapshots, or immutable audit exports for at least that long.</p></div>

</div>

### Audit evidence posture by trust mode

`STIGMEM_TRUST_MODE` changes how strongly the node enforces federation
trust decisions, but it does not disable ordinary `fact_audit_log` or
`federation_audit` writes.

<div className="stigmem-fields">

<div>
<dt>Trust mode</dt>
<dt><span className="stigmem-fields__type">Enforcement</span></dt>
<dd>Audit evidence posture</dd>
</div>

<div>
<dt><code>strict</code></dt>
<dt><span className="stigmem-fields__type">fail closed</span></dt>
<dd>Federation trust decisions fail closed where required; low-trust or unverifiable inputs are rejected, quarantined, or downgraded. Best high-assurance mode. Preserve <code>fact_audit_log</code>, <code>federation_audit</code>, fact-chain checkpoints, and transparency-log evidence together.</dd>
</div>

<div>
<dt><code>relaxed</code></dt>
<dt><span className="stigmem-fields__type">warnings, not failures</span></dt>
<dd>Trust signals computed; warnings emitted; some paths accept data with warning evidence instead of failing closed. Suitable for staged federation rollout. Treat warnings as review items and export audit rows before local retention expiry.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">checks skipped</span></dt>
<dd>Source-trust scoring and related federation trust checks are skipped. Operational audit rows still exist, but trust-enforcement evidence is intentionally absent. Do not treat this as a production assurance posture.</dd>
</div>

</div>

For production deployments, use `STIGMEM_TL_BACKEND=rekor` when
available, or place the local transparency-log file on append-only
storage. Export both audit tables to WORM-capable storage on a
schedule that is shorter than your local retention target.

## Per-principal quotas (Spec-10-Hardening rate limits) \{#per-principal-quotas\}

### Model

Stigmem uses a **token-bucket** rate limiter, one bucket per
`(entity_uri, tenant_id, dimension)` triple. Every inbound request
consumes one token from the relevant dimension bucket. Tokens refill
continuously at a fixed rate up to the bucket capacity.

### The 7 dimensions and their defaults

<div className="stigmem-fields">

<div>
<dt>Dimension</dt>
<dt><span className="stigmem-fields__type">Capacity · Refill</span></dt>
<dd>Covers</dd>
</div>

<div>
<dt><code>fact_write</code></dt>
<dt><span className="stigmem-fields__type">100 · 10/s</span></dt>
<dd><code>POST /v1/facts</code>, <code>DELETE /v1/facts/&#42;</code></dd>
</div>

<div>
<dt><code>fact_read</code></dt>
<dt><span className="stigmem-fields__type">500 · 50/s</span></dt>
<dd><code>GET /v1/facts/&#42;</code>, <code>GET /v1/recall&#42;</code></dd>
</div>

<div>
<dt><code>token_issue</code></dt>
<dt><span className="stigmem-fields__type">20 · 0.33/s</span></dt>
<dd><code>POST /v1/federation/capability-tokens</code></dd>
</div>

<div>
<dt><code>federation_pull</code></dt>
<dt><span className="stigmem-fields__type">30 · 0.5/s</span></dt>
<dd>Outbound pull replication.</dd>
</div>

<div>
<dt><code>admin_action</code></dt>
<dt><span className="stigmem-fields__type">10 · 0.17/s</span></dt>
<dd><code>POST /v1/admin/&#42;</code></dd>
</div>

<div>
<dt><code>subscription_event</code></dt>
<dt><span className="stigmem-fields__type">200 · 20/s</span></dt>
<dd>Outbound subscription deliveries.</dd>
</div>

<div>
<dt><code>audit_export</code></dt>
<dt><span className="stigmem-fields__type">10,000 · 167/s</span></dt>
<dd>Rows returned by <code>GET /v1/admin/audit</code>.</dd>
</div>

</div>

Federation peer requests (using peer-token auth) and unauthenticated
health-check paths are exempt from quota.

### Tuning via environment variables

The legacy per-hour env vars control the effective rate for
`fact_write` and `fact_read`. At startup they are converted to
token-bucket parameters:

```
rate_per_second = ceiling / 3600
```

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Effect</dd>
</div>

<div>
<dt><code>STIGMEM_RATE_LIMIT_WRITE_PER_HOUR</code></dt>
<dt><span className="stigmem-fields__type"><code>1000</code></span></dt>
<dd>Sets <code>fact_write</code> refill rate.</dd>
</div>

<div>
<dt><code>STIGMEM_RATE_LIMIT_READ_PER_HOUR</code></dt>
<dt><span className="stigmem-fields__type"><code>5000</code></span></dt>
<dd>Sets <code>fact_read</code> refill rate.</dd>
</div>

</div>

```bash
# Example: allow 10,000 writes/hour for a high-throughput ingest node
STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=10000

# Disable quotas entirely (dev/test only — do not use in production)
STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=0
STIGMEM_RATE_LIMIT_READ_PER_HOUR=0
```

<div className="stigmem-keypoint">

**Never set quota env vars to `0` in production.**

It removes the per-principal backpressure that protects the node from
noisy neighbours and credential misuse. When both read and write
limits are <code>0</code>, Stigmem emits a startup
<code>SECURITY WARNING</code> because quota enforcement is disabled;
treat that warning as acceptable only in isolated local/dev/test
environments.

</div>

Bucket state (current tokens, last refill timestamp) is stored in the
`quota_buckets` SQLite table. It persists across restarts.

### 429 response shape and `Retry-After` semantics

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

The `Retry-After` header is set to the integer ceiling of
`retry_after` (seconds). Clients should honour it and not immediately
retry.

### `quota_breach` audit events

Every 429 response generates a `quota_breach` audit event **before**
the response is sent (write-ahead). The `detail` field contains:

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

## Operator checklist

### Audit key management

<ol className="stigmem-steps">
<li>Mint a dedicated <code>audit.read</code> key for each monitoring or SIEM consumer. Never reuse application keys for audit access — a compromised app key would also expose the audit trail.</li>
<li>Store audit keys in your secrets manager (Vault, AWS Secrets Manager, 1Password) with a rotation schedule.</li>
<li>If your SIEM supports it, configure it to pull from <code>/v1/admin/audit</code> on a schedule and forward <code>quota_breach</code> and <code>replay_rejected</code> events to your alerting pipeline.</li>
</ol>

### Retention

<ol className="stigmem-steps">
<li>Verify that <code>fact_audit_log</code> rows older than 90 days have not been deleted. The node does not auto-purge; implement retention via your own SQLite maintenance job or by exporting to cold storage.</li>
<li>For compliance use cases, export audit log rows to an immutable store (S3 Object Lock, GCS object versioning, WORM-enabled storage) before the 90-day window.</li>
</ol>

```sql
-- Check oldest event in the log
SELECT min(ts), count(*) FROM fact_audit_log;
```

### Prometheus metrics

When `prometheus_client` is installed, the node exposes a `/metrics`
endpoint with quota and audit counters.

<div className="stigmem-fields">

<div>
<dt>Metric</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>stigmem_quota_breach_total</code></dt>
<dt><span className="stigmem-fields__type">counter</span></dt>
<dd>By <code>(principal, tenant, dimension)</code>.</dd>
</div>

<div>
<dt><code>stigmem_audit_event_total</code></dt>
<dt><span className="stigmem-fields__type">counter</span></dt>
<dd>By <code>(event_type, tenant)</code>.</dd>
</div>

</div>

Install the optional dependency:

```bash
pip install prometheus_client
```

No additional configuration is required — the endpoint is registered
automatically if the package is importable at startup.

### Quota baselines

<ol className="stigmem-steps">
<li>After 24 hours of representative traffic, query <code>quota_breach</code> events and identify principals that breach repeatedly. Increase <code>STIGMEM_RATE_LIMIT_WRITE_PER_HOUR</code> / <code>STIGMEM_RATE_LIMIT_READ_PER_HOUR</code> if defaults are too tight for legitimate workloads, or investigate the offending principal.</li>
<li>Set a Prometheus alert on <code>stigmem_quota_breach_total</code> to catch runaway clients before they degrade the node for other principals.</li>
</ol>

## Related

<div className="stigmem-next">

<a href="./mtls">
<strong>Security</strong>
<span>mTLS federation transport</span>
<small>Spec-10-Hardening transport layer.</small>
</a>

<a href="./key-rotation">
<strong>Security</strong>
<span>Key rotation</span>
<small>Spec-10-Hardening lifecycle runbooks.</small>
</a>

<a href="../operators/observability/monitoring">
<strong>Operators</strong>
<span>Monitoring</span>
<small>Prometheus metrics, structured logs, health endpoints.</small>
</a>

</div>
