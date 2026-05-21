---
title: Audit Log
sidebar_label: Audit Log
audience: Integrator
---

# Audit Log

<p className="stigmem-meta"><span>4 min read</span><span>Node operators · Security engineers</span><span>Track C · C3</span></p>

<div className="stigmem-lead">

**What this page is**

Track C — C3 exposes a joined audit surface that answers: *who*
(principal) used *which credential* (attested source) to assert
*which fact* (fact-id), and when.

</div>

Every call to `POST /v1/facts` writes an entry to `fact_audit_log`.
The audit endpoints join that table against `agent_keys` and `facts`
so you get the full identity trail in a single query.

## Identity trail model

```
principal (entity_uri, oidc_sub)
  └── attested_key_id → agent_keys(entity_uri, description)
        └── fact_id → facts(entity, relation, value, scope)
```

<div className="stigmem-fields">

<div>
<dt>Layer</dt>
<dt><span className="stigmem-fields__type">Identity</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt>principal</dt>
<dt><span className="stigmem-fields__type"><code>entity_uri</code> + <code>oidc_sub</code></span></dt>
<dd>The authenticated caller (e.g., <code>oidc:alice@example.com</code>, <code>agent:my-service</code>); <code>oidc_sub</code> populated when the key was issued via OIDC.</dd>
</div>

<div>
<dt>attested key</dt>
<dt><span className="stigmem-fields__type">Ed25519 registered key</span></dt>
<dd>The key that signed this assertion. <code>null</code> for unattested writes.</dd>
</div>

<div>
<dt>fact</dt>
<dt><span className="stigmem-fields__type">entity/relation/value</span></dt>
<dd>The triple stored in the fact store.</dd>
</div>

</div>

## Endpoints

### `GET /v1/audit` · paginated audit log

Query the enriched audit log with optional filters.

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>entity_uri</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter by asserting principal.</dd>
</div>

<div>
<dt><code>oidc_sub</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter by OIDC subject claim.</dd>
</div>

<div>
<dt><code>source</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter by fact <code>source</code> field.</dd>
</div>

<div>
<dt><code>fact_id</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Filter to entries for a specific fact.</dd>
</div>

<div>
<dt><code>attested</code></dt>
<dt><span className="stigmem-fields__type">bool</span></dt>
<dd><code>true</code> = attested entries only; <code>false</code> = unattested only.</dd>
</div>

<div>
<dt><code>cursor</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Opaque pagination cursor from a previous response.</dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">int</span></dt>
<dd>Page size (default 50, max 500).</dd>
</div>

</div>

Results are ordered `ts DESC, id DESC` (newest first). For
oldest-first streaming, use `GET /v1/audit/export`.

**Response (200 OK):**

```json
{
  "entries": [
    {
      "id": "uuid",
      "fact_id": "uuid",
      "event_type": "assert",
      "entity_uri": "oidc:alice@example.com",
      "oidc_sub": "108...",
      "source": "agent:coding-assistant",
      "attested_key_id": "uuid-or-null",
      "ts": "2026-05-03T01:00:00Z",
      "attested_key_entity_uri": "agent:coding-assistant",
      "attested_key_description": "prod keypair",
      "fact_entity": "user:alice",
      "fact_relation": "memory:context",
      "fact_value_type": "str",
      "fact_value_v": "working on stigmem docs",
      "fact_scope": "local"
    }
  ],
  "total": 1,
  "cursor": null
}
```

`attested_key_entity_uri` and `attested_key_description` are `null`
when the entry is unattested.

**Examples:**

```bash
# All entries for a specific principal
curl -s "http://localhost:8000/v1/audit?entity_uri=oidc:alice@example.com&limit=20" \
  -H 'Authorization: Bearer stgm_...' | jq .

# Only attested writes
curl -s "http://localhost:8000/v1/audit?attested=true" \
  -H 'Authorization: Bearer stgm_...' | jq '.entries[] | {entity_uri, source, fact_entity}'

# Paginate
curl -s "http://localhost:8000/v1/audit?cursor=<cursor-from-previous>" \
  -H 'Authorization: Bearer stgm_...' | jq .
```

### `GET /v1/audit/facts/{fact_id}` · trail for a single fact

Returns all audit entries for a specific fact, oldest first. Useful
for tracing the full assert/retract history of one fact including
every principal that touched it.

```bash
curl -s "http://localhost:8000/v1/audit/facts/<fact-id>" \
  -H 'Authorization: Bearer stgm_...' | jq .
# → array of enriched AuditLogEntry objects, ASC order
```

Returns `404` if the fact does not exist. Returns an empty array `[]`
if the fact exists but has no audit entries (possible for facts that
predate Track C).

### `GET /v1/audit/export` · CSV compliance export

Streams a CSV with all join columns for SIEM import or compliance
archival. Supports the same filters as `GET /v1/audit`. Default limit
is 5000 rows; maximum is 50000.

```bash
curl -s "http://localhost:8000/v1/audit/export" \
  -H 'Authorization: Bearer stgm_...' \
  -o stigmem-audit.csv

# Filtered export: one principal, last 7 days
curl -s "http://localhost:8000/v1/audit/export?entity_uri=oidc:alice@example.com&limit=10000" \
  -H 'Authorization: Bearer stgm_...' \
  -o alice-audit.csv
```

**CSV columns:**

```
id, fact_id, event_type,
principal_entity_uri, principal_oidc_sub,
source,
attested_key_id, attested_key_entity_uri, attested_key_description,
fact_entity, fact_relation, fact_value_type, fact_value_v, fact_scope,
ts
```

## Tenant scoping

<div className="stigmem-keypoint">

**Audit entries are automatically scoped to the caller's tenant.**

A key provisioned for tenant <code>"acme"</code> can only query audit
entries where <code>tenant_id = 'acme'</code> — cross-tenant audit
data is never returned, even with node-admin permissions.

</div>

This scoping was added in migration `012_multi_tenant.sql`. Rows
written before that migration carry `tenant_id = 'default'`. See
[Multi-Tenant Scoping](https://github.com/eidetic-labs/stigmem/tree/main/features/multi-tenant)
for the full isolation model.

## Retention and backfill

<div className="stigmem-grid">

<div><h4>Pre-Track-C facts have no entries</h4><p>The <code>fact_audit_log</code> table was created by migration <code>006_fact_audit.sql</code> — entries with <code>ts</code> prior to that migration date are absent.</p></div>
<div><h4>No automatic retention</h4><p>Log rotation / archival is not yet implemented; all entries accumulate indefinitely. Set up external archival if you need bounded storage.</p></div>

</div>

## Web UI

The Audit Log tab in the browser UI (`/` on the node) shows the same
joined view with filters for principal, source, and attestation
status. The **Export CSV** button triggers `GET /v1/audit/export`
with any active filters applied.

## See also

<div className="stigmem-next">

<a href="./agent-keypairs">
<strong>Security</strong>
<span>Agent keypairs</span>
<small>C1: registering keys and signing fact assertions.</small>
</a>

<a href="./human-key-issuance">
<strong>Security</strong>
<span>Human key issuance</span>
<small>C2: OIDC principals and garden roles → <code>entity_uri</code>.</small>
</a>

<a href="./authentication">
<strong>Security</strong>
<span>Authentication</span>
<small>Bearer-key model and permissions.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/features/multi-tenant">
<strong>Experimental</strong>
<span>Multi-tenant scoping</span>
<small><code>tenant_id</code> isolation model and migration 012.</small>
</a>

</div>
