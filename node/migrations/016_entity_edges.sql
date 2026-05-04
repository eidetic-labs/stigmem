-- Stigmem reference node — graph adjacency index (§20)
-- Migration 016: entity_edges side-index for O(degree)-per-hop traversal

-- -------------------------------------------------------------------------
-- entity_edges table
-- Each row mirrors one ref-typed fact: subject -[relation]-> object
-- id = source fact UUID (one-to-one with the fact row)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entity_edges (
    id            TEXT PRIMARY KEY,         -- = source fact id
    subject       TEXT NOT NULL,            -- normalized entity URI (from)
    relation      TEXT NOT NULL,            -- predicate label
    object        TEXT NOT NULL,            -- normalized entity URI (to)
    scope         TEXT NOT NULL,            -- inherits from source fact
    garden_id     TEXT REFERENCES gardens(id),
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    received_from TEXT,                     -- non-null for federated facts (§19.5.2)
    valid_until   TEXT,                     -- mirrors fact.valid_until for expiry filtering
    confidence    REAL NOT NULL,            -- mirrors fact.confidence; 0.0 = retracted
    source_trust  REAL,                     -- cached t(fact.source) per §19.4; nullable
    decay_epoch   INTEGER,                  -- Unix ms of last decay/retraction update
    created_at    INTEGER NOT NULL          -- Unix ms of edge creation
);

-- Subject-first index supports forward BFS hops and relation-filtered traversal
CREATE INDEX IF NOT EXISTS idx_edges_subject
    ON entity_edges (subject, scope, confidence);

-- Object-first index supports reverse BFS hops
CREATE INDEX IF NOT EXISTS idx_edges_object
    ON entity_edges (object, scope, confidence);

-- Combined subject+relation index for relation-filtered forward hops
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel
    ON entity_edges (subject, relation, scope);

-- Tenant isolation index
CREATE INDEX IF NOT EXISTS idx_edges_tenant
    ON entity_edges (tenant_id, scope);

-- -------------------------------------------------------------------------
-- Backfill: populate from existing ref-typed facts
-- Only inserts edges for facts with URI-like ref values; idempotent via
-- INSERT OR IGNORE.
-- -------------------------------------------------------------------------
INSERT OR IGNORE INTO entity_edges
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
    CAST(CAST(strftime('%s', f.timestamp) AS INTEGER) * 1000 AS INTEGER)
FROM facts f
WHERE f.value_type = 'ref'
  AND f.value_v IS NOT NULL
  AND f.value_v != 'null'
  AND (f.value_v LIKE '%://%' OR f.value_v LIKE 'urn:%')
  AND f.confidence > 0.0;
