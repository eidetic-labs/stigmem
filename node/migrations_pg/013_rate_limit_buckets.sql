-- Stigmem reference node — rate limiting (Postgres dialect)
-- Migration 013: sliding-window request counters per API key
-- Differs from SQLite: AUTOINCREMENT → SERIAL

CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    id       SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL,
    op_type  TEXT NOT NULL,
    ts       DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_key_op_ts
    ON rate_limit_buckets (key_hash, op_type, ts);
