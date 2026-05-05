-- Stigmem reference node — federation trust (Postgres dialect)
-- Migration 014: quarantine, trust manifests, capability tokens, trust rules
--
-- SQLite version rebuilt peers/replication_cursors/federation_audit to extend
-- the status CHECK constraint and used PRAGMA legacy_alter_table.
-- Postgres supports ALTER TABLE DROP CONSTRAINT / ADD CONSTRAINT directly.

-- -------------------------------------------------------------------------
-- peers: extend status CHECK to include 'pending_tl_proof'
-- -------------------------------------------------------------------------
ALTER TABLE peers DROP CONSTRAINT IF EXISTS peers_status_check;
ALTER TABLE peers ADD CONSTRAINT peers_status_check
    CHECK(status IN ('pending_verification','active','rejected','revoked','pending_tl_proof'));

CREATE INDEX IF NOT EXISTS idx_audit_peer_ts ON federation_audit(peer_id, ts);

-- -------------------------------------------------------------------------
-- Gardens: quarantine flag
-- -------------------------------------------------------------------------
ALTER TABLE gardens ADD COLUMN IF NOT EXISTS quarantine INTEGER NOT NULL DEFAULT 0;

-- -------------------------------------------------------------------------
-- garden_members: extend role CHECK to include 'quarantine:moderator'
-- -------------------------------------------------------------------------
ALTER TABLE garden_members DROP CONSTRAINT IF EXISTS garden_members_role_check;
ALTER TABLE garden_members ADD CONSTRAINT garden_members_role_check
    CHECK(role IN ('admin','writer','reader','quarantine:moderator'));

CREATE INDEX IF NOT EXISTS idx_garden_members_entity ON garden_members(entity_uri);

-- -------------------------------------------------------------------------
-- Facts: quarantine metadata
-- -------------------------------------------------------------------------
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_status        TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_garden_id     TEXT REFERENCES gardens(id);
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_acted_by      TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_acted_at      TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_reason        TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS derived_from             TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS attestation_chain        TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS attestation_chain_issuers TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS source_trust             REAL;

-- -------------------------------------------------------------------------
-- Org manifest storage (§19.1)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS federation_manifests (
    id              TEXT PRIMARY KEY,
    entity_uri      TEXT NOT NULL UNIQUE,
    manifest_json   TEXT NOT NULL,
    signature       TEXT NOT NULL,
    key_id          TEXT NOT NULL,
    issued_at       TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    log_entry_json  TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_federation_manifests_entity_uri
    ON federation_manifests(entity_uri);
CREATE INDEX IF NOT EXISTS idx_federation_manifests_key_id
    ON federation_manifests(key_id);

-- -------------------------------------------------------------------------
-- Capability token storage (§19.3)
-- Differs from SQLite: GLOB '[0-9a-f]*' → ~ '^[0-9a-f]+$' (Postgres regex)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capability_tokens (
    id          TEXT PRIMARY KEY,
    token_json  TEXT NOT NULL,
    issuer      TEXT NOT NULL,
    subject     TEXT NOT NULL,
    verb        TEXT NOT NULL,
    object      TEXT NOT NULL,
    issued_at   TEXT NOT NULL,
    expiry      TEXT NOT NULL,
    nonce       TEXT NOT NULL UNIQUE
                    CHECK(length(nonce) = 64 AND nonce ~ '^[0-9a-f]+$'),
    revoked_at  TEXT,
    revoke_log  TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capability_tokens_subject ON capability_tokens(subject);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_issuer  ON capability_tokens(issuer);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_nonce   ON capability_tokens(nonce);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_expiry  ON capability_tokens(expiry);

-- -------------------------------------------------------------------------
-- Auto-trust rules (§19)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quarantine_rules (
    id          TEXT PRIMARY KEY,
    rule_type   TEXT NOT NULL,
    org_uri     TEXT NOT NULL,
    scope       TEXT,
    entity_pat  TEXT,
    reason      TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    tenant_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_quarantine_rules_org_uri
    ON quarantine_rules(org_uri);

-- -------------------------------------------------------------------------
-- Query-time indexes
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_facts_quarantine_status
    ON facts(quarantine_status) WHERE quarantine_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facts_quarantine_garden
    ON facts(quarantine_garden_id) WHERE quarantine_garden_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facts_source_trust
    ON facts(source_trust) WHERE source_trust IS NOT NULL;
