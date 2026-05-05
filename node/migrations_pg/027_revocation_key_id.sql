-- Stigmem Phase 13 — tombstone revocation signing (spec §23.2.5, F-2/F-4 remediation)
ALTER TABLE tombstone_revocations ADD COLUMN IF NOT EXISTS key_id TEXT;
