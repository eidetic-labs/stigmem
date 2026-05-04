"""SQLite implementation of StorageBackend — the default backend.

When *encryption_key* is provided (32 bytes), the backend uses SQLCipher via
the ``sqlcipher3`` package instead of stdlib ``sqlite3``.  Install the extra
before enabling encryption::

    pip install 'stigmem-node[sqlcipher]'
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

from .base import StorageBackend


class SQLiteBackend(StorageBackend):
    """Default SQLite backend.

    Behaviour is identical to the pre-trait implementation in ``db.py``.
    Uses WAL journal mode and enforces foreign-key constraints on every
    connection.  When *encryption_key* is provided, SQLCipher is used
    transparently — the key is set via ``PRAGMA key`` immediately after open.
    """

    def __init__(self, db_path: str, encryption_key: bytes | None = None) -> None:
        self._db_path = db_path
        self._encryption_key = encryption_key

    @property
    def backend_name(self) -> str:
        return "sqlite"

    def _open_conn(self) -> Any:
        """Open and return a raw (un-transacted) connection, WAL + FK enabled."""
        if self._encryption_key is not None:
            try:
                import sqlcipher3 as _sc  # type: ignore[import]
            except ImportError as exc:
                raise RuntimeError(
                    "sqlcipher3 is required for SQLite encryption-at-rest. "
                    "Install it with: pip install 'stigmem-node[sqlcipher]'"
                ) from exc
            conn = _sc.connect(self._db_path)
            hex_key = self._encryption_key.hex()
            conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")  # noqa: S608
            conn.row_factory = _sc.Row
        else:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        conn = self._open_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_migrations(self, migrations_dir: Path) -> None:
        conn = self._open_conn()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    version    TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )"""
            )
            conn.commit()

            applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}

            for f in sorted(migrations_dir.glob("*.sql")):
                version = f.stem
                if version in applied:
                    continue
                conn.executescript(f.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(UTC).isoformat()),
                )
                conn.commit()
        finally:
            conn.close()

    def export_snapshot(self, dest: Path) -> None:
        """Online backup via ``sqlite3.Connection.backup()``.

        Encrypted databases produce encrypted snapshots (same key).
        """
        if self._encryption_key is not None:
            try:
                import sqlcipher3 as _sc  # type: ignore[import]
            except ImportError as exc:
                raise RuntimeError(
                    "sqlcipher3 is required to snapshot an encrypted SQLite database."
                ) from exc
            hex_key = self._encryption_key.hex()
            src_conn = _sc.connect(self._db_path)
            src_conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")  # noqa: S608
            dst_conn = _sc.connect(str(dest))
            dst_conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")  # noqa: S608
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()
        else:
            src_conn = sqlite3.connect(self._db_path)
            dst_conn = sqlite3.connect(str(dest))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()

    def import_snapshot(self, src: Path) -> None:
        """Restore by replacing the current database file."""
        import shutil

        shutil.copy2(str(src), self._db_path)
