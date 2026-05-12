from __future__ import annotations

from pathlib import Path

from stigmem_node.db import apply_migrations, collect_registered_plugin_migrations
from stigmem_node.plugins import Migration, PluginContext, PluginManifest
from stigmem_node.plugins.testing import stigmem_plugins


def test_migration_register_hook_collects_typed_migrations() -> None:
    def register(_ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name="sample",
                migration_id=1,
                sql="CREATE TABLE sample_plugin(id TEXT PRIMARY KEY)",
                description="sample plugin table",
            ),
        ]

    manifest = PluginManifest(
        name="migration-sample",
        version="1.0.0",
        hooks={"migration_register": register},
    )

    with stigmem_plugins([manifest]):
        migrations = collect_registered_plugin_migrations()

    assert migrations == [
        Migration(
            plugin_name="sample",
            migration_id=1,
            sql="CREATE TABLE sample_plugin(id TEXT PRIMARY KEY)",
            description="sample plugin table",
        )
    ]


def test_apply_migrations_fires_migration_register_without_changing_default(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def register(_ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        calls.append("migration_register")
        return value

    manifest = PluginManifest(
        name="migration-observer",
        version="1.0.0",
        hooks={"migration_register": register},
    )

    with stigmem_plugins([manifest]):
        apply_migrations(db_path=str(tmp_path / "test.db"))

    assert calls == ["migration_register"]
