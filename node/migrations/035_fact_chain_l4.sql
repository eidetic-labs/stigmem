-- Stigmem Phase B §5.2a.5 — ADR-016 L4 local hash chain.
--
-- Each local fact assertion appends one per-tenant chain entry. The entry
-- stores a deterministic event hash over the fact's canonical row data and a
-- chain hash over the previous chain hash plus this event. L5 external
-- anchoring can later checkpoint these chain hashes.

CREATE TABLE IF NOT EXISTS fact_chain (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    chain_seq     INTEGER NOT NULL,
    fact_id       TEXT NOT NULL REFERENCES facts(id),
    event_hash    TEXT NOT NULL,
    previous_hash TEXT,
    chain_hash    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE (tenant_id, chain_seq),
    UNIQUE (tenant_id, fact_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_chain_tenant_seq
    ON fact_chain (tenant_id, chain_seq);
CREATE INDEX IF NOT EXISTS idx_fact_chain_fact_id
    ON fact_chain (fact_id);
