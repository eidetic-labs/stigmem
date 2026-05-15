CREATE TABLE IF NOT EXISTS plugin_migrations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_name    TEXT NOT NULL,
    plugin_version TEXT NOT NULL,
    migration_id   INTEGER NOT NULL,
    backend        TEXT NOT NULL,
    checksum       TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    applied_at     TEXT NOT NULL,
    UNIQUE(plugin_name, backend, migration_id)
);

CREATE INDEX IF NOT EXISTS idx_plugin_migrations_plugin
    ON plugin_migrations(plugin_name, backend);
