-- Stigmem reference node — extends facts table for v0.9 (Memory Garden + Source Attestation)
-- Migration 011: adds garden_id and attested columns to facts (spec §17, §18)
--
-- Earlier migration 004_gardens.sql created the gardens and garden_members tables.
-- This migration completes the schema by linking facts to gardens and recording
-- per-fact source-attestation results.

ALTER TABLE facts ADD COLUMN garden_id TEXT;
CREATE INDEX IF NOT EXISTS idx_facts_garden ON facts(garden_id) WHERE garden_id IS NOT NULL;

-- attested: 1=true, 0=false, NULL=not-applicable (spec §18, §2.7)
ALTER TABLE facts ADD COLUMN attested INTEGER;
