-- Track C / C1 — per-agent Ed25519 public-key registration.
-- Agents register their Ed25519 public key; assertions can carry an attestation
-- token (key_id + signature) so the node verifies source provenance end-to-end.

CREATE TABLE IF NOT EXISTS agent_keys (
    id            TEXT PRIMARY KEY,
    entity_uri    TEXT NOT NULL,
    public_key    TEXT NOT NULL,  -- base64url-encoded Ed25519 raw public key (no padding)
    description   TEXT,
    registered_at TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'revoked'))
);

CREATE INDEX IF NOT EXISTS idx_agent_keys_entity        ON agent_keys(entity_uri);
CREATE INDEX IF NOT EXISTS idx_agent_keys_entity_status ON agent_keys(entity_uri, status);

-- Record which agent key attested each locally-written fact (NULL = unattested).
ALTER TABLE facts ADD COLUMN attested_key_id TEXT;
