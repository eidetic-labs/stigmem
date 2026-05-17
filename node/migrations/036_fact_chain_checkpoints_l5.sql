CREATE TABLE IF NOT EXISTS fact_chain_checkpoints (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    covered_chain_seq INTEGER NOT NULL,
    chain_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    submitted_at TEXT,
    next_retry_at TEXT,
    last_error TEXT,
    tl_backend TEXT NOT NULL,
    tl_log_id TEXT,
    tl_leaf_hash TEXT,
    tl_log_index INTEGER,
    tl_integrated_time INTEGER,
    tl_inclusion_proof TEXT NOT NULL DEFAULT '{}',
    tl_raw TEXT NOT NULL DEFAULT '{}',
    UNIQUE (tenant_id, covered_chain_seq)
);

CREATE INDEX IF NOT EXISTS idx_fact_chain_checkpoints_tenant_seq
    ON fact_chain_checkpoints (tenant_id, covered_chain_seq);

CREATE INDEX IF NOT EXISTS idx_fact_chain_checkpoints_status_retry
    ON fact_chain_checkpoints (status, next_retry_at);
