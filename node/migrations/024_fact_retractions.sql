-- Stigmem reference node — append-only fact retraction log (spec §24.2.1 c.3)
-- Migration 024 (spec 013c): records every retraction event — explicit reject
-- (quarantine/garden) and decay-sweeper confidence-floor drops.
-- Complements facts.confidence = 0.0 semantics; live-query behaviour unchanged.

CREATE TABLE IF NOT EXISTS fact_retractions (
    id           TEXT PRIMARY KEY,
    fact_id      TEXT NOT NULL REFERENCES facts(id),
    retracted_at TEXT NOT NULL,  -- ISO 8601 UTC
    retracted_by TEXT NOT NULL   -- entity URI or 'stigmem:system:decay'
);

CREATE INDEX IF NOT EXISTS idx_fact_retractions_fact_ts
    ON fact_retractions(fact_id, retracted_at);
