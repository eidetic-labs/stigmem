-- Stigmem reference node v0.8 — N-node scope-propagation tracking
-- Migration 004: origin_node_id, origin_allowed_scopes, re_federation_blocked (spec §6.8.1, §10)
--
-- These columns let relay nodes enforce the scope-intersection rule: a fact MUST
-- only be re-federated to a peer if scope ∈ origin_allowed_scopes ∩ peer.allowed_scopes.
-- NULL values indicate locally-asserted facts (no federated origin); pre-v0.8 federated
-- facts also have NULL (treat as no restriction, rely on per-peer scope agreement).

ALTER TABLE facts ADD COLUMN origin_node_id        TEXT;            -- node_id of original assertor; NULL = local
ALTER TABLE facts ADD COLUMN origin_allowed_scopes TEXT;            -- JSON array of scopes permitted at origin; NULL = local
ALTER TABLE facts ADD COLUMN re_federation_blocked INTEGER NOT NULL DEFAULT 0;  -- 1 = must not relay to third nodes

CREATE INDEX IF NOT EXISTS idx_facts_re_federation ON facts(re_federation_blocked, scope);
