-- RTBF tombstone plugin schema.
-- Retraction history remains owned by the time-travel plugin lane.

CREATE TABLE IF NOT EXISTS tombstones (
  id TEXT PRIMARY KEY,
  entity_uri TEXT NOT NULL,
  scope TEXT NOT NULL,
  reason TEXT,
  signed_by TEXT NOT NULL,
  key_id TEXT,
  signature TEXT NOT NULL,
  created_at TEXT NOT NULL,
  legal_hold INTEGER NOT NULL DEFAULT 0,
  tenant_id TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_tombstones_entity_uri ON tombstones(entity_uri);
CREATE INDEX IF NOT EXISTS idx_tombstones_tenant ON tombstones(tenant_id);

CREATE TABLE IF NOT EXISTS tombstone_revocations (
  id TEXT PRIMARY KEY,
  tombstone_id TEXT NOT NULL REFERENCES tombstones(id),
  reason TEXT NOT NULL,
  signed_by TEXT NOT NULL,
  key_id TEXT,
  signature TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tombrevoke_tombstone_id
  ON tombstone_revocations(tombstone_id);
