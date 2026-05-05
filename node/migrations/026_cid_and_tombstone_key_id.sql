-- Stigmem Phase 13 — content-addressing (spec §25) + tombstone key_id (spec §23.2.1 rev 14)
--
-- Execution order (§25.7.1): this migration applies after 025_rtbf_tombstones_retractions.sql.
-- It is safe to apply on a DB that already has the tombstones and fact_retractions tables.

-- §25.3.1: add cid column to facts (nullable during backfill window)
ALTER TABLE facts ADD COLUMN cid TEXT;

-- §25.3.1: dual-addressing alias table
CREATE TABLE IF NOT EXISTS fact_cid_aliases (
  fact_id  TEXT NOT NULL REFERENCES facts(id),
  cid      TEXT NOT NULL,
  PRIMARY KEY (fact_id, cid)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_cid_aliases_cid ON fact_cid_aliases(cid);
CREATE INDEX IF NOT EXISTS idx_fact_cid_aliases_fact_id ON fact_cid_aliases(fact_id);

-- §23.2.1 rev 14 (F-8): key_id is now a REQUIRED field on TombstoneRecord.
-- The column is nullable here to preserve compatibility with rows written before this migration.
-- New writes MUST supply a non-null key_id (enforced at the application layer, §23.2.1).
ALTER TABLE tombstones ADD COLUMN key_id TEXT;

-- Index to support CID-based fact lookups without joining fact_cid_aliases
CREATE INDEX IF NOT EXISTS idx_facts_cid ON facts(cid) WHERE cid IS NOT NULL;
