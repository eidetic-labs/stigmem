-- Stigmem reference node — Phase 9: recall endpoint
-- Migration 019: FTS5 lexical index on facts + recall_audit_log

-- -------------------------------------------------------------------------
-- facts_fts: FTS5 virtual table for lexical (BM25) search
-- Stores a copy of entity / relation / value_v for full-text recall.
-- Populated by AFTER INSERT / UPDATE / DELETE triggers on facts.
-- -------------------------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    fact_id  UNINDEXED,   -- stored-only; not tokenised
    entity,
    relation,
    value_v,
    tokenize='unicode61 remove_diacritics 1'
);

-- Keep FTS in sync with facts.
CREATE TRIGGER IF NOT EXISTS facts_fts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(fact_id, entity, relation, value_v)
    VALUES (new.id, new.entity, new.relation, new.value_v);
END;

CREATE TRIGGER IF NOT EXISTS facts_fts_au AFTER UPDATE OF entity, relation, value_v ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, fact_id, entity, relation, value_v)
    VALUES ('delete', old.rowid, old.id, old.entity, old.relation, old.value_v);
    INSERT INTO facts_fts(fact_id, entity, relation, value_v)
    VALUES (new.id, new.entity, new.relation, new.value_v);
END;

CREATE TRIGGER IF NOT EXISTS facts_fts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, fact_id, entity, relation, value_v)
    VALUES ('delete', old.rowid, old.id, old.entity, old.relation, old.value_v);
END;

-- Backfill existing facts into FTS index.
INSERT INTO facts_fts(fact_id, entity, relation, value_v)
SELECT id, entity, relation, value_v FROM facts;

-- -------------------------------------------------------------------------
-- recall_audit_log: one row per POST /v1/recall call (spec §20 audit)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recall_audit_log (
    id             TEXT PRIMARY KEY,
    entity_uri     TEXT,         -- caller identity
    query_hash     TEXT NOT NULL, -- SHA-256 hex of query string
    scope          TEXT NOT NULL,
    token_budget   INTEGER NOT NULL,
    facts_returned INTEGER NOT NULL,
    tokens_used    INTEGER NOT NULL,
    truncated      INTEGER NOT NULL DEFAULT 0,
    tenant_id      TEXT NOT NULL DEFAULT 'default',
    ts             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recall_audit_ts
    ON recall_audit_log (ts);
CREATE INDEX IF NOT EXISTS idx_recall_audit_entity
    ON recall_audit_log (entity_uri);
