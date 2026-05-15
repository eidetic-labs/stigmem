from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from stigmem_node.db import apply_migrations, collect_registered_plugin_migrations
from stigmem_node.plugins import Migration, PluginContext, PluginManifest, PluginMigrationError
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


def test_plugin_migration_first_apply_records_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    def register(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE first_apply_plugin(id TEXT PRIMARY KEY)",
                description="first apply table",
            ),
        ]

    manifest = PluginManifest(
        name="first-apply-plugin",
        version="1.2.3",
        hooks={"migration_register": register},
    )

    with stigmem_plugins([manifest]):
        apply_migrations(db_path=str(db_path))

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("first_apply_plugin",),
        ).fetchone()
        row = conn.execute(
            "SELECT plugin_name, plugin_version, migration_id, checksum "
            "FROM plugin_migrations WHERE plugin_name=?",
            ("first-apply-plugin",),
        ).fetchone()

    assert table is not None
    assert row is not None
    assert row["plugin_name"] == "first-apply-plugin"
    assert row["plugin_version"] == "1.2.3"
    assert row["migration_id"] == 1
    assert len(row["checksum"]) == 64


def test_plugin_migration_reapply_is_noop(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    def register(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE reapply_plugin(id TEXT PRIMARY KEY)",
                description="reapply table",
            ),
        ]

    manifest = PluginManifest(
        name="reapply-plugin",
        version="1.0.0",
        hooks={"migration_register": register},
    )

    with stigmem_plugins([manifest]):
        apply_migrations(db_path=str(db_path))
        apply_migrations(db_path=str(db_path))

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM plugin_migrations WHERE plugin_name=?",
            ("reapply-plugin",),
        ).fetchone()[0]

    assert count == 1


def test_plugin_migration_checksum_mismatch_is_refused(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    def register_original(
        ctx: PluginContext,
        value: list[Migration],
        **_: object,
    ) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE checksum_plugin(id TEXT PRIMARY KEY)",
                description="original",
            ),
        ]

    def register_changed(
        ctx: PluginContext,
        value: list[Migration],
        **_: object,
    ) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE checksum_plugin_changed(id TEXT PRIMARY KEY)",
                description="changed",
            ),
        ]

    first = PluginManifest(
        name="checksum-plugin",
        version="1.0.0",
        hooks={"migration_register": register_original},
    )
    second = PluginManifest(
        name="checksum-plugin",
        version="1.0.1",
        hooks={"migration_register": register_changed},
    )

    with stigmem_plugins([first]):
        apply_migrations(db_path=str(db_path))

    with stigmem_plugins([second]), pytest.raises(PluginMigrationError, match="checksum mismatch"):
        apply_migrations(db_path=str(db_path))


def test_plugin_migration_downgrade_is_refused(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    def register_v2(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE downgrade_plugin(id TEXT PRIMARY KEY)",
                description="base",
            ),
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=2,
                sql="CREATE TABLE downgrade_plugin_next(id TEXT PRIMARY KEY)",
                description="next",
            ),
        ]

    def register_v1(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="CREATE TABLE downgrade_plugin(id TEXT PRIMARY KEY)",
                description="base",
            ),
        ]

    first = PluginManifest(
        name="downgrade-plugin",
        version="2.0.0",
        hooks={"migration_register": register_v2},
    )
    second = PluginManifest(
        name="downgrade-plugin",
        version="1.0.0",
        hooks={"migration_register": register_v1},
    )

    with stigmem_plugins([first]):
        apply_migrations(db_path=str(db_path))

    with stigmem_plugins([second]), pytest.raises(PluginMigrationError, match="downgrade refused"):
        apply_migrations(db_path=str(db_path))


def test_plugin_migrations_apply_in_dependency_registration_order(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    def register_dep(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql=(
                    "CREATE TABLE plugin_order_log("
                    "seq INTEGER PRIMARY KEY AUTOINCREMENT, plugin TEXT NOT NULL)"
                ),
                description="order log",
            ),
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=2,
                sql="INSERT INTO plugin_order_log(plugin) VALUES ('dep-plugin')",
                description="dep marker",
            ),
        ]

    def register_addon(ctx: PluginContext, value: list[Migration], **_: object) -> list[Migration]:
        return [
            *value,
            Migration(
                plugin_name=ctx.plugin_name,
                migration_id=1,
                sql="INSERT INTO plugin_order_log(plugin) VALUES ('addon-plugin')",
                description="addon marker",
            ),
        ]

    dep = PluginManifest(
        name="dep-plugin",
        version="1.0.0",
        hooks={"migration_register": register_dep},
    )
    addon = PluginManifest(
        name="addon-plugin",
        version="1.0.0",
        depends_on=frozenset({"dep-plugin"}),
        hooks={"migration_register": register_addon},
    )

    with stigmem_plugins([dep, addon]):
        apply_migrations(db_path=str(db_path))

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT plugin FROM plugin_order_log ORDER BY seq").fetchall()

    assert [row[0] for row in rows] == ["dep-plugin", "addon-plugin"]
