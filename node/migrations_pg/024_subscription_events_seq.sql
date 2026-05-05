-- Stigmem reference node — explicit seq column on subscription_events (Postgres dialect)
-- Migration 024: uses BIGSERIAL sequence so seq is auto-populated on INSERT.

CREATE SEQUENCE IF NOT EXISTS subscription_events_seq_seq;

ALTER TABLE subscription_events
    ADD COLUMN IF NOT EXISTS seq BIGINT DEFAULT nextval('subscription_events_seq_seq');

CREATE INDEX IF NOT EXISTS idx_sub_events_seq ON subscription_events(seq);
