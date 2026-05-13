-- Stigmem reference node — initial schema
-- Migration 001: fact store, auth, node metadata

CREATE TABLE IF NOT EXISTS schema_migrations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    version    TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
    id          TEXT PRIMARY KEY,
    entity      TEXT NOT NULL,
    relation    TEXT NOT NULL,
    value_type  TEXT NOT NULL CHECK(value_type IN ('string','text','number','boolean','datetime','ref','null')),
    value_v     TEXT NOT NULL,
    source      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    valid_until TEXT,                    -- ISO 8601 UTC or NULL
    confidence  REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public'))
);

CREATE INDEX IF NOT EXISTS idx_entity_relation       ON facts(entity, relation);
CREATE INDEX IF NOT EXISTS idx_entity_relation_scope ON facts(entity, relation, scope);
CREATE INDEX IF NOT EXISTS idx_scope                 ON facts(scope);
CREATE INDEX IF NOT EXISTS idx_timestamp             ON facts(timestamp);
CREATE INDEX IF NOT EXISTS idx_valid_until           ON facts(valid_until) WHERE valid_until IS NOT NULL;

-- API keys — credentials are hashes of the raw bearer token.
-- v0.9.0a1 rows may contain legacy SHA-256 hex; Phase B+ rows contain Argon2id.
CREATE TABLE IF NOT EXISTS api_keys (
    id          TEXT PRIMARY KEY,
    key_hash    TEXT NOT NULL UNIQUE,
    entity_uri  TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT '["read","write"]',  -- JSON array
    description TEXT,
    created_at  TEXT NOT NULL,
    expires_at  TEXT                     -- ISO 8601 UTC or NULL (non-expiring)
);

-- Node-level metadata (stable across restarts).
CREATE TABLE IF NOT EXISTS node_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
