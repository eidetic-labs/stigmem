-- Stigmem reference node v0.9 — Memory Garden primitive
-- Migration 004: gardens, garden_members (spec §17)

CREATE TABLE IF NOT EXISTS gardens (
    id          TEXT PRIMARY KEY,
    slug        TEXT NOT NULL,
    name        TEXT NOT NULL,
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public')),
    description TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(slug)
);

CREATE INDEX IF NOT EXISTS idx_gardens_slug ON gardens(slug);

CREATE TABLE IF NOT EXISTS garden_members (
    garden_id   TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    entity_uri  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin','writer','reader')),
    added_by    TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    PRIMARY KEY (garden_id, entity_uri)
);

CREATE INDEX IF NOT EXISTS idx_garden_members_entity ON garden_members(entity_uri);
