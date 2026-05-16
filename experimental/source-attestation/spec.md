---
spec_id: Spec-X6-Source-Attestation
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: pre-reset section 18 source-attestation material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
title: Spec-X6-Source-Attestation
sidebar_label: Source Attestation
audience: Spec
description: "API-key to entity_uri binding with enforce/warn/off modes; trust anchor for connectors."
---

# Spec-X6-Source-Attestation: Source Attestation {#section-18}

**Status:** Normative (v1.0)

API-key → entity_uri binding with enforce/warn/off modes; trust anchor for connectors.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

### Spec-X6-Source-Attestation section 1 Motivation {#section-18-1}

In the pre-reset source-attestation design, the `source` field in a fact request body is caller-declared:

```json
{ "entity": "...", "relation": "...", "source": "stigmem://node/user/alice", ... }
```

Nothing prevents an `agent:assistant` principal from writing `"source": "stigmem://node/user/bob"`. The stored fact will falsely attribute its origin to Bob. This undermines:
- Audit trails (who actually wrote this fact?)
- Trust scoring (confidence in a fact depends on who asserted it)
- Track C's keypair-signed attribution model

Source attestation closes this gap by binding `source` to the verified `entity_uri` from the auth principal at write time.

### Spec-X6-Source-Attestation section 2 Attestation Model {#section-18-2}

When a fact is asserted with auth enabled, the node:

1. Resolves the key's registered `entity_uri` and `allowed_source_entities` (Spec-X6-Source-Attestation section 7).
2. Normalizes `fact.source` and all entries in the authorized set using Spec-01-Fact-Model URI normalization.
3. Checks:

```
attested = normalized(fact.source) ∈ { normalized(identity.entity_uri) } ∪ normalized(identity.allowed_source_entities)
```

If `source` is absent from the request and the key has a registered `entity_uri`, the node auto-fills `source` from `key.entity_uri` before the check (Spec-X6-Source-Attestation section 8). The auto-filled value is returned in the response.

The result is stored as the `attested` column on the fact record (see Spec-X6-Source-Attestation attestation field). The behavior on mismatch depends on the node's configured `SourceAttestationMode`:

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

**`enforce` mode:**
- Any `source` outside `{entity_uri} ∪ allowed_source_entities` causes HTTP 403:
  ```json
  { "error": "source_attestation_failed",
    "detail": "source URI must equal the authenticated principal's entity_uri or delegation list" }
  ```
- `attested: true` on all accepted facts.

**`warn` mode (default):**
- Mismatch logged to stderr: `[stigmem] WARN: source attestation mismatch — declared source=X, identity=Y`.
- Fact accepted with `attested: false`.
- `attested: true` if source matches.

**`off` mode:**
- No check. `attested: null` on all facts.

### Spec-X6-Source-Attestation section 3 Well-Known Advertisement {#section-18-3}

Nodes MUST advertise their attestation mode at `/.well-known/stigmem`:

```json
{
  ...existing fields...,
  "source_attestation": "enforce" | "warn" | "off"
}
```

Clients SHOULD read this before writing to understand whether their `source` claim will be enforced.

### Spec-X6-Source-Attestation section 4 Attestation and Retraction {#section-18-4}

A retraction (fact with `confidence=0.0`) is subject to the same attestation rules as any other fact write. If the node is in `enforce` mode and the caller's identity differs from the `source` field in the retraction body, the retraction is rejected with `HTTP 403`.

**Implication:** A fact written by `agent:assistant` can only be retracted by `agent:assistant` in `enforce` mode (since the source must match the caller). If the original writer is no longer available, node admins must temporarily set `warn` or `off` mode to perform administrative retractions.

### Spec-X6-Source-Attestation section 5 Integration with Track C (Per-Agent Keypairs) {#section-18-5}

Track C adds per-agent keypair registration. Once an agent's public key is registered on the node, a stronger form of attestation becomes possible: the agent signs the fact payload before submission, and the node verifies the signature against the registered public key. This moves attestation from "bearer-token-level" (who presented this API key?) to "fact-level" (who signed this specific fact payload?).

Source attestation is a first step. `attested: true` means the bearer-token-level check passed. Track C extends this with a separate `signature_verified: true | false | null` field once keypairs are implemented.


### Spec-X6-Source-Attestation section 6 Querying by Attestation {#section-18-6}

Facts can be filtered by attestation status:

```
GET /v1/facts?attested=true    // only source-attested facts
GET /v1/facts?attested=false   // only non-attested facts (warn/off mode)
```

The `attested` query parameter is optional. Omitting it returns all facts.

### Spec-X6-Source-Attestation section 7 Key Registration: Binding `entity_uri` to an API Key {#section-18-7}

Source attestation depends on the node knowing the caller's authorized `entity_uri`. This binding is established at **key creation time** and is immutable — a key's `entity_uri` cannot be changed after creation (to prevent retroactive provenance forgery).

#### `entity_uri` requirements

- MUST be a formal URI matching the `stigmem://` scheme (Spec-01-Fact-Model entity URI scheme). Informal URIs are rejected at key creation.
- MUST be unique within the node's `api_keys` table (one key per entity).
- Stored in normalized form (Spec-01-Fact-Model URI normalization) to align with ingest normalization.

#### Key creation

A key is created with a single POST that binds the `entity_uri`, scope
permissions, and optional delegation list at creation time. The node returns
the raw API key exactly once in the response; only its SHA-256 digest is
stored server-side. The `entity_uri` is immutable after creation to prevent
retroactive re-attribution of facts already written with this key.

```
POST /v1/auth/keys
Authorization: Bearer <admin-key>
{
  "description":             "CTO agent key",
  "entity_uri":              "stigmem://company.example/agent/cto",
  "allowed_scopes":          ["company", "public"],
  "allowed_source_entities": []
}
→ 201 {
    "key_id":                  "<uuid>",
    "raw_key":                 "<secret>",   // shown once; SHA-256 stored
    "entity_uri":              "stigmem://company.example/agent/cto",
    "allowed_scopes":          ["company","public"],
    "allowed_source_entities": [],
    "created_at":              "2026-05-03T00:00:00Z"
  }
```

The caller MUST store `raw_key` securely — it is not retrievable after creation. The node stores only the SHA-256 hex digest.

**Creating a key without `entity_uri`** is allowed for backward compatibility. Such a key can still write facts; in `enforce` mode it will be rejected (HTTP 400 `key_not_attested`); in `warn` mode writes are accepted with `attested: false`.

**Immutability:** Nodes MUST NOT allow `entity_uri` to be updated via `PATCH`. Attempting to update it returns HTTP 422:

```json
{ "error": "immutable_field",
  "detail": "entity_uri cannot be changed after creation; revoke and re-create the key" }
```

#### Updated `Identity` shape

The `Identity` shape extends the authenticated identity shape with the `allowed_source_entities`
field needed for delegation (Spec-X6-Source-Attestation section 9). This is the object the node constructs
from the API key record when authenticating a request — it drives every
attestation check in the write path.

```
Identity {
  entity_uri:              URI            // registered at key creation; enforced against fact.source
  credential:              string         // API key (SHA-256 stored server-side)
  node_url:                string
  allowed_scopes:          FactScope[]
  allowed_source_entities: URI[]          // additional source URIs this key may claim (see Spec-X6-Source-Attestation section 9)
}
```

#### Updated attestation check (Spec-X6-Source-Attestation section 2 with delegation)

The check in Spec-X6-Source-Attestation section 2 is updated to include the delegation list:

```
attested = normalized(fact.source) ∈ { normalized(identity.entity_uri) } ∪ normalized(identity.allowed_source_entities)
```

All normalization uses Spec-01-Fact-Model URI normalization. Delegation set entries are stored in normalized form at key creation.


### Spec-X6-Source-Attestation section 8 Source Auto-fill {#section-18-8}

If the `source` field is absent from a `POST /v1/facts` request body and the presenting key has a registered `entity_uri`, the node MUST auto-fill `source` from `key.entity_uri`. The auto-filled value MUST appear in the response body.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value":  { "type": "string", "v": "CEO" },
  "confidence": 1.0, "scope": "company" }
  // source omitted

→ 201 { ..., "source": "stigmem://company.example/agent/cto", "attested": true }
```

If `source` is absent and the key has **no registered `entity_uri`**:

| Mode | Behaviour |
|---|---|
| `enforce` | HTTP 400: `{ "error": "source_required", "detail": "source is required when key has no entity_uri in enforce mode" }` |
| `warn` | Accept; include `X-Stigmem-Warn: source_unattested` in response; `attested: false`. |
| `off` | Accept; `attested: null`. |

### Spec-X6-Source-Attestation section 9 Delegation via `allowed_source_entities` {#section-18-9}

Some adapters write facts on behalf of other principals. The Paperclip hook, for example, writes facts with `source="stigmem://company.example/agent/cto"` while running inside an agent's context — but the adapter's own key may be bound to `stigmem://company.example/adapter/paperclip`.

A key's `allowed_source_entities` is an explicit allowlist of additional URIs the key is authorized to claim as `source`:

```json
{
  "entity_uri":              "stigmem://company.example/adapter/paperclip",
  "allowed_source_entities": [
    "stigmem://company.example/agent/cto",
    "stigmem://company.example/agent/qa"
  ]
}
```

This key may write facts with `source` equal to any of: the adapter itself, the CTO agent, or the QA agent. Any other `source` claim is rejected (HTTP 403 `source_attestation_failed`).

**Delegation is not transitive.** If key K1 (entity E1) has E2 in `allowed_source_entities`, K1 can claim E1 or E2, but this grants K1 no rights to entities that E2's own key delegates.

**Default:** `allowed_source_entities` defaults to `[]`. Every delegation must be an explicit operator grant.

### Spec-X6-Source-Attestation section 10 Full Key Management API {#section-18-10}

All key management routes require a key with `admin=true`. The key management
API covers the full lifecycle: creation, inspection, scope/delegation updates,
and revocation. Revocation is a soft delete — the key record is retained with a
`revoked_at` timestamp for audit purposes, but all subsequent authentication
attempts with the revoked key are rejected. A separate attestation-audit
endpoint provides a searchable event log of every attestation decision the node
has made, filterable by key, outcome, and time.

```
POST   /v1/auth/keys                             // create key
GET    /v1/auth/keys                             // list all keys
GET    /v1/auth/keys/:key_id                     // get key metadata
PATCH  /v1/auth/keys/:key_id                     // update description, allowed_scopes, allowed_source_entities
DELETE /v1/auth/keys/:key_id                     // revoke key (sets revoked_at; record retained for audit)

GET    /v1/auth/attestation-audit                // attestation event log (admin only)
```

`PATCH` request body may include `description`, `allowed_scopes`, `allowed_source_entities`. `entity_uri` and `admin` are immutable after creation.

The attestation audit endpoint returns a paginated log of every attestation
decision the node has made. Each event records the key that was used, the
`source` value the caller claimed, whether attestation passed, and — when it
failed — the specific rejection reason. This log is essential for operators
transitioning from `warn` to `enforce` mode: querying for `attested=false`
events surfaces all callers that would break under strict enforcement.

```
GET /v1/auth/attestation-audit?key_id=<id>&attested=false&limit=50
→ 200 {
    "events": [{
      "id":              "<uuid>",
      "key_id":          "...",
      "entity_uri":      "...",           // key's registered entity_uri; null for legacy keys
      "claimed_source":  "...",           // source value from the request
      "attested":        true | false,
      "rejection_reason": null | "source_attestation_failed" | "source_required" | "key_not_attested",
      "ts":              "2026-05-03T00:00:00Z"
    }],
    "cursor": "...", "has_more": false
  }
```

Filter params: `key_id`, `attested` (true/false), `after` (pagination cursor), `limit` (max 500).


### Spec-X6-Source-Attestation section 11 Schema Migration (Migration 005) {#section-18-11}

Migration 005 adds two tables to support source attestation. The `api_keys`
table formalizes key storage that was previously external to the database,
binding each key to an `entity_uri` and carrying its scope permissions and
delegation list. The `attestation_audit` table provides the append-only event
log queried by the admin audit endpoint (Spec-X6-Source-Attestation section 10). Both tables are additive and
do not alter the existing `facts` schema — the `attested` column on `facts`
was already added in Spec-X6-Source-Attestation attestation field.

```sql
-- API key management (Spec-X6-Source-Attestation.7)
CREATE TABLE IF NOT EXISTS api_keys (
  id                      TEXT PRIMARY KEY,
  description             TEXT,
  credential_hash         TEXT NOT NULL UNIQUE,     -- SHA-256 hex of raw key
  entity_uri              TEXT,                     -- formal URI; NULL for legacy keys
  allowed_scopes          TEXT NOT NULL DEFAULT '["local","team","company","public"]',
  allowed_source_entities TEXT NOT NULL DEFAULT '[]', -- JSON array; stored in normalized form
  admin                   INTEGER NOT NULL DEFAULT 0,
  created_at              TEXT NOT NULL,
  revoked_at              TEXT                      -- NULL if active
);

CREATE INDEX IF NOT EXISTS idx_api_keys_credential ON api_keys(credential_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_entity_uri ON api_keys(entity_uri);

-- Attestation audit log (Spec-X6-Source-Attestation.10)
CREATE TABLE IF NOT EXISTS attestation_audit (
  id               TEXT PRIMARY KEY,
  key_id           TEXT NOT NULL REFERENCES api_keys(id),
  entity_uri       TEXT,
  claimed_source   TEXT NOT NULL,
  attested         INTEGER NOT NULL,      -- 1=true, 0=false
  rejection_reason TEXT,
  ts               TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attestation_audit_key_ts   ON attestation_audit(key_id, ts);
CREATE INDEX IF NOT EXISTS idx_attestation_audit_attested ON attestation_audit(attested, ts);
```

**Migration note for existing deployments:** Older nodes may manage API keys outside the database. Migration 005 formalizes key storage. Operators MUST:
1. Register existing keys via `POST /v1/auth/keys` using an `existing_credential` migration field (accepted for 30 days post-deploy).
2. Set `STIGMEM_SOURCE_ATTESTATION_MODE=warn` initially.
3. Register `entity_uri` for all keys, then switch to `enforce` after verifying the audit log shows no `attested=false` writes.

### Spec-X6-Source-Attestation section 12 Error Reference {#section-18-12}

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `source_required` | `source` omitted; key has no `entity_uri`; `enforce` mode |
| 400 | `key_not_attested` | Key has no `entity_uri`; node requires attestation |
| 403 | `source_attestation_failed` | `source` not in `{entity_uri} ∪ allowed_source_entities` |
| 422 | `immutable_field` | Attempt to PATCH `entity_uri` or `admin` |

---
