-- Stigmem reference node — atomic subscription-delivery claim (issue #47)
--
-- Background
-- ----------
-- The original delivery path performed a non-atomic SELECT + UPDATE on
-- ``subscription_events`` rows: ``deliver_pending`` selected rows in state
-- ``pending`` then later transitioned them to ``delivered``.  Two concurrent
-- callers — typically the background ``sweep_loop`` task and a synchronous
-- test/admin invocation of ``deliver_pending`` — could observe the same
-- row in their respective SELECTs and each deliver it once, yielding
-- duplicate webhook POSTs (`call_count == 2` in the flaky tombstone tests).
--
-- The same race is a real production concern once additional delivery
-- workers exist (per-tenant pools, admin replay endpoints, or plugin-driven
-- alternative dispatchers under ADR-011 C1 — the ``subscription_*`` hook
-- family will eventually fire here).  Idempotency must live below the hook
-- layer so that a given event fires plugin handlers at most once.
--
-- Fix
-- ---
-- Introduce a ``delivering`` intermediate state plus a ``claimed_at``
-- timestamp.  A worker atomically transitions ``pending → delivering`` via
-- a single ``UPDATE … WHERE id IN (SELECT … LIMIT N) RETURNING …`` query;
-- SQLite/libsql serialize writes, so two concurrent claimers receive
-- disjoint row sets (or one receives zero).  After delivery the row moves
-- to ``delivered`` (success) or back to ``pending`` with a new
-- ``next_retry_at`` (failure / retry).
--
-- A stale-claim sweep at the top of ``deliver_pending`` reverts rows that
-- have been in ``delivering`` longer than the configured timeout (default
-- 300 s), so a crashed worker does not strand events forever.

ALTER TABLE subscription_events ADD COLUMN claimed_at TEXT;

-- Replace the pending-only index with one that also serves the stale-claim
-- recovery query (``WHERE delivery_status='delivering' AND claimed_at < ?``).
DROP INDEX IF EXISTS idx_sub_events_pending;
CREATE INDEX idx_sub_events_status_retry
    ON subscription_events (delivery_status, next_retry_at);
CREATE INDEX idx_sub_events_claimed
    ON subscription_events (delivery_status, claimed_at);
