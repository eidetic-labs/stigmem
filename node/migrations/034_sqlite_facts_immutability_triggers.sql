-- Stigmem Phase B §5.2a.3 — ADR-016 L2 SQLite immutability triggers.
--
-- The facts table is append-only after L1 projection retirement. Mutable
-- derived state belongs in projection tables. These triggers block direct
-- UPDATE/DELETE attempts and leave a fact_mutation_attempted audit row.
--
-- SQLite RAISE(ABORT) rolls back trigger-side audit inserts. RAISE(FAIL)
-- preserves the audit row while still rejecting the mutating statement.

CREATE TRIGGER IF NOT EXISTS facts_no_update
BEFORE UPDATE ON facts
BEGIN
    INSERT INTO fact_audit_log
        (id, fact_id, event_type, entity_uri, source, ts, tenant_id, detail)
    VALUES
        (
            'audit_' || lower(hex(randomblob(16))),
            OLD.id,
            'fact_mutation_attempted',
            NULL,
            'sqlite-trigger:facts_no_update',
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            COALESCE(OLD.tenant_id, 'default'),
            '{"operation":"UPDATE","table":"facts"}'
        );
    SELECT RAISE(FAIL, 'facts table is append-only; write projection tables instead of UPDATE facts');
END;

CREATE TRIGGER IF NOT EXISTS facts_no_delete
BEFORE DELETE ON facts
BEGIN
    INSERT INTO fact_audit_log
        (id, fact_id, event_type, entity_uri, source, ts, tenant_id, detail)
    VALUES
        (
            'audit_' || lower(hex(randomblob(16))),
            OLD.id,
            'fact_mutation_attempted',
            NULL,
            'sqlite-trigger:facts_no_delete',
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            COALESCE(OLD.tenant_id, 'default'),
            '{"operation":"DELETE","table":"facts"}'
        );
    SELECT RAISE(FAIL, 'facts table is append-only; write projection tables instead of DELETE FROM facts');
END;
