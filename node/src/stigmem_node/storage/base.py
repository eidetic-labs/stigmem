"""StorageBackend abstract base — the seam between node logic and persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class StorageBackend(ABC):
    """Pluggable storage seam.

    Implement this class to add a new persistence backend.  The interface covers:
      - Connection lifecycle  (``connection``)
      - Transaction semantics (commit on clean exit, rollback on exception)
      - Migration runner      (``apply_migrations``)
      - Snapshot hooks        (``export_snapshot`` / ``import_snapshot``)

    Fact CRUD and query primitives are expressed as raw SQL through the
    SQLite-API-compatible connection object yielded by ``connection()``.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Short identifier returned in ``/.well-known/stigmem`` and logs, e.g. ``'sqlite'``."""
        raise NotImplementedError

    @abstractmethod
    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """Yield a SQLite-API-compatible connection.

        Contract:
          * Commits on clean exit.
          * Rolls back and re-raises on any exception.
          * Always closes the underlying connection.
          * Rows must support column access by name (``row["column"]``).
        """
        raise NotImplementedError

    @abstractmethod
    def apply_migrations(self, migrations_dir: Path) -> None:
        """Run all un-applied numbered ``.sql`` files found in *migrations_dir*.

        Implementations must be idempotent — already-applied versions (tracked in
        ``schema_migrations``) must be silently skipped.
        """
        raise NotImplementedError

    def export_snapshot(self, dest: Path) -> None:
        """Export a point-in-time snapshot to *dest*.

        Optional hook for backup/DR workflows (e.g. Fly.io volume snapshots).
        Raise ``NotImplementedError`` if the backend does not support it.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support snapshot export")

    def import_snapshot(self, src: Path) -> None:
        """Restore from a snapshot at *src*.

        Optional hook.  Raise ``NotImplementedError`` if unsupported.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support snapshot import")
