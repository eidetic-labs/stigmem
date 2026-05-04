-- Stigmem reference node — fix idempotency_key uniqueness scope (Postgres dialect)
-- Migration 019_subscriptions_idempotency_tenant_scope
--
-- SQLite version rebuilt the subscriptions table (needed PRAGMA foreign_keys=OFF
-- because SQLite cannot DROP CONSTRAINT).  Postgres supports ALTER TABLE
-- DROP CONSTRAINT / ADD CONSTRAINT directly.

-- Drop the table-wide UNIQUE(idempotency_key) constraint
-- (Postgres auto-names this subscriptions_idempotency_key_key)
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_idempotency_key_key;

-- Scope uniqueness to (idempotency_key, tenant_id, subscriber_identity).
-- NULL values are allowed (each NULL is considered distinct in Postgres UNIQUE).
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_idempotency_key_scoped
    UNIQUE (idempotency_key, tenant_id, subscriber_identity);

-- Ensure indexes exist (already created by migration 018; IF NOT EXISTS is a no-op).
CREATE INDEX IF NOT EXISTS idx_subscriptions_target
    ON subscriptions (target, tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_subscriber
    ON subscriptions (subscriber_identity, tenant_id);
