-- Migration 025: add created_at column to peers table (Phase 12 §22.1)
-- Backfill with established_at (equivalent semantic for existing rows).
ALTER TABLE peers ADD COLUMN created_at TEXT;
UPDATE peers SET created_at = established_at WHERE created_at IS NULL;
