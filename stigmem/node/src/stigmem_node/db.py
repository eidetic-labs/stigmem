"""Database setup, migrations, and connection management."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Generator

from .settings import settings

# src/stigmem_node/db.py  →  ../../..  = node/  →  node/migrations/
_MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


@contextmanager
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.db_path)
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


def apply_migrations(db_path: str | None = None) -> None:
    """Apply any un-applied numbered SQL migrations from migrations/."""
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            )"""
        )
        conn.commit()

        applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}

        sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        for f in sql_files:
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


def get_or_create_node_id(db_path: str | None = None) -> str:
    """Return the stable node UUID, creating it on first run."""
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT value FROM node_meta WHERE key='node_id'").fetchone()
        if row:
            return str(row["value"])
        node_id = f"stigmem:node:{uuid.uuid4()}"
        conn.execute("INSERT INTO node_meta (key, value) VALUES ('node_id', ?)", (node_id,))
        conn.commit()
        return node_id
    finally:
        conn.close()
