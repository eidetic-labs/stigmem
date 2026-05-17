-- Stigmem Phase B §5.2a.2 — ADR-016 L1 append-only journal + projections.
--
-- These tables are the foundation for moving mutable derived fact state out of
-- facts. Later §5.2a slices refactor the remaining mutation paths and add hard
-- trigger enforcement.

CREATE TABLE IF NOT EXISTS fact_journal (
    id          TEXT PRIMARY KEY,
    fact_id     TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    event_ts    TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    actor_uri   TEXT,
    source      TEXT,
    scope       TEXT,
    cid         TEXT,
    body_json   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_journal_fact_id ON fact_journal(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_journal_tenant_ts ON fact_journal(tenant_id, event_ts);

CREATE TABLE IF NOT EXISTS fact_validity_overrides (
    fact_id     TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    valid_until TEXT,
    confidence  REAL CHECK(confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    reason      TEXT,
    updated_at  TEXT NOT NULL,
    updated_by  TEXT
);

CREATE TABLE IF NOT EXISTS fact_embedding_status (
    fact_id           TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    embedding_missing INTEGER NOT NULL CHECK(embedding_missing IN (0, 1)),
    updated_at        TEXT NOT NULL,
    last_error        TEXT,
    updated_by        TEXT
);

CREATE INDEX IF NOT EXISTS idx_fact_embedding_status_missing
    ON fact_embedding_status(embedding_missing) WHERE embedding_missing = 1;

CREATE TABLE IF NOT EXISTS fact_recall_signals (
    fact_id          TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    last_recalled_at TEXT,
    recall_count     INTEGER NOT NULL DEFAULT 0 CHECK(recall_count >= 0),
    salience         REAL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_cid_backfill (
    fact_id      TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    status       TEXT NOT NULL CHECK(status IN ('pending', 'complete', 'failed', 'skipped')),
    attempted_at TEXT,
    error        TEXT,
    updated_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_cid_backfill_status ON fact_cid_backfill(status);

CREATE TABLE IF NOT EXISTS fact_quarantine_status (
    fact_id              TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    quarantine_garden_id TEXT,
    quarantine_status    TEXT,
    quarantine_reason    TEXT,
    quarantine_acted_by  TEXT,
    quarantine_acted_at  TEXT,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_quarantine_status_state
    ON fact_quarantine_status(quarantine_status);

CREATE TABLE IF NOT EXISTS fact_garden_membership (
    fact_id    TEXT PRIMARY KEY REFERENCES facts(id) ON DELETE CASCADE,
    garden_id  TEXT,
    updated_at TEXT NOT NULL,
    updated_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_fact_garden_membership_garden
    ON fact_garden_membership(garden_id) WHERE garden_id IS NOT NULL;
