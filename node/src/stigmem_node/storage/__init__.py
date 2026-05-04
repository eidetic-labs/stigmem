"""Storage backend registry and factory.

Usage::

    from stigmem_node.storage import make_backend

    # Relies on settings.storage_backend (and related env vars)
    backend = make_backend(_settings=settings)

    with backend.connection() as conn:
        conn.execute("SELECT ...")

    # Explicit path always returns a SQLiteBackend (backward-compat for
    # CLI tools and test fixtures that create their own temp databases)
    backend = make_backend(db_path="/tmp/test.db")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import StorageBackend
from .libsql_backend import LibSQLBackend
from .sqlite_backend import SQLiteBackend

if TYPE_CHECKING:
    pass

__all__ = ["StorageBackend", "SQLiteBackend", "LibSQLBackend", "make_backend"]


def make_backend(
    db_path: str | None = None,
    _settings: Any | None = None,
) -> StorageBackend:
    """Return the appropriate ``StorageBackend`` instance.

    Args:
        db_path: When provided, always returns a ``SQLiteBackend`` at this
            path.  This preserves backward-compatibility for CLI tools,
            ``apply_migrations(db_path=…)`` calls, and test fixtures that
            supply a temporary database path directly.
        _settings: A ``Settings`` object to read ``storage_backend``,
            ``db_path``, ``libsql_url``, and ``libsql_auth_token`` from.
            Defaults to the live ``stigmem_node.settings.settings`` singleton,
            which means test fixtures can control backend selection by
            patching ``db_mod.settings`` as they already do.
    """
    # An explicit path always means SQLite — backward-compat guarantee.
    if db_path is not None:
        return SQLiteBackend(db_path)

    if _settings is None:
        from stigmem_node.settings import settings  # lazy to avoid import cycles

        _settings = settings

    backend_name: str = getattr(_settings, "storage_backend", "sqlite")
    path: str = _settings.db_path

    if backend_name == "libsql":
        return LibSQLBackend(
            db_path=path,
            sync_url=getattr(_settings, "libsql_url", ""),
            auth_token=getattr(_settings, "libsql_auth_token", ""),
        )

    return SQLiteBackend(path)
