-- Stigmem reference node v0.7 — entity normalization support
-- Migration 003: entity_aliases table for pre-v0.7 migration tooling (spec §2.6.6)
--
-- New facts written after this migration have their entity/source normalized on ingest
-- by the strict normalizer (entity_normalizer.py). Pre-existing facts may have
-- non-canonical entity URIs; this table provides the alias mapping needed to locate
-- them via canonical queries during the migration window.

CREATE TABLE IF NOT EXISTS entity_aliases (
    raw_uri       TEXT NOT NULL,
    canonical_uri TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (raw_uri)
);

CREATE INDEX IF NOT EXISTS idx_entity_aliases_canonical ON entity_aliases(canonical_uri);
