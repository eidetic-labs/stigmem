-- Lazy instruction discovery plugin schema.

CREATE TABLE IF NOT EXISTS instruction_manifests (
    id               TEXT PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    version          TEXT NOT NULL,
    fact_uri         TEXT NOT NULL,
    token_count      INTEGER NOT NULL,
    body             TEXT NOT NULL,
    created_at       INTEGER NOT NULL,
    superseded_at    INTEGER,
    UNIQUE(agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_manifests_agent ON instruction_manifests (agent_id, superseded_at);

CREATE TABLE IF NOT EXISTS instruction_audit (
    id               TEXT PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    heartbeat_id     TEXT NOT NULL,
    session_start    INTEGER NOT NULL,
    intent           TEXT NOT NULL,
    loaded_chunks    TEXT NOT NULL,
    used_chunks      TEXT NOT NULL DEFAULT '[]',
    missed_chunks    TEXT NOT NULL DEFAULT '[]',
    audit_token      TEXT NOT NULL UNIQUE,
    audit_closed     INTEGER,
    created_at       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_agent_session ON instruction_audit (agent_id, session_start DESC);
CREATE INDEX IF NOT EXISTS idx_audit_token ON instruction_audit (audit_token);

CREATE TABLE IF NOT EXISTS boot_stubs (
    agent_id          TEXT NOT NULL,
    adapter_profile   TEXT NOT NULL DEFAULT 'generic',
    stub_version      INTEGER NOT NULL DEFAULT 1,
    body              TEXT NOT NULL,
    token_count       INTEGER NOT NULL,
    generated_at      INTEGER NOT NULL,
    manifest_version  TEXT NOT NULL,
    PRIMARY KEY (agent_id, adapter_profile)
);
