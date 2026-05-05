-- Stigmem reference node — graph adjacency index (§20) — Postgres dialect
-- Migration 016: entity_edges side-index for O(degree)-per-hop traversal
--
-- Differences from the SQLite version:
--   * decay_epoch / created_at use BIGINT (not INTEGER) — Unix milliseconds
--     exceed the 2^31 limit of Postgres INTEGER.
--   * Backfill uses EXTRACT(EPOCH …) instead of strftime('%s', …).
--   * INSERT OR IGNORE → INSERT … ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS entity_edges (
    id            TEXT PRIMARY KEY,
    subject       TEXT NOT NULL,
    relation      TEXT NOT NULL,
    object        TEXT NOT NULL,
    scope         TEXT NOT NULL,
    garden_id     TEXT REFERENCES gardens(id),
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    received_from TEXT,
    valid_until   TEXT,
    confidence    REAL NOT NULL,
    source_trust  REAL,
    decay_epoch   BIGINT,
    created_at    BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_subject
    ON entity_edges (subject, scope, confidence);

CREATE INDEX IF NOT EXISTS idx_edges_object
    ON entity_edges (object, scope, confidence);

CREATE INDEX IF NOT EXISTS idx_edges_subject_rel
    ON entity_edges (subject, relation, scope);

CREATE INDEX IF NOT EXISTS idx_edges_tenant
    ON entity_edges (tenant_id, scope);

INSERT INTO entity_edges
    (id, subject, relation, object, scope, garden_id, tenant_id,
     received_from, valid_until, confidence, source_trust, decay_epoch, created_at)
SELECT
    f.id,
    f.entity,
    f.relation,
    f.value_v,
    f.scope,
    f.garden_id,
    COALESCE(f.tenant_id, 'default'),
    f.received_from,
    f.valid_until,
    f.confidence,
    f.source_trust,
    NULL,
    (EXTRACT(EPOCH FROM f.timestamp::timestamptz) * 1000)::BIGINT
FROM facts f
WHERE f.value_type = 'ref'
  AND f.value_v IS NOT NULL
  AND f.value_v != 'null'
  AND (f.value_v LIKE '%://%' OR f.value_v LIKE 'urn:%')
  AND f.confidence > 0.0
ON CONFLICT DO NOTHING;
