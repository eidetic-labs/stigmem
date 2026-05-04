-- Stigmem reference node — federation trust (§19)
-- Migration 014: quarantine garden flag, quarantine fact metadata, source_trust snapshot,
--                org manifests, capability tokens, quarantine routing rules

-- -------------------------------------------------------------------------
-- Gardens: quarantine flag
-- -------------------------------------------------------------------------
ALTER TABLE gardens ADD COLUMN quarantine INTEGER NOT NULL DEFAULT 0;
-- 0 = standard garden, 1 = quarantine garden

-- -------------------------------------------------------------------------
-- garden_members: extend role CHECK constraint for quarantine:moderator
-- SQLite cannot ALTER a CHECK constraint; rebuild the table.
-- -------------------------------------------------------------------------
ALTER TABLE garden_members RENAME TO garden_members_old;

CREATE TABLE garden_members (
    garden_id   TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    entity_uri  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin','writer','reader','quarantine:moderator')),
    added_by    TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    PRIMARY KEY (garden_id, entity_uri)
);

INSERT INTO garden_members SELECT * FROM garden_members_old;
DROP TABLE garden_members_old;

CREATE INDEX IF NOT EXISTS idx_garden_members_entity ON garden_members(entity_uri);

-- -------------------------------------------------------------------------
-- Facts: quarantine metadata
-- -------------------------------------------------------------------------
ALTER TABLE facts ADD COLUMN quarantine_status TEXT;
-- NULL = not quarantined; "pending" = awaiting review;
-- "promoted" = admitted to a target garden; "rejected" = permanently rejected

ALTER TABLE facts ADD COLUMN quarantine_garden_id TEXT REFERENCES gardens(id);
ALTER TABLE facts ADD COLUMN quarantine_acted_by  TEXT;
ALTER TABLE facts ADD COLUMN quarantine_acted_at  TEXT;
ALTER TABLE facts ADD COLUMN quarantine_reason    TEXT;

-- Facts: provenance chain (§19.6)
ALTER TABLE facts ADD COLUMN derived_from              TEXT;  -- JSON array of FactHash
ALTER TABLE facts ADD COLUMN attestation_chain         TEXT;  -- JSON array of base64url sigs
ALTER TABLE facts ADD COLUMN attestation_chain_issuers TEXT;  -- JSON array of URI

-- Facts: source-trust snapshot (§19.4)
ALTER TABLE facts ADD COLUMN source_trust REAL;
-- Snapshot of t at write time; authoritative value recomputed live at recall.

-- -------------------------------------------------------------------------
-- Org manifest storage (§19.1)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS federation_manifests (
    id              TEXT PRIMARY KEY,
    entity_uri      TEXT NOT NULL UNIQUE,
    manifest_json   TEXT NOT NULL,   -- JCS-canonical manifest body
    signature       TEXT NOT NULL,   -- base64url Ed25519 sig
    key_id          TEXT NOT NULL,
    issued_at       TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    log_entry_json  TEXT,            -- NULL if not yet submitted to transparency log
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_federation_manifests_entity_uri
    ON federation_manifests(entity_uri);
CREATE INDEX IF NOT EXISTS idx_federation_manifests_key_id
    ON federation_manifests(key_id);

-- -------------------------------------------------------------------------
-- Capability token storage (§19.3)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capability_tokens (
    id          TEXT PRIMARY KEY,   -- token_id UUID
    token_json  TEXT NOT NULL,      -- full signed token body (JCS-canonical)
    issuer      TEXT NOT NULL,
    subject     TEXT NOT NULL,
    verb        TEXT NOT NULL,
    object      TEXT NOT NULL,
    issued_at   TEXT NOT NULL,
    expiry      TEXT NOT NULL,
    nonce       TEXT NOT NULL UNIQUE
                    CHECK(length(nonce) = 64 AND nonce GLOB '[0-9a-f]*'),
    revoked_at  TEXT,               -- NULL if active
    revoke_log  TEXT,               -- JSON of RevocationEvent if revoked
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capability_tokens_subject ON capability_tokens(subject);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_issuer  ON capability_tokens(issuer);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_nonce   ON capability_tokens(nonce);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_expiry  ON capability_tokens(expiry);

-- -------------------------------------------------------------------------
-- Auto-trust rules (§19 issue scope — operator-configured bypass/reject)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quarantine_rules (
    id          TEXT PRIMARY KEY,
    rule_type   TEXT NOT NULL,   -- "always_trust" or "never_trust"
    org_uri     TEXT NOT NULL,   -- source org / entity_uri pattern (exact match)
    scope       TEXT,            -- scope filter; NULL = apply to all scopes
    entity_pat  TEXT,            -- entity URI prefix pattern; NULL = all entities
    reason      TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    tenant_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_quarantine_rules_org_uri
    ON quarantine_rules(org_uri);

-- -------------------------------------------------------------------------
-- Quarantine-specific admin audit extension
-- The existing fact_audit_log table (Migration 007) gains rows with
-- event_type "quarantine_promote" / "quarantine_reject".
-- The detail JSON carries the extra §19.5.6 fields.
-- No schema change needed; detail is already a TEXT/JSON blob.
-- -------------------------------------------------------------------------

-- -------------------------------------------------------------------------
-- Query-time indexes
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_facts_quarantine_status
    ON facts(quarantine_status) WHERE quarantine_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facts_quarantine_garden
    ON facts(quarantine_garden_id) WHERE quarantine_garden_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facts_source_trust
    ON facts(source_trust) WHERE source_trust IS NOT NULL;
