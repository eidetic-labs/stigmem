-- Stigmem reference node — recall endpoint (Postgres dialect)
-- Migration 019: facts_fts placeholder + recall_audit_log
--
-- SQLite version creates an FTS5 virtual table (USING fts5) with BM25 search
-- and sync triggers.  Postgres uses plain B-tree tables here; the recall
-- endpoint's _lexical_search() degrades gracefully (returns {} on error)
-- when it encounters the FTS5-specific "bm25(facts_fts)" / "MATCH ?" syntax.
--
-- Operators wanting full Postgres FTS can:
--   1. Enable pg_trgm: CREATE EXTENSION IF NOT EXISTS pg_trgm;
--   2. Add a GIN index on a tsvector column in facts.
--   3. Override _lexical_search() with a Postgres FTS query.

-- Placeholder table so references in application code don't cause "table not found"
-- errors at startup (e.g. information_schema introspection).
CREATE TABLE IF NOT EXISTS facts_fts (
    fact_id  TEXT NOT NULL,
    entity   TEXT NOT NULL DEFAULT '',
    relation TEXT NOT NULL DEFAULT '',
    value_v  TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_facts_fts_fact_id ON facts_fts (fact_id);

-- -------------------------------------------------------------------------
-- recall_audit_log: one row per POST /v1/recall call (spec §20 audit)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recall_audit_log (
    id             TEXT PRIMARY KEY,
    entity_uri     TEXT,
    query_hash     TEXT NOT NULL,
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
