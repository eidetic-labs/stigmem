-- Stigmem reference node — fact audit detail column
-- Migration 015: add structured detail column to fact_audit_log for event-specific payloads
-- (e.g. trust_score snapshot on quarantine_ingest events)

ALTER TABLE fact_audit_log ADD COLUMN detail TEXT;
