-- Stigmem Phase 13 — tombstone revocation signing (spec §23.2.5, F-2/F-4 remediation)
--
-- Adds key_id to tombstone_revocations to support Ed25519-signed revocations.
-- Nullable for backward compatibility with rows written before this migration.
-- New writes MUST supply key_id (enforced at application layer).

ALTER TABLE tombstone_revocations ADD COLUMN key_id TEXT;
