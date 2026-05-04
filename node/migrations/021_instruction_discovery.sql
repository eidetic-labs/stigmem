-- Stigmem reference node — lazy instruction discovery (spec §21, Phase 10 ACM-225)
-- Migration 021: instruction_manifests, instruction_audit, boot_stubs tables

-- Instruction manifest registry (§21.7)
CREATE TABLE IF NOT EXISTS instruction_manifests (
    id               TEXT PRIMARY KEY,           -- UUID
    agent_id         TEXT NOT NULL,
    version          TEXT NOT NULL,
    fact_uri         TEXT NOT NULL,              -- instruction: scope URI
    token_count      INTEGER NOT NULL,
    body             TEXT NOT NULL,              -- JSON: array of manifest entries
    created_at       INTEGER NOT NULL,           -- Unix ms
    superseded_at    INTEGER,                    -- NULL if current version
    UNIQUE(agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_manifests_agent ON instruction_manifests (agent_id, superseded_at);

-- Discovery audit log (append-only, §21.5.1)
CREATE TABLE IF NOT EXISTS instruction_audit (
    id               TEXT PRIMARY KEY,           -- audevent_ prefixed
    agent_id         TEXT NOT NULL,
    heartbeat_id     TEXT NOT NULL,
    session_start    INTEGER NOT NULL,           -- Unix ms
    intent           TEXT NOT NULL,
    loaded_chunks    TEXT NOT NULL,              -- JSON array of unit names
    used_chunks      TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    missed_chunks    TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    audit_token      TEXT NOT NULL UNIQUE,
    audit_closed     INTEGER,                    -- Unix ms; NULL until POST /audit
    created_at       INTEGER NOT NULL            -- Unix ms
);
CREATE INDEX IF NOT EXISTS idx_audit_agent_session ON instruction_audit (agent_id, session_start DESC);
CREATE INDEX IF NOT EXISTS idx_audit_token         ON instruction_audit (audit_token);

-- Boot stub cache (§21.7)
CREATE TABLE IF NOT EXISTS boot_stubs (
    agent_id          TEXT NOT NULL,
    adapter_profile   TEXT NOT NULL DEFAULT 'generic',
    stub_version      INTEGER NOT NULL DEFAULT 1,
    body              TEXT NOT NULL,              -- full markdown stub
    token_count       INTEGER NOT NULL,
    generated_at      INTEGER NOT NULL,           -- Unix ms
    manifest_version  TEXT NOT NULL,              -- version string of backing manifest
    PRIMARY KEY (agent_id, adapter_profile)
);
