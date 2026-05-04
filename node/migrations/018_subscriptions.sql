-- Stigmem reference node — subscription primitive (spec §20)
-- Migration 016: subscriptions + subscription_events tables

CREATE TABLE subscriptions (
    id                      TEXT PRIMARY KEY,
    subscriber_identity     TEXT NOT NULL,
    target                  TEXT NOT NULL,
    target_kind             TEXT NOT NULL DEFAULT 'scope',  -- 'scope' | 'entity'
    on_change               TEXT NOT NULL,                  -- 'webhook' | 'wake'
    delivery_address        TEXT NOT NULL,
    idempotency_key         TEXT UNIQUE,
    created_at              TEXT NOT NULL,
    last_delivered_at       TEXT,
    tenant_id               TEXT NOT NULL DEFAULT 'default',
    circuit_open            INTEGER NOT NULL DEFAULT 0,
    consecutive_failures    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_subscriptions_target ON subscriptions (target, tenant_id);
CREATE INDEX idx_subscriptions_subscriber ON subscriptions (subscriber_identity, tenant_id);

CREATE TABLE subscription_events (
    id                  TEXT PRIMARY KEY,
    subscription_id     TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,
    entity_uri          TEXT,
    fact_id             TEXT,
    payload             TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    delivered_at        TEXT,
    delivery_status     TEXT NOT NULL DEFAULT 'pending',
    delivery_attempts   INTEGER NOT NULL DEFAULT 0,
    next_retry_at       TEXT
);

CREATE INDEX idx_sub_events_pending ON subscription_events (delivery_status, next_retry_at);
CREATE INDEX idx_sub_events_replay ON subscription_events (subscription_id, created_at DESC);
