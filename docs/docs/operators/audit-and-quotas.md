---
id: audit-and-quotas
title: Audit Log & Quotas — Operator Quick-Start
sidebar_label: Audit & Quotas
description: Operator quick-start for the audit log and per-principal quotas introduced in Phase 12 (spec §22.3–§22.4).
---

# Audit Log & Quotas — Operator Quick-Start

**Audience:** node operators setting up audit access and tuning quota limits for production deployments.  
**Spec:** §22.3 (Audit Log), §22.4 (Per-Principal Quotas).  
**Full reference:** [Security — Audit Log & Per-Principal Quotas](../security/audit-and-quotas.md)

---

## Quick setup

### 1. Mint an audit.read key

```bash
curl -s -X POST https://your-node.example.com/v1/admin/api-keys \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_uri": "stigmem://your-org.example.com/siem-reader",
    "permissions": ["audit.read"]
  }' | jq '.key'
# → "stgm_..."  Store this in your secrets manager.
```

### 2. Tail recent events

```bash
curl -s "https://your-node.example.com/v1/admin/audit?limit=50" \
  -H "Authorization: Bearer $AUDIT_KEY" \
  | jq '.entries[] | {ts, event_type, principal: .entity_uri}'
```

### 3. Set quota ceilings (optional)

```bash
# Increase write throughput for a high-ingest node
export STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=10000
export STIGMEM_RATE_LIMIT_READ_PER_HOUR=50000
```

Restart the node for the new values to take effect.  The defaults (1 000 writes/hour, 5 000 reads/hour) are intentionally conservative — adjust upward once you have baseline traffic data.

---

## Operator checklist

- [ ] Dedicated `audit.read` key minted and stored in secrets manager.
- [ ] SIEM or log pipeline configured to pull from `/v1/admin/audit` on a schedule.
- [ ] Prometheus alert on `stigmem_quota_breaches_total` (install `prometheus_client` to enable the `/metrics` endpoint).
- [ ] Retention plan in place — the node does not auto-purge `fact_audit_log`. Minimum retention: 90 days (§22.3.3).
- [ ] Quota ceilings reviewed after 24 h of representative traffic; offending principals investigated.

---

## Related pages

| Topic | Page |
|---|---|
| Full audit log reference (event types, pagination, schema) | [Audit Log & Per-Principal Quotas](../security/audit-and-quotas.md) |
| mTLS federation transport | [mTLS](../security/mtls.md) |
| Key rotation runbook | [Key Rotation](../security/key-rotation.md) |
| Container hardening | [Container Hardening](./container-hardening.md) |
| Monitoring (Prometheus metrics) | [Monitoring](../operating/monitoring.md) |
