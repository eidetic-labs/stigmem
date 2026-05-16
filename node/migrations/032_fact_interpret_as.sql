-- Stigmem reference node — ADR-003 fact interpretation marker

ALTER TABLE facts
    ADD COLUMN interpret_as TEXT NOT NULL DEFAULT 'content'
    CHECK (interpret_as IN ('content', 'instruction'));

CREATE INDEX IF NOT EXISTS idx_facts_interpret_as
    ON facts(interpret_as);
