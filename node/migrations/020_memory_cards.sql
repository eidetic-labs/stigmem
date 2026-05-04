-- Stigmem reference node — memory cards materializer (spec §20, Phase 9 ACM-214)
-- Migration 020: per-entity synthesized summary table

CREATE TABLE IF NOT EXISTS memory_cards (
    entity_uri         TEXT NOT NULL,
    tenant_id          TEXT NOT NULL DEFAULT 'default',
    scope              TEXT NOT NULL DEFAULT 'local',
    summary            TEXT NOT NULL DEFAULT '',
    fact_hashes        TEXT NOT NULL DEFAULT '[]',  -- JSON array of sha256(fact_id)
    avg_confidence     REAL NOT NULL DEFAULT 0.0,
    refreshed_at       TEXT,
    is_stale           INTEGER NOT NULL DEFAULT 1,  -- 1=stale, 0=fresh
    has_contradictions INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_uri, tenant_id, scope)
);

CREATE INDEX IF NOT EXISTS idx_memory_cards_stale
    ON memory_cards (is_stale, tenant_id, scope);
CREATE INDEX IF NOT EXISTS idx_memory_cards_entity
    ON memory_cards (entity_uri, tenant_id);
