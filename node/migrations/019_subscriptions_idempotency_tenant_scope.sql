-- Stigmem reference node — fix idempotency_key uniqueness scope (security R1/R2)
--
-- Migration 018 created `idempotency_key TEXT UNIQUE`, a table-wide unique constraint.
-- Problems:
--   R1: A key claimed in tenant A prevents any entity in tenant B from using the same
--       key value — cross-tenant collision causes an unhandled IntegrityError (500).
--   R2: The application-level lookup was not scoped to subscriber_identity, allowing
--       entity B to receive entity A's subscription record via idempotency key.
--
-- Fix: scope uniqueness to (idempotency_key, tenant_id, subscriber_identity).
-- This means each identity within a tenant owns their own key namespace, preventing
-- both cross-tenant and cross-entity collisions.
--
-- SQLite does not support DROP CONSTRAINT, so we recreate the table.

PRAGMA foreign_keys = OFF;

BEGIN;

CREATE TABLE subscriptions_new (
    id                      TEXT PRIMARY KEY,
    subscriber_identity     TEXT NOT NULL,
    target                  TEXT NOT NULL,
    target_kind             TEXT NOT NULL DEFAULT 'scope',
    on_change               TEXT NOT NULL,
    delivery_address        TEXT NOT NULL,
    idempotency_key         TEXT,
    created_at              TEXT NOT NULL,
    last_delivered_at       TEXT,
    tenant_id               TEXT NOT NULL DEFAULT 'default',
    circuit_open            INTEGER NOT NULL DEFAULT 0,
    consecutive_failures    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (idempotency_key, tenant_id, subscriber_identity)
);

INSERT INTO subscriptions_new SELECT * FROM subscriptions;

DROP TABLE subscriptions;
ALTER TABLE subscriptions_new RENAME TO subscriptions;

CREATE INDEX idx_subscriptions_target     ON subscriptions (target, tenant_id);
CREATE INDEX idx_subscriptions_subscriber ON subscriptions (subscriber_identity, tenant_id);

COMMIT;

PRAGMA foreign_keys = ON;
