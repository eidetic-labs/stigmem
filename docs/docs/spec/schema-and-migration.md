---
title: Spec-17 Schema and Migration
sidebar_label: Spec-17 Schema and Migration
audience: Spec
description: "Spec-17-Schema-and-Migration rendered entry point — schema, migrations, indexes, and backend contract."
---

# Spec-17-Schema-and-Migration \{#section-10\}

<p className="stigmem-meta"><span>4 min read</span><span>Spec contributor · Implementer</span><span>SQL migrations 001–013</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-17-Schema-and-Migration`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/17-schema-and-migration.md).
SQL schema migrations covering facts, federation, gardens,
attestation, tombstones.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source. Legacy §10 anchors are retained for existing links
while the maintained schema contract lives in
`Spec-17-Schema-and-Migration`.
:::

### Migration 004 — gardens and source attestation

```sql
-- gardens table (§17)
CREATE TABLE IF NOT EXISTS gardens (
    id          TEXT PRIMARY KEY,
    slug        TEXT NOT NULL,           -- URL-safe identifier; e.g. "project-atlas"
    name        TEXT NOT NULL,
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public')),
    description TEXT,
    created_by  TEXT NOT NULL,           -- entity_uri of creator
    created_at  TEXT NOT NULL,
    UNIQUE(slug)
);

-- garden_members table (§17.2)
CREATE TABLE IF NOT EXISTS garden_members (
    garden_id   TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    entity_uri  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin','writer','reader')),
    added_by    TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    PRIMARY KEY (garden_id, entity_uri)
);

CREATE INDEX IF NOT EXISTS idx_garden_members_entity ON garden_members(entity_uri);

-- Add garden_id column to facts (NULL for pre-the pre-reset spec facts)
ALTER TABLE facts ADD COLUMN garden_id TEXT;
CREATE INDEX IF NOT EXISTS idx_facts_garden ON facts(garden_id) WHERE garden_id IS NOT NULL;

-- Add attested column to facts (NULL for pre-the pre-reset spec facts)
ALTER TABLE facts ADD COLUMN attested INTEGER;  -- 1=true, 0=false, NULL=not-applicable
```

<div className="stigmem-keypoint">

**Backward compatibility.**

Pre-the pre-reset spec facts have <code>garden_id = NULL</code> (no
garden) and <code>attested = NULL</code> (attestation not
applicable). Both columns are nullable by design.

</div>

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

Production nodes SHOULD use a migration-versioned schema. The reference
implementation uses numbered SQL migration files applied at startup. Each
migration is additive — columns are added, never removed, and new tables do not
alter existing ones — so that a node can be upgraded in place without data loss.
The sections below show the cumulative schema across spec versions: the
original v0.4 `facts` table, then the federation and data-quality tables added
in pre-reset, the entity-alias table from pre-reset, and the scope-propagation columns
from the pre-reset spec.

### Existing tables (v0.4, unchanged)

The `facts` table is the single source of truth for all assertions in a
Stigmem node. Each row is an immutable fact record whose columns map directly
to the atomic fact shape defined in §2. The table is append-only: retractions,
confidence updates, and conflict resolutions are all expressed as new rows
rather than mutations to existing ones.

```sql
facts (
  id          TEXT PRIMARY KEY,
  entity      TEXT NOT NULL,
  relation    TEXT NOT NULL,
  value_type  TEXT NOT NULL,
  value_v     TEXT NOT NULL,
  source      TEXT NOT NULL,
  timestamp   TEXT NOT NULL,
  valid_until TEXT,
  confidence  REAL NOT NULL,
  scope       TEXT NOT NULL
)
```

**Required indexes:** `(entity, relation)`, `(entity, relation, scope)`, `scope`, `timestamp`.

### New columns — migration 002 (pre-reset)

Federation (§6) requires two pieces of per-fact metadata that the v0.4 schema
did not carry. `hlc` stores the hybrid logical clock timestamp used for
cursor-based replication ordering (§5.8) — it is `NULL` for facts created
before pre-reset. `received_from` records the `node_id` of the peer that delivered
the fact; it is `NULL` for locally-asserted facts. Together these columns let
the node distinguish local assertions from federated ones and provide a total
order for pull replication.

```sql
ALTER TABLE facts ADD COLUMN hlc           TEXT;          -- HLC timestamp; NULL for pre-pre-reset facts
ALTER TABLE facts ADD COLUMN received_from TEXT;          -- node_id if federated; NULL if local
```

### New tables — migration 002 (pre-reset)

Migration 002 introduces four tables that support the federation and
data-quality features added in pre-reset.

**`peers`** stores the bilateral peer declarations described in §6.1. Each row
represents one direction of a federation relationship: the remote node's
identity, its Ed25519 public key, the scopes it is allowed to replicate, and
the lifecycle status of the declaration.

**`replication_cursors`** tracks the HLC watermark for each peer in each
direction (inbound and outbound). The cursor is the opaque token returned by
pull replication (§5.8); persisting it lets the node resume replication from
where it left off after a restart.

**`conflicts`** records pairs of facts that the conflict detector (§7) flagged
as contradictory. The table carries references to both original facts and the
resolution fact (if any), enabling an audit trail for every resolution decision.

**`federation_audit`** is an append-only security log. Every rejected fact,
rejected token, scope violation, or replay attempt during federation is
recorded here so that operators can diagnose trust failures and detect
misbehaving peers.

**`nonce_cache`** prevents replay attacks on federation tokens (§3). Each nonce
is stored with its expiry time; a background pruning job removes expired entries.

```sql
peers (
  id              TEXT PRIMARY KEY,       -- uuid
  node_id         TEXT NOT NULL UNIQUE,   -- peer's stable URI
  node_url        TEXT NOT NULL,
  federation_pubkey TEXT NOT NULL,        -- base64url Ed25519
  allowed_scopes  TEXT NOT NULL,          -- JSON array
  status          TEXT NOT NULL,          -- pending_verification | active | rejected | revoked
  established_at  TEXT,                   -- ISO 8601; set when status→active
  declaration_sig TEXT NOT NULL,
  signed_at       TEXT NOT NULL
)

replication_cursors (
  peer_id         TEXT NOT NULL REFERENCES peers(id),
  direction       TEXT NOT NULL,          -- "inbound" | "outbound"
  cursor          TEXT,                   -- opaque HLC string; NULL = start from beginning
  updated_at      TEXT NOT NULL,
  PRIMARY KEY (peer_id, direction)
)

conflicts (
  id              TEXT PRIMARY KEY,       -- "stigmem:conflict:<uuid>"
  fact_a_id       TEXT NOT NULL REFERENCES facts(id),
  fact_b_id       TEXT NOT NULL REFERENCES facts(id),
  status          TEXT NOT NULL DEFAULT 'unresolved',
  resolution_fact_id TEXT,
  detected_at     TEXT NOT NULL
)

federation_audit (
  id              TEXT PRIMARY KEY,
  peer_id         TEXT NOT NULL,
  event_type      TEXT NOT NULL,          -- "rejected_fact" | "rejected_token" | "scope_violation" | "replay_attempt"
  detail          TEXT,                   -- JSON blob with fact_id, reason, etc.
  ts              TEXT NOT NULL
)

nonce_cache (
  nonce           TEXT PRIMARY KEY,
  peer_id         TEXT NOT NULL,
  expires_at      TEXT NOT NULL           -- prune when expires_at < now
)
```

**Indexes to add:**
- `conflicts(status)` for unresolved-conflict queries
- `federation_audit(peer_id, ts)` for audit queries
- `nonce_cache(expires_at)` for TTL pruning
- `facts(hlc)` for cursor-based replication queries
- `facts(received_from)` for provenance queries

### New tables — migration 003 (pre-reset)

The pre-reset entity normalizer (§2.6) ensures that all new facts use canonical
URIs, but facts created before pre-reset may contain non-canonical forms (e.g.
mixed-case or trailing-slash variants). The `entity_aliases` table maps each
raw, non-canonical URI to its normalized canonical form so that queries
transparently match pre-pre-reset data without requiring a destructive
back-migration of the `facts` table.

```sql
-- Entity alias table for pre-pre-reset migration tooling (spec §2.6.6)
CREATE TABLE IF NOT EXISTS entity_aliases (
    raw_uri       TEXT NOT NULL,          -- original non-canonical stored form
    canonical_uri TEXT NOT NULL,          -- normalized form (output of normalize_entity_uri)
    created_at    TEXT NOT NULL,
    PRIMARY KEY (raw_uri)
);

CREATE INDEX IF NOT EXISTS idx_entity_aliases_canonical ON entity_aliases(canonical_uri);
```

### New columns — migration 004 (pre-reset)

In an N-node federation topology a fact may traverse multiple relay hops. These
three columns track the fact's provenance so that a receiving node can enforce
scope propagation invariants (§6.8). `origin_node_id` identifies the node that
originally asserted the fact (as opposed to the immediate peer that delivered
it). `origin_allowed_scopes` records the scope set the originator granted, so
that downstream relays can check whether re-federation is permitted.
`re_federation_blocked` is a computed flag set to `1` when company-scoped facts
must not be forwarded to third nodes — this is the default behaviour described
in §6.8.2.

```sql
-- Scope propagation tracking for N-node federation (spec §6.8.1)
ALTER TABLE facts ADD COLUMN origin_node_id        TEXT;   -- NULL for locally-asserted facts
ALTER TABLE facts ADD COLUMN origin_allowed_scopes TEXT;   -- JSON array; NULL for locally-asserted facts
ALTER TABLE facts ADD COLUMN re_federation_blocked INTEGER NOT NULL DEFAULT 0;  -- 1 if company-scope re-fed is blocked

CREATE INDEX IF NOT EXISTS idx_facts_re_federation ON facts(re_federation_blocked, scope);
```

**Note:** Migration 004 columns are NULL for all pre-the pre-reset spec facts. Nodes MUST populate
`origin_node_id` and `origin_allowed_scopes` only for facts received via federation
after the pre-reset spec is deployed.

</details>
