-- Stigmem reference node — R-21 per-session read/write graph tracking

CREATE TABLE IF NOT EXISTS session_scope_access (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    entity_uri  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    scope       TEXT NOT NULL,
    access_type TEXT NOT NULL CHECK (access_type IN ('read', 'write')),
    ts          TEXT NOT NULL,
    UNIQUE(session_id, entity_uri, tenant_id, scope, access_type)
);

CREATE INDEX IF NOT EXISTS idx_session_scope_access_lookup
    ON session_scope_access(session_id, entity_uri, tenant_id, access_type, scope);
