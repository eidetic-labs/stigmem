-- Allow the mTLS SAN mismatch audit event emitted by federation peer auth.

PRAGMA legacy_alter_table = ON;

ALTER TABLE federation_audit RENAME TO federation_audit_old;

CREATE TABLE federation_audit (
    id         TEXT PRIMARY KEY,
    peer_id    TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
                    'rejected_fact','rejected_token','scope_violation','replay_attempt',
                    'tl_proof_missing','tl_proof_verified','manifest_stored',
                    'manifest_refresh_failed','san_mismatch'
               )),
    detail     TEXT,
    ts         TEXT NOT NULL
);

INSERT INTO federation_audit SELECT * FROM federation_audit_old;

DROP TABLE federation_audit_old;

CREATE INDEX IF NOT EXISTS idx_audit_peer_ts ON federation_audit(peer_id, ts);

PRAGMA legacy_alter_table = OFF;
