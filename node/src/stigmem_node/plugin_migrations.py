"""Plugin migration lifecycle ledger and application."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from packaging.version import InvalidVersion, Version

from .plugins import Migration, PluginMigrationError
from .storage import StorageBackend


@dataclass(frozen=True, slots=True)
class _MigrationRecord:
    plugin_name: str
    plugin_version: str
    migration_id: int
    backend: str
    checksum: str


def apply_registered_plugin_migrations(
    backend: StorageBackend,
    migrations: Iterable[Migration],
    *,
    plugin_order: Iterable[str] = (),
    plugin_versions: dict[str, str] | None = None,
) -> None:
    """Apply plugin-declared migrations with checksum and downgrade checks."""

    ordered = _ordered_migrations(
        migrations,
        backend_name=backend.backend_name,
        plugin_order=plugin_order,
        plugin_versions=plugin_versions or {},
    )
    with backend.connection() as conn:
        _ensure_plugin_migrations_table(conn)
        applied = _load_applied(conn, backend.backend_name)
        _validate_no_duplicate_declarations(ordered)
        _validate_no_downgrades(ordered, applied)
        for migration in ordered:
            key = (migration.plugin_name, migration.backend, migration.migration_id)
            checksum = _checksum(migration.sql)
            existing = applied.get(key)
            if existing is not None:
                if existing.checksum != checksum:
                    raise PluginMigrationError(
                        "plugin migration checksum mismatch for "
                        f"{migration.plugin_name}:{migration.migration_id}"
                    )
                continue
            conn.execute(migration.sql)
            conn.execute(
                "INSERT INTO plugin_migrations "
                "(plugin_name, plugin_version, migration_id, backend, checksum, "
                "description, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    migration.plugin_name,
                    migration.plugin_version,
                    migration.migration_id,
                    migration.backend,
                    checksum,
                    migration.description,
                    datetime.now(UTC).isoformat(),
                ),
            )


def _ensure_plugin_migrations_table(conn: Any) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS plugin_migrations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_name    TEXT NOT NULL,
            plugin_version TEXT NOT NULL,
            migration_id   INTEGER NOT NULL,
            backend        TEXT NOT NULL,
            checksum       TEXT NOT NULL,
            description    TEXT NOT NULL DEFAULT '',
            applied_at     TEXT NOT NULL,
            UNIQUE(plugin_name, backend, migration_id)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_plugin_migrations_plugin "
        "ON plugin_migrations(plugin_name, backend)"
    )


def _load_applied(
    conn: Any,
    backend_name: str,
) -> dict[tuple[str, str, int], _MigrationRecord]:
    rows = conn.execute(
        "SELECT plugin_name, plugin_version, migration_id, backend, checksum "
        "FROM plugin_migrations WHERE backend = ?",
        (backend_name,),
    ).fetchall()
    return {
        (row["plugin_name"], row["backend"], int(row["migration_id"])): _MigrationRecord(
            plugin_name=row["plugin_name"],
            plugin_version=row["plugin_version"],
            migration_id=int(row["migration_id"]),
            backend=row["backend"],
            checksum=row["checksum"],
        )
        for row in rows
    }


def _ordered_migrations(
    migrations: Iterable[Migration],
    *,
    backend_name: str,
    plugin_order: Iterable[str],
    plugin_versions: dict[str, str],
) -> list[Migration]:
    order_index = {name: idx for idx, name in enumerate(plugin_order)}
    filtered = [
        _with_plugin_version(migration, plugin_versions)
        for migration in migrations
        if migration.backend == backend_name
    ]
    return sorted(
        filtered,
        key=lambda migration: (
            order_index.get(migration.plugin_name, len(order_index)),
            migration.plugin_name,
            migration.migration_id,
        ),
    )


def _with_plugin_version(
    migration: Migration,
    plugin_versions: dict[str, str],
) -> Migration:
    if migration.plugin_version != "0.0.0":
        return migration
    version = plugin_versions.get(migration.plugin_name)
    if version is None:
        return migration
    return Migration(
        plugin_name=migration.plugin_name,
        migration_id=migration.migration_id,
        sql=migration.sql,
        description=migration.description,
        plugin_version=version,
        backend=migration.backend,
    )


def _validate_no_duplicate_declarations(migrations: list[Migration]) -> None:
    seen: dict[tuple[str, str, int], str] = {}
    for migration in migrations:
        key = (migration.plugin_name, migration.backend, migration.migration_id)
        checksum = _checksum(migration.sql)
        previous = seen.get(key)
        if previous is not None and previous != checksum:
            raise PluginMigrationError(
                "duplicate plugin migration declaration with different SQL for "
                f"{migration.plugin_name}:{migration.migration_id}"
            )
        seen[key] = checksum


def _validate_no_downgrades(
    migrations: list[Migration],
    applied: dict[tuple[str, str, int], _MigrationRecord],
) -> None:
    latest_applied_id: dict[tuple[str, str], int] = {}
    latest_applied_version: dict[tuple[str, str], Version] = {}
    for record in applied.values():
        plugin_key = (record.plugin_name, record.backend)
        latest_applied_id[plugin_key] = max(
            latest_applied_id.get(plugin_key, record.migration_id),
            record.migration_id,
        )
        latest_applied_version[plugin_key] = max(
            latest_applied_version.get(plugin_key, _parse_version(record.plugin_version)),
            _parse_version(record.plugin_version),
        )

    declared_ids: dict[tuple[str, str], set[int]] = {}
    declared_versions: dict[tuple[str, str], Version] = {}
    for migration in migrations:
        plugin_key = (migration.plugin_name, migration.backend)
        declared_ids.setdefault(plugin_key, set()).add(migration.migration_id)
        declared_versions[plugin_key] = max(
            declared_versions.get(plugin_key, _parse_version(migration.plugin_version)),
            _parse_version(migration.plugin_version),
        )

    for plugin_key, applied_id in latest_applied_id.items():
        declared = declared_ids.get(plugin_key)
        if declared and max(declared) < applied_id:
            raise PluginMigrationError(
                f"plugin migration downgrade refused for {plugin_key[0]}: "
                f"applied migration {applied_id} is newer than declared {max(declared)}"
            )

    for plugin_key, applied_version in latest_applied_version.items():
        declared_version = declared_versions.get(plugin_key)
        if declared_version is not None and declared_version < applied_version:
            raise PluginMigrationError(
                f"plugin version downgrade refused for {plugin_key[0]}: "
                f"applied {applied_version} is newer than declared {declared_version}"
            )


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _parse_version(raw: str) -> Version:
    try:
        return Version(raw)
    except InvalidVersion as exc:
        raise PluginMigrationError(f"invalid plugin migration version {raw!r}") from exc
