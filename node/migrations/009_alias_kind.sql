-- Stigmem reference node — Phase 6 F5: fuzzy entity resolver (spec §2.6)
-- Migration 007: add kind column to entity_aliases to distinguish pre-v0.7 migration
-- aliases from user-defined semantic aliases (e.g. user:alice ≡ user:a.smith).
--
-- 'migration' — populated by normalize_entities_sweep (pre-v0.7 backward compat)
-- 'user'      — registered via POST /v1/aliases (human-defined semantic equivalences)

ALTER TABLE entity_aliases ADD COLUMN kind TEXT NOT NULL DEFAULT 'migration';
