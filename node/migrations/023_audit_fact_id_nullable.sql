-- Stigmem reference node — make fact_audit_log.fact_id nullable
-- Migration 023: audit events for non-fact operations (quota_breach, key_rotation,
-- admin_action, etc.) do not have an associated fact_id.

-- SQLite does not support DROP NOT NULL via ALTER TABLE; the constraint must be
-- removed by recreating the table.  All existing rows have a non-null fact_id,
-- so the copy is lossless.

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS fact_audit_log_v2 (
    id              TEXT PRIMARY KEY,
    fact_id         TEXT,               -- nullable: NULL for non-fact events
    event_type      TEXT NOT NULL DEFAULT 'assert',
    entity_uri      TEXT,
    oidc_sub        TEXT,
    source          TEXT NOT NULL DEFAULT '',
    attested_key_id TEXT,
    ts              TEXT NOT NULL,
    tenant_id       TEXT,
    detail          TEXT,
    seq             INTEGER
);

INSERT INTO fact_audit_log_v2
    (id, fact_id, event_type, entity_uri, oidc_sub, source,
     attested_key_id, ts, tenant_id, detail, seq)
SELECT  id, fact_id, event_type, entity_uri, oidc_sub, source,
        attested_key_id, ts, tenant_id, detail, seq
FROM fact_audit_log;

DROP TABLE fact_audit_log;

ALTER TABLE fact_audit_log_v2 RENAME TO fact_audit_log;

CREATE INDEX IF NOT EXISTS idx_fact_audit_fact_id  ON fact_audit_log(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_audit_entity   ON fact_audit_log(entity_uri);
CREATE INDEX IF NOT EXISTS idx_fact_audit_oidc_sub ON fact_audit_log(oidc_sub);
CREATE INDEX IF NOT EXISTS idx_fact_audit_ts       ON fact_audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_fact_audit_seq      ON fact_audit_log(seq);

PRAGMA foreign_keys = ON;
