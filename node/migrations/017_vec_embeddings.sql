-- Stigmem reference node — Phase 9: sqlite-vec embeddings + graph index
-- Migration 016: entity_edges (§1 design memo), embedding_meta (mixed-model safety),
--                embedding_missing flag on facts

-- -------------------------------------------------------------------------
-- entity_edges: materialized adjacency table (design memo §1 Option B)
-- Populated when a fact with value.type = "ref" is asserted.
-- Updated by the decay sweeper (confidence mirror) and retraction logic.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entity_edges (
    id            TEXT PRIMARY KEY,   -- = source fact id
    subject       TEXT NOT NULL,      -- normalized entity URI ("from" node)
    relation      TEXT NOT NULL,      -- predicate / edge label
    object        TEXT NOT NULL,      -- normalized entity URI ("to" node)
    scope         TEXT NOT NULL,
    confidence    REAL NOT NULL,      -- mirrors fact.confidence; updated by decay sweeper
    source_trust  REAL,               -- cached t(fact.source) per §19.4; nullable
    decay_epoch   INTEGER,            -- Unix ms of last decay sweep touch
    created_at    INTEGER NOT NULL    -- Unix ms
);

CREATE INDEX IF NOT EXISTS idx_edges_subject
    ON entity_edges (subject, scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_object
    ON entity_edges (object, scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel
    ON entity_edges (subject, relation, scope);

-- -------------------------------------------------------------------------
-- embedding_meta: single-row table tracking the active embedding model.
-- Prevents mixed-model pollution (different model_id or dimension).
-- The node refuses to embed if stored values differ from configured values.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS embedding_meta (
    id          INTEGER PRIMARY KEY CHECK (id = 1),  -- exactly one row
    model_id    TEXT NOT NULL,
    dimension   INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

-- -------------------------------------------------------------------------
-- facts: embedding status flag
-- NULL  = embedding not configured / not applicable
-- 1     = embedding missing (not yet computed or failed)
-- 0     = embedding present in vec_facts
-- -------------------------------------------------------------------------
ALTER TABLE facts ADD COLUMN embedding_missing INTEGER;

-- Index to support efficient backfill queries
CREATE INDEX IF NOT EXISTS idx_facts_embedding_missing
    ON facts (embedding_missing) WHERE embedding_missing = 1;
