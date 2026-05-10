"""Tests for `stigmem auth bootstrap-key` CLI subcommand.

Surfaced as issue #105 during 2026-05-10 dogfooding: a fresh install with
`STIGMEM_AUTH_REQUIRED=true` (the default; see #104) had no documented
path to register the first admin key. This subcommand closes the
catch-22.

Design note: the system never generates the key. The caller provides
the value via `--key` or `STIGMEM_BOOTSTRAP_KEY` env var; we hash and
store it. The CLI's job is registration, not generation. This eliminates
the "reveal channel" entirely — the credential never flows through any
output path of the command.

Test surface:
- Registers a key on empty api_keys table with `--key VALUE`
- Reads from STIGMEM_BOOTSTRAP_KEY env var as fallback
- Refuses (exit 2) with no key provided
- Refuses (exit 2) with key shorter than 16 chars
- Refuses (exit 1) when api_keys is non-empty
- Honours `--entity-uri` and `--permissions` overrides
"""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from contextlib import redirect_stderr, redirect_stdout

import pytest

import stigmem_node.cli as cli_mod
import stigmem_node.db as db_mod
from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations


@pytest.fixture()
def fresh_db(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> str:
    """Migrated SQLite DB with no rows in api_keys. Patches the settings
    `db_path` so `db()` / `register_api_key()` resolve to this temp file."""
    path = str(tmp_path) + "/cli-test.db"  # type: ignore[operator]
    apply_migrations(db_path=path)
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


def _row_for_key(db_path: str, raw_key: str) -> tuple[str, list[str]] | None:
    conn = sqlite3.connect(db_path)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = conn.execute(
        "SELECT entity_uri, permissions FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return row[0], json.loads(row[1])


# ── Happy path ────────────────────────────────────────────────────────────

def test_bootstrap_key_registers_provided_key(fresh_db: str) -> None:
    raw = "a" * 32  # 32 chars; clears the min-length check
    rc, stdout, stderr = _run(["auth", "bootstrap-key", "--key", raw])
    assert rc == 0
    # The raw key MUST NOT appear in stdout (the whole point of the refactor).
    assert raw not in stdout
    # Confirmation message has key_id, entity, permissions — but never the raw key.
    assert "Registered admin API key" in stderr
    assert "key_id=" in stderr
    assert raw not in stderr

    row = _row_for_key(fresh_db, raw)
    assert row is not None
    entity, perms = row
    assert entity == "agent:admin"
    assert perms == ["admin", "write", "read"]


def test_bootstrap_key_reads_env_var_fallback(
    fresh_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = "b" * 32
    monkeypatch.setenv("STIGMEM_BOOTSTRAP_KEY", raw)
    rc, stdout, stderr = _run(["auth", "bootstrap-key"])
    assert rc == 0
    assert raw not in stdout
    assert raw not in stderr
    assert _row_for_key(fresh_db, raw) is not None


# ── Refusal paths ─────────────────────────────────────────────────────────

def test_bootstrap_key_refuses_with_no_key_provided(
    fresh_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure no env-var bleed-through from the test environment
    monkeypatch.delenv("STIGMEM_BOOTSTRAP_KEY", raising=False)
    rc, stdout, stderr = _run(["auth", "bootstrap-key"])
    assert rc == 2
    assert "no key value provided" in stderr
    assert "openssl rand -hex 32" in stderr  # example must be in the error


def test_bootstrap_key_refuses_short_key(fresh_db: str) -> None:
    rc, stdout, stderr = _run(["auth", "bootstrap-key", "--key", "tooshort"])
    assert rc == 2
    assert "at least 16 characters" in stderr
    assert "openssl rand -hex 32" in stderr


def test_bootstrap_key_refuses_on_non_empty_table(fresh_db: str) -> None:
    # Pre-populate the table via the internal create_api_key (test-only path).
    create_api_key(entity_uri="agent:existing", permissions=["read"])
    raw = "c" * 32
    rc, stdout, stderr = _run(["auth", "bootstrap-key", "--key", raw])
    assert rc == 1
    assert stdout == ""
    assert "api_keys table is not empty" in stderr
    assert "Bootstrap is one-shot" in stderr
    assert "POST /v1/auth/keys" in stderr
    # Confirm the second key did NOT get registered
    assert _row_for_key(fresh_db, raw) is None


# ── Override flags ────────────────────────────────────────────────────────

def test_bootstrap_key_honors_entity_uri_override(fresh_db: str) -> None:
    raw = "d" * 32
    rc, _, stderr = _run(
        ["auth", "bootstrap-key", "--key", raw, "--entity-uri", "agent:custom"]
    )
    assert rc == 0
    assert "agent:custom" in stderr
    row = _row_for_key(fresh_db, raw)
    assert row is not None
    assert row[0] == "agent:custom"


def test_bootstrap_key_honors_permissions_override(fresh_db: str) -> None:
    raw = "e" * 32
    rc, _, _ = _run(
        ["auth", "bootstrap-key", "--key", raw, "--permissions", "read"]
    )
    assert rc == 0
    row = _row_for_key(fresh_db, raw)
    assert row is not None
    assert row[1] == ["read"]
