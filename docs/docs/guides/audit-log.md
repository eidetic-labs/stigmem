---
id: audit-log
title: Audit Log
sidebar_label: Audit Log
---

# Audit Log

**Audience:** Node operators and security engineers who need an end-to-end trace linking asserted facts back to verified principals.

Track C — C3 exposes a joined audit surface that answers: _who_ (principal) used _which credential_ (attested source) to assert _which fact_ (fact-id), and when.

Every call to `POST /v1/facts` writes an entry to `fact_audit_log`. The audit endpoints join that table against `agent_keys` and `facts` so you get the full identity trail in a single query.

---

## Identity trail model

```
principal (entity_uri, oidc_sub)
  └── attested_key_id → agent_keys(entity_uri, description)
        └── fact_id → facts(entity, relation, value, scope)
```

- **principal** — the authenticated caller's `entity_uri` (e.g. `oidc:alice@example.com`, `agent:my-service`) and `oidc_sub` if the key was issued via the OIDC bridge.
- **attested key** — the registered Ed25519 key that signed this assertion. `null` for unattested writes.
- **fact** — the entity/relation/value triple stored in the fact store.

---

## Endpoints

### GET /v1/audit — paginated audit log

Query the enriched audit log with optional filters.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_uri` | string | Filter by asserting principal |
| `oidc_sub` | string | Filter by OIDC subject claim |
| `source` | string | Filter by fact `source` field |
| `fact_id` | string | Filter to entries for a specific fact |
| `attested` | bool | `true` = attested entries only; `false` = unattested only |
| `cursor` | string | Opaque pagination cursor from a previous response |
| `limit` | int | Page size (default 50, max 500) |

Results are ordered `ts DESC, id DESC` (newest first). For oldest-first streaming, use `GET /v1/audit/export`.

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

`attested_key_entity_uri` and `attested_key_description` are `null` when the entry is unattested.

**`curl` example:**

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

---

### GET /v1/audit/facts/\{fact\_id\} — trail for a single fact

Returns all audit entries for a specific fact, oldest first. Useful for tracing the full assert/retract history of one fact including every principal that touched it.

```bash
curl -s "http://localhost:8000/v1/audit/facts/<fact-id>" \
  -H 'Authorization: Bearer stgm_...' | jq .
# → array of enriched AuditLogEntry objects, ASC order
```

Returns `404` if the fact does not exist. Returns an empty array `[]` if the fact exists but has no audit entries (possible for facts that predate Track C).

---

### GET /v1/audit/export — CSV compliance export

Streams a CSV with all join columns for SIEM import or compliance archival. Supports the same filters as `GET /v1/audit`. Default limit is 5000 rows; maximum is 50000.

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

---

## Retention and backfill

Facts asserted before Track C landed do not have audit entries. The `fact_audit_log` table was created by migration `006_fact_audit.sql` — all entries with `ts` prior to that migration date are absent.

Retention policy (log rotation / archival) is not yet implemented; all entries accumulate indefinitely. Set up external archival if you need bounded storage.

---

## Web UI

The Audit Log tab in the browser UI (`/` on the node) shows the same joined view with filters for principal, source, and attestation status. The **Export CSV** button triggers `GET /v1/audit/export` with any active filters applied.

---

## See also

- [Agent Keypairs](./agent-keypairs) — C1: registering keys and signing fact assertions
- [Human Key Issuance](./human-key-issuance) — C2: how OIDC principals and garden roles flow into `entity_uri`
- [Authentication](./authentication) — Bearer-key model and permissions
- [OIDC / SSO Integration](./oidc-sso) — OIDC bridge that populates `oidc_sub`
