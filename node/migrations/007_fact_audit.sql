-- Track C / C3 — fact-level audit log.
-- Joins principal (entity_uri, oidc_sub), attested source (attested_key_id), and fact-id
-- for a verifiable end-to-end identity trail on every assertion.

CREATE TABLE IF NOT EXISTS fact_audit_log (
    id              TEXT PRIMARY KEY,
    fact_id         TEXT NOT NULL,
    event_type      TEXT NOT NULL DEFAULT 'assert',
    entity_uri      TEXT,          -- caller's entity_uri (null = pre-auth facts)
    oidc_sub        TEXT,          -- populated when key was issued via OIDC exchange
    source          TEXT NOT NULL,
    attested_key_id TEXT,          -- agent_keys.id if assertion was attested
    ts              TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_audit_fact_id  ON fact_audit_log(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_audit_entity   ON fact_audit_log(entity_uri);
CREATE INDEX IF NOT EXISTS idx_fact_audit_oidc_sub ON fact_audit_log(oidc_sub);
CREATE INDEX IF NOT EXISTS idx_fact_audit_ts       ON fact_audit_log(ts);
