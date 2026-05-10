"""Tests for `stigmem auth bootstrap-key` CLI subcommand.

Surfaced as issue #105 during 2026-05-10 dogfooding: a fresh install with
`STIGMEM_AUTH_REQUIRED=true` (the default; see #104) had no documented
path to mint the first admin key without docker-exec'ing into the
container and calling `create_api_key()` in a Python REPL. This CLI
subcommand closes the catch-22.

Test surface:
- Mints a key on an empty api_keys table; raw key written to stdout
- Refuses (exit code 1) when api_keys is non-empty
- Honours `--entity-uri` and `--permissions` overrides
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

import stigmem_node.cli as cli_mod
import stigmem_node.db as db_mod
from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations


@pytest.fixture()
def fresh_db(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> str:
    """Migrated SQLite DB with no rows in api_keys. Patches the settings
    `db_path` so `db()` / `create_api_key()` resolve to this temp file."""
    path = str(tmp_path) + "/cli-test.db"  # type: ignore[operator]
    apply_migrations(db_path=path)
    # Patch the runtime settings.db_path that db() reads through make_backend.
    import stigmem_node.settings as settings_mod
    monkeypatch.setattr(settings_mod.settings, "db_path", path)
    monkeypatch.setattr(db_mod, "settings", settings_mod.settings)
    yield path


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Build args, call the command function, return (exit_code, stdout, stderr)."""
    parser = cli_mod._build_parser()
    args = parser.parse_args(argv)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = args.func(args)
    return rc, out.getvalue(), err.getvalue()


def test_bootstrap_key_mints_on_empty_table(fresh_db: str) -> None:
    rc, stdout, stderr = _run(["auth", "bootstrap-key"])
    assert rc == 0
    raw_key = stdout.strip()
    # SHA-256 hex digest of a UUID4 → 32 hex chars (the implementation uses uuid4().hex)
    assert len(raw_key) == 32, f"raw key has unexpected length: {len(raw_key)}"
    assert all(c in "0123456789abcdef" for c in raw_key), "raw key is not hex"
    assert "minted admin key" in stderr
    assert "agent:admin" in stderr
    assert "admin" in stderr and "write" in stderr and "read" in stderr

    # The key should be usable: hashing it should match a row in api_keys.
    import hashlib
    import sqlite3

    conn = sqlite3.connect(fresh_db)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    rows = conn.execute(
        "SELECT entity_uri, permissions FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "agent:admin"


def test_bootstrap_key_refuses_on_non_empty_table(fresh_db: str) -> None:
    # Pre-populate the table by minting a key via the same internal path.
    create_api_key(entity_uri="agent:existing", permissions=["read"])
    rc, stdout, stderr = _run(["auth", "bootstrap-key"])
    assert rc == 1
    assert stdout == ""  # no key emitted
    assert "api_keys table is not empty" in stderr
    assert "Bootstrap is one-shot" in stderr
    assert "POST /v1/auth/keys" in stderr


def test_bootstrap_key_honors_entity_uri_override(fresh_db: str) -> None:
    rc, stdout, stderr = _run(
        ["auth", "bootstrap-key", "--entity-uri", "agent:custom-bootstrap"]
    )
    assert rc == 0
    assert "agent:custom-bootstrap" in stderr


def test_bootstrap_key_honors_permissions_override(fresh_db: str) -> None:
    rc, stdout, stderr = _run(
        ["auth", "bootstrap-key", "--permissions", "read"]
    )
    assert rc == 0
    raw_key = stdout.strip()
    # Verify the persisted permissions are exactly what we passed
    import hashlib
    import json as _json
    import sqlite3

    conn = sqlite3.connect(fresh_db)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = conn.execute(
        "SELECT permissions FROM api_keys WHERE key_hash = ?", (key_hash,)
    ).fetchone()
    conn.close()
    assert row is not None
    perms = _json.loads(row[0])
    assert perms == ["read"]
