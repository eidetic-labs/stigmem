-- Stigmem reference node v0.3.0 — federation schema additions
-- Migration 002: HLC timestamps, peers, cursors, conflicts, audit, nonce cache

-- Per-scope key restriction on api_keys (§3.5 v0.5); default = all scopes for backward-compat
ALTER TABLE api_keys ADD COLUMN allowed_scopes TEXT NOT NULL DEFAULT '["local","team","company","public"]';

-- New columns on facts table (NULL for pre-v0.5 facts)
ALTER TABLE facts ADD COLUMN hlc           TEXT;
ALTER TABLE facts ADD COLUMN received_from TEXT;

CREATE INDEX IF NOT EXISTS idx_hlc           ON facts(hlc)           WHERE hlc IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_received_from ON facts(received_from) WHERE received_from IS NOT NULL;

-- Peer registry (spec §6.1)
CREATE TABLE IF NOT EXISTS peers (
    id                TEXT PRIMARY KEY,
    node_id           TEXT NOT NULL UNIQUE,
    node_url          TEXT NOT NULL,
    federation_pubkey TEXT NOT NULL,
    allowed_scopes    TEXT NOT NULL,   -- JSON array
    status            TEXT NOT NULL CHECK(status IN ('pending_verification','active','rejected','revoked')),
    established_at    TEXT,            -- ISO 8601; set when status → active
    declaration_sig   TEXT NOT NULL,
    signed_at         TEXT NOT NULL
);

-- Replication cursors — one row per (peer, direction)
CREATE TABLE IF NOT EXISTS replication_cursors (
    peer_id    TEXT NOT NULL REFERENCES peers(id),
    direction  TEXT NOT NULL CHECK(direction IN ('inbound','outbound')),
    cursor     TEXT,         -- opaque HLC string; NULL = start from beginning
    updated_at TEXT NOT NULL,
    PRIMARY KEY (peer_id, direction)
);

-- Conflict registry (spec §3.3, §5.9)
CREATE TABLE IF NOT EXISTS conflicts (
    id                 TEXT PRIMARY KEY,   -- "stigmem:conflict:<uuid>"
    fact_a_id          TEXT NOT NULL REFERENCES facts(id),
    fact_b_id          TEXT NOT NULL REFERENCES facts(id),
    status             TEXT NOT NULL DEFAULT 'unresolved' CHECK(status IN ('unresolved','resolved')),
    resolution_fact_id TEXT,
    detected_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);

-- Federation audit log (spec §6.4)
CREATE TABLE IF NOT EXISTS federation_audit (
    id         TEXT PRIMARY KEY,
    peer_id    TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('rejected_fact','rejected_token','scope_violation','replay_attempt')),
    detail     TEXT,          -- JSON blob
    ts         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_peer_ts ON federation_audit(peer_id, ts);

-- Nonce cache for replay protection (spec §6.6)
CREATE TABLE IF NOT EXISTS nonce_cache (
    nonce      TEXT PRIMARY KEY,
    peer_id    TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nonce_expires ON nonce_cache(expires_at);
