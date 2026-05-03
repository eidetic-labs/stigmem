-- Stigmem reference node — multi-tenant scoping (v1.0-rc)
-- Migration 012: adds tenant_id to all write-bearing tables so a single node
-- can serve multiple independent tenants without data leakage.
-- DEFAULT 'default' preserves backward compatibility for all existing rows.
--
-- Gardens: the original UNIQUE(slug) constraint is widened to UNIQUE(slug, tenant_id)
-- so different tenants may use the same slug independently.  This requires a
-- table recreation because SQLite does not support DROP CONSTRAINT.

-- Step 1: rebuild gardens without the old global UNIQUE(slug)
CREATE TABLE gardens_new (
    id          TEXT PRIMARY KEY,
    slug        TEXT NOT NULL,
    name        TEXT NOT NULL,
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public')),
    description TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    UNIQUE(slug, tenant_id)
);

INSERT INTO gardens_new
    SELECT id, slug, name, scope, description, created_by, created_at, 'default'
    FROM gardens;

DROP TABLE gardens;
ALTER TABLE gardens_new RENAME TO gardens;

CREATE INDEX IF NOT EXISTS idx_gardens_slug   ON gardens(slug);
CREATE INDEX IF NOT EXISTS idx_gardens_tenant ON gardens(tenant_id);

-- Step 2: add tenant_id to the remaining tables
ALTER TABLE api_keys ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE facts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id);

ALTER TABLE fact_audit_log ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON fact_audit_log(tenant_id);
