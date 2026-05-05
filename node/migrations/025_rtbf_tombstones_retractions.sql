-- Stigmem — RTBF tombstones, revocations, and append-only retraction log
-- Implements §23.5.3 (tombstones/revocations) and §24.2.1 c.3 (fact_retractions)
-- Required for §24.4 query_facts_as_of / recall_as_of time-travel support.

-- Active tombstones suppressing entity facts from recall (§23.2.1).
-- legal_hold: 0 = retroactive suppression (default RTBF); 1 = preserve for as_of admin queries.
CREATE TABLE IF NOT EXISTS tombstones (
  id          TEXT PRIMARY KEY,          -- "tomb_" + UUIDv7
  entity_uri  TEXT NOT NULL,
  scope       TEXT NOT NULL,             -- serialized ScopePattern: "*" | FactScope | JSON array
  reason      TEXT,
  signed_by   TEXT NOT NULL,
  signature   TEXT NOT NULL,
  created_at  TEXT NOT NULL,             -- ISO 8601
  legal_hold  INTEGER NOT NULL DEFAULT 0, -- 0 = false, 1 = true
  tenant_id   TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_tombstones_entity_uri ON tombstones(entity_uri);
CREATE INDEX IF NOT EXISTS idx_tombstones_tenant ON tombstones(tenant_id);

-- Tombstone revocations — non-destructive reinstatement of a tombstoned entity (§23.2.5).
CREATE TABLE IF NOT EXISTS tombstone_revocations (
  id           TEXT PRIMARY KEY,         -- "tombrevoke_" + UUIDv7
  tombstone_id TEXT NOT NULL REFERENCES tombstones(id),
  reason       TEXT NOT NULL,
  signed_by    TEXT NOT NULL,
  signature    TEXT NOT NULL,
  created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tombrevoke_tombstone_id ON tombstone_revocations(tombstone_id);

-- Append-only retraction log — authoritative for as_of retraction gating (§24.2.1 c.3).
-- Populated in addition to setting facts.confidence = 0.0 on retraction.
-- query_facts_as_of MUST join this table on retracted_at <= as_of; MUST NOT use facts.confidence.
CREATE TABLE IF NOT EXISTS fact_retractions (
  id           TEXT PRIMARY KEY,          -- "retract_" + UUIDv7 (or uuid4 for compat)
  fact_id      TEXT NOT NULL REFERENCES facts(id),
  retracted_at TEXT NOT NULL,             -- ISO 8601; authoritative timestamp for as_of queries
  retracted_by TEXT                       -- actor entity URI if known; null = system
);

CREATE INDEX IF NOT EXISTS idx_fact_retractions_fact_id ON fact_retractions(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_retractions_retracted_at ON fact_retractions(retracted_at);
