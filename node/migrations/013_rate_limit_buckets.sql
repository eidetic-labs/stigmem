-- Stigmem reference node — rate limiting
-- Migration 013: sliding-window request counters per API key

CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL,
    op_type  TEXT NOT NULL,  -- 'read' or 'write'
    ts       REAL NOT NULL   -- Unix timestamp (seconds, float)
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_key_op_ts
    ON rate_limit_buckets (key_hash, op_type, ts);
