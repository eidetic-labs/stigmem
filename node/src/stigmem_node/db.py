"""Database setup, migrations, and connection management.

The ``db()`` context manager and ``apply_migrations()`` now delegate to the
configured ``StorageBackend``.  SQLite remains the default; set
``STIGMEM_STORAGE_BACKEND=libsql`` (plus ``STIGMEM_LIBSQL_URL`` /
``STIGMEM_LIBSQL_AUTH_TOKEN``) to switch to libSQL / Turso.

Test fixtures patch ``stigmem_node.db.settings`` to override the backend
and database path without touching the environment.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

from .settings import settings as settings
from .storage import make_backend

# Resolved once at import time; exposed for test fixtures that need the path.
_MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


@contextmanager
def db() -> Generator[Any, None, None]:
    """Yield a transaction-scoped, SQLite-API-compatible connection.

    Passes the current module-level ``settings`` to ``make_backend`` so that
    test fixtures can redirect the backend by patching ``db_mod.settings``.
    """
    with make_backend(_settings=settings).connection() as conn:
        yield conn


def apply_migrations(db_path: str | None = None) -> None:
    """Apply any un-applied numbered SQL migrations from migrations/.

    When *db_path* is given, always uses SQLite at that path (backward-compat
    for CLI tools and test fixtures).  When omitted, honours ``settings``.
    """
    make_backend(db_path=db_path, _settings=settings).apply_migrations(_MIGRATIONS_DIR)


def get_or_create_federation_keypair(db_path: str | None = None) -> tuple[str, str]:
    """Return (pubkey_b64url, privkey_b64url), generating and persisting if needed."""
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    with make_backend(db_path=db_path, _settings=settings).connection() as conn:
        pub_row = conn.execute(
            "SELECT value FROM node_meta WHERE key='federation_pubkey'"
        ).fetchone()
        priv_row = conn.execute(
            "SELECT value FROM node_meta WHERE key='federation_privkey'"
        ).fetchone()
        if pub_row and priv_row:
            return str(pub_row["value"]), str(priv_row["value"])

        privkey = Ed25519PrivateKey.generate()
        pubkey = privkey.public_key()
        priv_b64 = (
            base64.urlsafe_b64encode(
                privkey.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
            )
            .decode()
            .rstrip("=")
        )
        pub_b64 = (
            base64.urlsafe_b64encode(pubkey.public_bytes(Encoding.Raw, PublicFormat.Raw))
            .decode()
            .rstrip("=")
        )
        conn.execute(
            "INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_pubkey', ?)",
            (pub_b64,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_privkey', ?)",
            (priv_b64,),
        )

    return pub_b64, priv_b64


def get_or_create_node_id(db_path: str | None = None) -> str:
    """Return the stable node UUID, creating it on first run."""
    with make_backend(db_path=db_path, _settings=settings).connection() as conn:
        row = conn.execute("SELECT value FROM node_meta WHERE key='node_id'").fetchone()
        if row:
            return str(row["value"])
        node_id = f"stigmem:node:{uuid.uuid4()}"
        conn.execute("INSERT INTO node_meta (key, value) VALUES ('node_id', ?)", (node_id,))

    return node_id
