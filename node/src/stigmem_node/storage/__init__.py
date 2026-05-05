"""Storage backend registry and factory.

Usage::

    from stigmem_node.storage import make_backend

    # Relies on settings.storage_backend (and related env vars)
    backend = make_backend(_settings=settings)

    with backend.connection() as conn:
        conn.execute("SELECT ...")

    # Explicit path always returns a plaintext SQLiteBackend (backward-compat
    # for CLI tools and test fixtures that create their own temp databases).
    backend = make_backend(db_path="/tmp/test.db")
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .base import StorageBackend
from .libsql_backend import LibSQLBackend
from .postgres_backend import PostgresBackend
from .sqlite_backend import SQLiteBackend

if TYPE_CHECKING:
    pass

__all__ = ["StorageBackend", "SQLiteBackend", "LibSQLBackend", "PostgresBackend", "make_backend"]


def make_backend(
    db_path: str | None = None,
    _settings: Any | None = None,
) -> StorageBackend:
    """Return the appropriate ``StorageBackend`` instance.

    Args:
        db_path: When provided, always returns a plaintext ``SQLiteBackend``
            at this path.  This preserves backward-compatibility for CLI tools,
            ``apply_migrations(db_path=…)`` calls, and test fixtures that
            supply a temporary database path directly.  Encryption settings
            are ignored when *db_path* is given.
        _settings: A ``Settings`` object to read ``storage_backend``,
            ``db_path``, ``libsql_url``, ``libsql_auth_token``, and
            ``at_rest_encryption`` from.  Defaults to the live
            ``stigmem_node.settings.settings`` singleton so that test fixtures
            can control backend selection by patching ``db_mod.settings``.

    Raises:
        RuntimeError: If ``at_rest_encryption="on"`` is set but no key source
            is configured (``at_rest_key_passphrase_env`` / ``at_rest_key_kms_uri``
            both empty).  The node refuses to start in this state.
    """
    # An explicit path always means plaintext SQLite — backward-compat guarantee.
    if db_path is not None:
        return SQLiteBackend(db_path)

    if _settings is None:
        from stigmem_node.settings import settings  # lazy to avoid import cycles

        _settings = settings

    # Resolve encryption key (Phase 8 / ACM-184).  load_key() raises immediately
    # if encryption is on but no key source is configured — this surfaces the
    # misconfiguration at app startup (apply_migrations call) rather than lazily.
    encryption_key: bytes | None = None
    if getattr(_settings, "at_rest_encryption", "off") == "on":
        from .encryption import load_key

        encryption_key = load_key(_settings)

    backend_name: str = getattr(_settings, "storage_backend", "sqlite")
    path: str = _settings.db_path

    if backend_name == "libsql":
        return LibSQLBackend(
            db_path=path,
            sync_url=getattr(_settings, "libsql_url", ""),
            auth_token=getattr(_settings, "libsql_auth_token", ""),
            encryption_key=encryption_key,
        )

    if backend_name == "postgres":
        # Accept STIGMEM_PG_DSN, STIGMEM_DATABASE_URL, or bare DATABASE_URL.
        dsn: str = (
            getattr(_settings, "pg_dsn", "")
            or getattr(_settings, "database_url", "")
            or os.environ.get("DATABASE_URL", "")
        )
        if not dsn:
            raise RuntimeError(
                "storage_backend='postgres' requires a connection string. "
                "Set STIGMEM_PG_DSN, STIGMEM_DATABASE_URL, or DATABASE_URL."
            )
        schema: str = getattr(_settings, "pg_schema", "public")
        embed_enabled_pg: bool = getattr(_settings, "embed_enabled", False)
        embed_dimension_pg: int = int(getattr(_settings, "embed_dimension", 768))
        return PostgresBackend(
            dsn=dsn,
            schema=schema,
            pool_min=int(getattr(_settings, "postgres_pool_min", 2)),
            pool_max=int(getattr(_settings, "postgres_pool_max", 10)),
            embed_enabled=embed_enabled_pg,
            embed_dimension=embed_dimension_pg,
        )

    embed_enabled: bool = getattr(_settings, "embed_enabled", False)
    embed_dimension: int = int(getattr(_settings, "embed_dimension", 768))
    return SQLiteBackend(
        path,
        encryption_key=encryption_key,
        embed_enabled=embed_enabled,
        embed_dimension=embed_dimension,
    )
