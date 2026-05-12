-- Tighten capability token nonce validation.
--
-- The original SQLite CHECK used ``nonce GLOB '[0-9a-f]*'``, which only
-- required the nonce to start with a lowercase hex character. Rebuild the
-- table so all 64 characters must be lowercase hex.

PRAGMA foreign_keys=OFF;
BEGIN;

ALTER TABLE capability_tokens RENAME TO capability_tokens_old;

CREATE TABLE capability_tokens (
    id          TEXT PRIMARY KEY,
    token_json  TEXT NOT NULL,
    issuer      TEXT NOT NULL,
    subject     TEXT NOT NULL,
    verb        TEXT NOT NULL,
    object      TEXT NOT NULL,
    issued_at   TEXT NOT NULL,
    expiry      TEXT NOT NULL,
    nonce       TEXT NOT NULL UNIQUE
                    CHECK(length(nonce) = 64 AND nonce NOT GLOB '*[^0-9a-f]*'),
    revoked_at  TEXT,
    revoke_log  TEXT,
    created_at  TEXT NOT NULL
);

INSERT INTO capability_tokens (
    id,
    token_json,
    issuer,
    subject,
    verb,
    object,
    issued_at,
    expiry,
    nonce,
    revoked_at,
    revoke_log,
    created_at
)
SELECT
    id,
    token_json,
    issuer,
    subject,
    verb,
    object,
    issued_at,
    expiry,
    nonce,
    revoked_at,
    revoke_log,
    created_at
FROM capability_tokens_old;

DROP TABLE capability_tokens_old;

CREATE INDEX IF NOT EXISTS idx_capability_tokens_subject ON capability_tokens(subject);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_issuer  ON capability_tokens(issuer);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_nonce   ON capability_tokens(nonce);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_expiry  ON capability_tokens(expiry);

COMMIT;
PRAGMA foreign_keys=ON;
