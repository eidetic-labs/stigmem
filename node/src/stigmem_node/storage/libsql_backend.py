"""libSQL / Turso adapter for StorageBackend.

Supports two modes:
  * **Local** — ``db_path`` only; behaves like SQLite but via the libsql client.
  * **Embedded-replica** — ``db_path`` + ``sync_url`` + ``auth_token``; local
    SQLite file kept in sync with a Turso database.  Drop-in for Fly.io
    persistent volumes.

Encryption-at-rest is enabled by passing *encryption_key* (32 bytes).  The key
is forwarded to ``libsql.connect()`` as a hex string.  Both local and
embedded-replica modes support encryption; the Turso cloud primary uses its own
server-side encryption independently of the local replica key.

Install the optional dependency before use::

    pip install "stigmem-node[libsql]"
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

from .base import StorageBackend


def _split_sql(sql: str) -> list[str]:
    """Split a SQL script into individual statements, stripping comments.

    libsql-experimental does not expose ``executescript()``, so we split
    manually.  Migration files contain only DDL with no embedded semicolons
    inside string literals, so a simple split is safe.
    """
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return [stmt.strip() for stmt in sql.split(";") if stmt.strip()]


class _LibSQLRow:
    """Dict-like row wrapper that supports ``row["col"]`` and ``row[i]`` access.

    libsql-experimental's ``row_factory`` protocol mirrors sqlite3: the factory
    is called as ``factory(cursor, row_tuple)`` for each fetched row.
    """

    __slots__ = ("_data", "_values")

    def __init__(self, cursor: Any, row: tuple) -> None:
        cols = [d[0] for d in cursor.description]
        self._values: tuple = row
        self._data: dict[str, Any] = dict(zip(cols, row))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def __iter__(self) -> Any:
        return iter(self._values)

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class LibSQLBackend(StorageBackend):
    """libSQL backend (Turso-compatible).

    In embedded-replica mode (``sync_url`` set) the local file acts as the
    read/write store; the client syncs with Turso on every new connection.
    In local mode (no ``sync_url``) the behaviour is equivalent to SQLite.

    Pass *encryption_key* (32 bytes) to enable at-rest encryption for the local
    replica file.  Requires ``libsql-experimental >= 0.0.4`` or a build that
    exposes the ``encryption_key`` parameter in ``libsql.connect()``.
    """

    def __init__(
        self,
        db_path: str,
        sync_url: str = "",
        auth_token: str = "",  # nosec B107 — empty string is the correct default for optional Turso auth
        encryption_key: bytes | None = None,
    ) -> None:
        self._db_path = db_path
        self._sync_url = sync_url
        self._auth_token = auth_token
        self._encryption_key = encryption_key

    @property
    def backend_name(self) -> str:
        return "libsql"

    def _connect(self) -> Any:
        try:
            import libsql_experimental as libsql  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "libsql-experimental is required for the libSQL backend. "
                "Install it with: pip install 'stigmem-node[libsql]'"
            ) from exc

        enc_kwargs: dict[str, str] = {}
        if self._encryption_key is not None:
            enc_kwargs["encryption_key"] = self._encryption_key.hex()

        if self._sync_url:
            conn = libsql.connect(
                database=self._db_path,
                sync_url=self._sync_url,
                auth_token=self._auth_token,
                **enc_kwargs,
            )
            conn.sync()
        else:
            conn = libsql.connect(database=self._db_path, **enc_kwargs)

        conn.row_factory = _LibSQLRow
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_migrations(self, migrations_dir: Path) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    version    TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )"""
            )
            conn.commit()

            applied = {
                row["version"]
                for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            }

            for f in sorted(migrations_dir.glob("*.sql")):
                version = f.stem
                if version in applied:
                    continue
                for stmt in _split_sql(f.read_text()):
                    conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(UTC).isoformat()),
                )
                conn.commit()
        finally:
            conn.close()
