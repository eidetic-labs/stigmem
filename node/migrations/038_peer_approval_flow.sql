-- Add pending peer approval state and audit events for explicit peer activation.

PRAGMA legacy_alter_table = ON;

ALTER TABLE replication_cursors RENAME TO replication_cursors_old;
ALTER TABLE peers RENAME TO peers_old;
ALTER TABLE federation_audit RENAME TO federation_audit_old;

CREATE TABLE peers (
    id                TEXT PRIMARY KEY,
    node_id           TEXT NOT NULL UNIQUE,
    node_url          TEXT NOT NULL,
    federation_pubkey TEXT NOT NULL,
    allowed_scopes    TEXT NOT NULL,
    status            TEXT NOT NULL CHECK(status IN (
                        'pending_verification','pending_approval','active',
                        'rejected','revoked','pending_tl_proof'
                      )),
    established_at    TEXT,
    declaration_sig   TEXT NOT NULL,
    signed_at         TEXT NOT NULL,
    created_at        TEXT
);

CREATE TABLE replication_cursors (
    peer_id    TEXT NOT NULL REFERENCES peers(id),
    direction  TEXT NOT NULL CHECK(direction IN ('inbound','outbound')),
    cursor     TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (peer_id, direction)
);

CREATE TABLE federation_audit (
    id         TEXT PRIMARY KEY,
    peer_id    TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
                    'rejected_fact','rejected_token','scope_violation','replay_attempt',
                    'tl_proof_missing','tl_proof_verified','manifest_stored',
                    'manifest_refresh_failed','san_mismatch',
                    'peer_approved','peer_approval_failed'
               )),
    detail     TEXT,
    ts         TEXT NOT NULL
);

INSERT INTO peers (
    id,
    node_id,
    node_url,
    federation_pubkey,
    allowed_scopes,
    status,
    established_at,
    declaration_sig,
    signed_at,
    created_at
)
SELECT
    id,
    node_id,
    node_url,
    federation_pubkey,
    allowed_scopes,
    status,
    established_at,
    declaration_sig,
    signed_at,
    created_at
FROM peers_old;
INSERT INTO replication_cursors SELECT * FROM replication_cursors_old;
INSERT INTO federation_audit SELECT * FROM federation_audit_old;

DROP TABLE replication_cursors_old;
DROP TABLE peers_old;
DROP TABLE federation_audit_old;

CREATE INDEX IF NOT EXISTS idx_audit_peer_ts ON federation_audit(peer_id, ts);

PRAGMA legacy_alter_table = OFF;
