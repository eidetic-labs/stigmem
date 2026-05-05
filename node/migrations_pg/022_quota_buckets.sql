-- Stigmem reference node — per-principal token-bucket quotas (Postgres dialect)
-- Migration 022: quota_buckets table + seq auto-sequence on fact_audit_log
--
-- Differs from SQLite: PostgreSQL has no implicit "rowid". Instead, we attach
-- a named sequence to fact_audit_log.seq so the column is auto-populated on
-- INSERT and emit() does not need a separate SELECT rowid / UPDATE step.

CREATE TABLE IF NOT EXISTS quota_buckets (
    entity_uri  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    dimension   TEXT NOT NULL,
    tokens      DOUBLE PRECISION NOT NULL,
    last_refill DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (entity_uri, tenant_id, dimension)
);

CREATE SEQUENCE IF NOT EXISTS fact_audit_log_seq_seq;

ALTER TABLE fact_audit_log
    ADD COLUMN IF NOT EXISTS seq BIGINT DEFAULT nextval('fact_audit_log_seq_seq');

CREATE INDEX IF NOT EXISTS idx_fact_audit_seq ON fact_audit_log(seq);
