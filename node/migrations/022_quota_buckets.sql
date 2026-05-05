-- Stigmem reference node — per-principal token-bucket quotas (spec §22.4)
-- Migration 022: token-bucket state table + seq column on fact_audit_log

-- Token-bucket state: one row per (entity_uri, tenant_id, dimension).
-- Upserted on every quota check so initial rows are created lazily.
CREATE TABLE IF NOT EXISTS quota_buckets (
    entity_uri  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    dimension   TEXT NOT NULL,  -- 'fact_write', 'fact_read', 'token_issue', etc.
    tokens      REAL NOT NULL,  -- current token count (float, may be fractional)
    last_refill REAL NOT NULL,  -- Unix epoch (float seconds) of last refill
    PRIMARY KEY (entity_uri, tenant_id, dimension)
);

-- Monotonically increasing sequence number for audit ordering / cursor pagination.
-- Exposed via the admin audit export endpoint (spec §22.3).
-- Old rows keep NULL; new rows set it via the emit helper using rowid.
ALTER TABLE fact_audit_log ADD COLUMN seq INTEGER;

CREATE INDEX IF NOT EXISTS idx_fact_audit_seq ON fact_audit_log(seq);
