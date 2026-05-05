-- Stigmem reference node — multi-tenant scoping (Postgres dialect)
-- Migration 012: adds tenant_id; uses ALTER TABLE instead of table rebuild
-- because Postgres enforces FK constraints at the DDL level even with no rows.
-- SQLite needed a rebuild to change UNIQUE(slug) → UNIQUE(slug, tenant_id);
-- Postgres can do this with DROP CONSTRAINT / ADD CONSTRAINT.

-- Step 1: add tenant_id to gardens
ALTER TABLE gardens ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';

-- Drop old UNIQUE(slug) constraint (Postgres auto-name: gardens_slug_key)
ALTER TABLE gardens DROP CONSTRAINT IF EXISTS gardens_slug_key;

-- Add new composite UNIQUE(slug, tenant_id)
ALTER TABLE gardens ADD CONSTRAINT gardens_slug_tenant_key UNIQUE (slug, tenant_id);

CREATE INDEX IF NOT EXISTS idx_gardens_slug   ON gardens(slug);
CREATE INDEX IF NOT EXISTS idx_gardens_tenant ON gardens(tenant_id);

-- Step 2: add tenant_id to the remaining tables
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE facts ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id);

ALTER TABLE fact_audit_log ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON fact_audit_log(tenant_id);
