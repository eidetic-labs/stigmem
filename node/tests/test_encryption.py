"""Tests for encryption-at-rest (Phase 8).

Test coverage:
  - Key derivation (Argon2id determinism, 32-byte output)
  - KMS URI loading (env:// scheme)
  - Startup refusal when encryption=on but no key source configured
  - SQLite encrypted DB: readable with correct key
  - SQLite encrypted DB: unreadable by plain sqlite3 (SQLCipher skip if not installed)
  - libSQL encrypted DB: connection succeeds (skips if libsql-experimental absent)

Run encrypted conformance suite::

    pip install 'stigmem-node[encryption,sqlcipher]'
    pytest --encrypt=on

Run encryption-specific tests only::

    pytest tests/test_encryption.py
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import pytest

import stigmem_node.db as db_mod
import stigmem_node.main as main_mod
import stigmem_node.settings as settings_module
from stigmem_node.storage import make_backend
from stigmem_node.storage.encryption import _reset_key_cache, derive_key, load_key

Settings = settings_module.Settings


_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

_PASSPHRASE_ENV = "_STIGMEM_ENC_TEST_PASSPHRASE"
_PASSPHRASE = "unit-test-passphrase-not-for-production"
_RAW_HEX_KEY = "a" * 64  # 32 bytes, all 0xaa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enc_settings(db_file: str, backend: str = "sqlite") -> Settings:
    return Settings(
        db_path=db_file,
        storage_backend=backend,
        at_rest_encryption="on",
        at_rest_key_passphrase_env=_PASSPHRASE_ENV,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Ensure key cache is clean before and after each test."""
    _reset_key_cache()
    yield  # type: ignore[misc]
    _reset_key_cache()


@pytest.fixture()
def passphrase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_PASSPHRASE_ENV, _PASSPHRASE)


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


class TestDeriveKey:
    def test_returns_32_bytes(self) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        key = derive_key(b"test-passphrase")
        assert len(key) == 32

    def test_deterministic(self) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        k1 = derive_key(b"same-passphrase")
        k2 = derive_key(b"same-passphrase")
        assert k1 == k2

    def test_different_passphrases_yield_different_keys(self) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        k1 = derive_key(b"passphrase-a")
        k2 = derive_key(b"passphrase-b")
        assert k1 != k2

    def test_key_is_bytes_not_str(self) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        key = derive_key(b"any-passphrase")
        assert isinstance(key, bytes)


# ---------------------------------------------------------------------------
# load_key — source selection and error paths
# ---------------------------------------------------------------------------


class TestLoadKey:
    def test_passphrase_env_returns_32_bytes(self, passphrase_env: None) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_passphrase_env=_PASSPHRASE_ENV,
        )
        key = load_key(s)
        assert len(key) == 32

    def test_kms_env_uri_returns_raw_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("_STIGMEM_ENC_KMS_VAR", _RAW_HEX_KEY)
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_ENC_KMS_VAR",
        )
        key = load_key(s)
        assert key == bytes.fromhex(_RAW_HEX_KEY)
        assert len(key) == 32

    def test_kms_takes_priority_over_passphrase(
        self, monkeypatch: pytest.MonkeyPatch, passphrase_env: None
    ) -> None:
        monkeypatch.setenv("_STIGMEM_ENC_KMS_VAR", _RAW_HEX_KEY)
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_passphrase_env=_PASSPHRASE_ENV,
            at_rest_key_kms_uri="env://_STIGMEM_ENC_KMS_VAR",
        )
        key = load_key(s)
        assert key == bytes.fromhex(_RAW_HEX_KEY)

    def test_no_source_raises(self) -> None:
        s = Settings(at_rest_encryption="on")
        with pytest.raises(RuntimeError, match="no key source"):
            load_key(s)

    def test_kms_missing_env_var_raises(self) -> None:
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_MISSING_XYZ",
        )
        with pytest.raises(RuntimeError, match="_STIGMEM_MISSING_XYZ"):
            load_key(s)

    def test_kms_invalid_hex_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("_STIGMEM_ENC_BAD", "not-hex-data")
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_ENC_BAD",
        )
        with pytest.raises(RuntimeError, match="valid hex"):
            load_key(s)

    def test_kms_wrong_length_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("_STIGMEM_ENC_SHORT", "deadbeef")  # 4 bytes
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_ENC_SHORT",
        )
        with pytest.raises(RuntimeError, match="4 bytes"):
            load_key(s)

    def test_unsupported_kms_scheme_raises(self) -> None:
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_kms_uri="aws-kms://arn:aws:kms:us-east-1:123:key/abc",
        )
        with pytest.raises(RuntimeError, match="Unsupported KMS URI"):
            load_key(s)

    def test_passphrase_env_missing_raises(self) -> None:
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_passphrase_env="_STIGMEM_DEFINITELY_MISSING",
        )
        # Ensure it's not accidentally set
        os.environ.pop("_STIGMEM_DEFINITELY_MISSING", None)
        with pytest.raises(RuntimeError, match="_STIGMEM_DEFINITELY_MISSING"):
            load_key(s)

    def test_result_is_cached(self, passphrase_env: None) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        s = Settings(
            at_rest_encryption="on",
            at_rest_key_passphrase_env=_PASSPHRASE_ENV,
        )
        k1 = load_key(s)
        k2 = load_key(s)
        assert k1 is k2  # same object — cached


# ---------------------------------------------------------------------------
# make_backend() startup validation
# ---------------------------------------------------------------------------


class TestMakeBackendStartupValidation:
    def test_refuses_start_without_key_source(self, tmp_path: Path) -> None:
        s = Settings(db_path=str(tmp_path / "enc.db"), at_rest_encryption="on")
        with pytest.raises(RuntimeError, match="no key source"):
            make_backend(_settings=s)

    def test_plaintext_backend_ignores_encryption_fields(self, tmp_path: Path) -> None:
        """Backward-compat: explicit db_path skips encryption entirely."""
        db_file = str(tmp_path / "plain.db")
        backend = make_backend(db_path=db_file)
        backend.apply_migrations(_MIGRATIONS_DIR)
        with backend.connection() as conn:
            conn.execute("SELECT 1")

    def test_settings_validator_rejects_invalid_mode(self) -> None:
        with pytest.raises(Exception, match="at_rest_encryption"):
            Settings(at_rest_encryption="yes")


# ---------------------------------------------------------------------------
# SQLite encrypted backend
# ---------------------------------------------------------------------------


class TestSQLiteEncryptedBackend:
    def test_encrypted_db_readable_with_correct_key(
        self, tmp_path: Path, passphrase_env: None
    ) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        pytest.importorskip("sqlcipher3", reason="sqlcipher3 not installed")

        db_file = str(tmp_path / "enc.db")
        s = _enc_settings(db_file)
        backend = make_backend(_settings=s)
        backend.apply_migrations(_MIGRATIONS_DIR)

        fact_id = str(uuid.uuid4())
        with backend.connection() as conn:
            conn.execute(
                "INSERT INTO facts "
                "(id, entity, relation, value_type, value_v, source, timestamp, confidence, scope) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                (fact_id, "agent:alice", "name", "string", "Alice", "agent:alice", 1.0, "local"),
            )

        _reset_key_cache()
        backend2 = make_backend(_settings=_enc_settings(db_file))
        with backend2.connection() as conn:
            row = conn.execute("SELECT value_v FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row is not None
        assert row["value_v"] == "Alice"

    def test_encrypted_db_unreadable_by_plain_sqlite3(
        self, tmp_path: Path, passphrase_env: None
    ) -> None:
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        pytest.importorskip("sqlcipher3", reason="sqlcipher3 not installed")

        db_file = str(tmp_path / "enc.db")
        backend = make_backend(_settings=_enc_settings(db_file))
        backend.apply_migrations(_MIGRATIONS_DIR)

        with backend.connection() as conn:
            conn.execute(
                "INSERT INTO facts "
                "(id, entity, relation, value_type, value_v, source, timestamp, confidence, scope) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                (
                    str(uuid.uuid4()),
                    "agent:bob",
                    "name",
                    "string",
                    "Bob",
                    "agent:bob",
                    1.0,
                    "local",
                ),
            )

        # Plain sqlite3 must not be able to read the encrypted file.
        plain = sqlite3.connect(db_file)
        with pytest.raises(sqlite3.DatabaseError):
            plain.execute("SELECT * FROM facts").fetchall()
        plain.close()

    def test_api_roundtrip_with_encrypted_backend(
        self, tmp_path: Path, passphrase_env: None
    ) -> None:
        """Full API-level roundtrip via TestClient with encrypted storage."""
        pytest.importorskip("argon2", reason="argon2-cffi not installed")
        pytest.importorskip("sqlcipher3", reason="sqlcipher3 not installed")

        from fastapi.testclient import TestClient

        db_file = str(tmp_path / "enc_api.db")
        s = _enc_settings(db_file)
        backend = make_backend(_settings=s)
        backend.apply_migrations(_MIGRATIONS_DIR)

        original = settings_module.settings
        settings_module.settings = s  # type: ignore[assignment]
        db_mod.settings = s  # type: ignore[assignment]
        try:
            app = main_mod.create_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.post(
                    "/v1/facts",
                    json={
                        "scope": "local",
                        "entity": "agent:test",
                        "relation": "role",
                        "value": "engineer",
                        "source": "agent:test",
                    },
                )
                assert resp.status_code == 200
                resp2 = c.get("/v1/facts?entity=agent:test&relation=role")
                assert resp2.status_code == 200
                facts = resp2.json()["facts"]
                assert len(facts) == 1
                assert facts[0]["value"] == "engineer"
        finally:
            settings_module.settings = original  # type: ignore[assignment]
            db_mod.settings = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# libSQL encrypted backend
# ---------------------------------------------------------------------------


class TestLibSQLEncryptedBackend:
    def test_libsql_encrypted_local_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """libSQL local mode with encryption_key — boot and basic read/write."""
        pytest.importorskip("libsql_experimental", reason="libsql-experimental not installed")
        monkeypatch.setenv("_STIGMEM_ENC_KMS_VAR", _RAW_HEX_KEY)

        db_file = str(tmp_path / "enc_libsql.db")
        s = Settings(
            db_path=db_file,
            storage_backend="libsql",
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_ENC_KMS_VAR",
        )
        backend = make_backend(_settings=s)
        backend.apply_migrations(_MIGRATIONS_DIR)

        fact_id = str(uuid.uuid4())
        with backend.connection() as conn:
            conn.execute(
                "INSERT INTO facts "
                "(id, entity, relation, value_type, value_v, source, timestamp, confidence, scope) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                (fact_id, "agent:carol", "lang", "string", "Python", "agent:carol", 1.0, "local"),
            )

        _reset_key_cache()
        s2 = Settings(
            db_path=db_file,
            storage_backend="libsql",
            at_rest_encryption="on",
            at_rest_key_kms_uri="env://_STIGMEM_ENC_KMS_VAR",
        )
        backend2 = make_backend(_settings=s2)
        with backend2.connection() as conn:
            row = conn.execute("SELECT value_v FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row is not None
        assert row["value_v"] == "Python"
