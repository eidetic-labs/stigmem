-- Stigmem reference node — make fact_audit_log.fact_id nullable (Postgres dialect)
-- Migration 023: audit events for non-fact operations do not have a fact_id.
--
-- PostgreSQL supports ALTER COLUMN DROP NOT NULL directly, unlike SQLite which
-- requires a full table rebuild.

ALTER TABLE fact_audit_log ALTER COLUMN fact_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fact_audit_fact_id  ON fact_audit_log(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_audit_entity   ON fact_audit_log(entity_uri);
CREATE INDEX IF NOT EXISTS idx_fact_audit_oidc_sub ON fact_audit_log(oidc_sub);
CREATE INDEX IF NOT EXISTS idx_fact_audit_ts       ON fact_audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_fact_audit_seq      ON fact_audit_log(seq);
