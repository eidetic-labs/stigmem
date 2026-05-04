"""SQLite implementation of StorageBackend — the default backend."""

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
    connection.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @property
    def backend_name(self) -> str:
        return "sqlite"

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_migrations(self, migrations_dir: Path) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
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
        """Online backup via ``sqlite3.Connection.backup()``."""
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
