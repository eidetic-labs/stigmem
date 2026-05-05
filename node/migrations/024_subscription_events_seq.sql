-- Stigmem reference node — explicit seq column on subscription_events
-- Migration 024: replaces implicit SQLite rowid usage with an explicit
-- monotonic integer so cursor-based pagination works on all backends.

ALTER TABLE subscription_events ADD COLUMN seq INTEGER;

-- Backfill existing rows deterministically (ordered by created_at then id).
-- New rows are set by the application after INSERT using cursor.lastrowid
-- (SQLite) or the sequence DEFAULT (PostgreSQL via migrations_pg/024).
UPDATE subscription_events
SET    seq = (
    SELECT COUNT(*)
    FROM   subscription_events AS s2
    WHERE  s2.created_at < subscription_events.created_at
        OR (s2.created_at = subscription_events.created_at AND s2.id <= subscription_events.id)
);

CREATE INDEX IF NOT EXISTS idx_sub_events_seq ON subscription_events(seq);
