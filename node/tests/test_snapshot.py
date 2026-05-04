"""Tests for signed-snapshot backup/restore (Phase 8 — ACM-185)."""

from __future__ import annotations

import base64
import json
import sqlite3
import tarfile
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from stigmem_node.snapshot import (
    SnapshotVerificationError,
    _CURSOR_ARTIFACT,
    _DB_ARTIFACT,
    snapshot_create,
    snapshot_restore,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_db(path: str) -> None:
    """Initialise a minimal stigmem DB with node_meta and schema_migrations."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS node_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL
        );
        INSERT OR IGNORE INTO schema_migrations (version, applied_at)
        VALUES ('001_init', '2026-01-01T00:00:00+00:00');
        """
    )
    conn.commit()
    conn.close()


def _make_secondary_key_file(tmp_path: Path) -> tuple[Path, str]:
    """Write a raw Ed25519 private key to a file; return (path, pub_b64url)."""
    priv = Ed25519PrivateKey.generate()
    raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub_b64 = _b64url_encode(priv.public_key().public_bytes_raw())
    key_file = tmp_path / "secondary.key"
    key_file.write_text(_b64url_encode(raw))
    return key_file, pub_b64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_file(tmp_path: Path) -> str:
    path = str(tmp_path / "stigmem.db")
    _make_db(path)
    return path


# ---------------------------------------------------------------------------
# snapshot_create — structure and content
# ---------------------------------------------------------------------------


def test_create_produces_tarball(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    result = snapshot_create(db_path=db_file, out_path=out)
    assert result == out
    assert out.exists()
    assert tarfile.is_tarfile(str(out))


def test_create_tarball_contains_required_members(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    with tarfile.open(out, "r:gz") as tf:
        names = tf.getnames()

    assert "manifest.json" in names
    assert _DB_ARTIFACT in names
    assert _CURSOR_ARTIFACT in names


def test_manifest_structure(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    with tarfile.open(out, "r:gz") as tf:
        mf = json.loads(tf.extractfile("manifest.json").read())  # type: ignore[union-attr]

    assert mf["version"] == 1
    assert "created_at" in mf
    assert "signer_pubkey" in mf
    assert "signature" in mf
    assert _DB_ARTIFACT in mf["artifacts"]
    assert _CURSOR_ARTIFACT in mf["artifacts"]
    for v in mf["artifacts"].values():
        assert v.startswith("sha256:")


def test_auto_named_output(db_file: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = snapshot_create(db_path=db_file)
    assert result.name.startswith("stigmem-snapshot-")
    assert result.suffix == ".gz"


def test_schema_cursor_captured(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    with tarfile.open(out, "r:gz") as tf:
        cursor = json.loads(tf.extractfile(_CURSOR_ARTIFACT).read())  # type: ignore[union-attr]

    assert "001_init" in cursor["applied_migrations"]


# ---------------------------------------------------------------------------
# snapshot_create — secondary signing key
# ---------------------------------------------------------------------------


def test_create_with_secondary_key(db_file: str, tmp_path: Path) -> None:
    key_file, expected_pub = _make_secondary_key_file(tmp_path)
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out, sign_with_key_path=key_file)

    with tarfile.open(out, "r:gz") as tf:
        mf = json.loads(tf.extractfile("manifest.json").read())  # type: ignore[union-attr]

    assert mf["signer_pubkey"] == expected_pub


# ---------------------------------------------------------------------------
# snapshot_restore — happy path
# ---------------------------------------------------------------------------


def test_restore_round_trip(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    restore_db = str(tmp_path / "restored.db")
    snapshot_restore(tarball_path=out, db_path=restore_db)

    conn = sqlite3.connect(restore_db)
    row = conn.execute("SELECT version FROM schema_migrations WHERE version='001_init'").fetchone()
    conn.close()
    assert row is not None


def test_restore_with_trusted_keys_file(db_file: str, tmp_path: Path) -> None:
    key_file, pub_b64 = _make_secondary_key_file(tmp_path)
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out, sign_with_key_path=key_file)

    trusted = tmp_path / "trusted.json"
    trusted.write_text(json.dumps([pub_b64]))

    restore_db = str(tmp_path / "restored.db")
    snapshot_restore(tarball_path=out, db_path=restore_db, trusted_keys_path=trusted)
    assert Path(restore_db).exists()


# ---------------------------------------------------------------------------
# snapshot_restore — tamper detection
# ---------------------------------------------------------------------------


def _tamper_artifact(tarball: Path, artifact_name: str, out: Path) -> None:
    """Rebuild tarball with one artifact's bytes corrupted."""
    import copy
    import io

    replacement = b"TAMPERED_CONTENT_XYZ"
    with tarfile.open(tarball, "r:gz") as tf_in, tarfile.open(out, "w:gz") as tf_out:
        for member in tf_in.getmembers():
            if member.name == artifact_name:
                patched = copy.copy(member)
                patched.size = len(replacement)
                tf_out.addfile(patched, fileobj=io.BytesIO(replacement))
            else:
                content = tf_in.extractfile(member)
                tf_out.addfile(member, content)


def _tamper_manifest_signature(tarball: Path, out: Path) -> None:
    """Rebuild tarball with the manifest signature zeroed out."""
    import io

    with tarfile.open(tarball, "r:gz") as tf_in, tarfile.open(out, "w:gz") as tf_out:
        for member in tf_in.getmembers():
            if member.name == "manifest.json":
                mf = json.loads(tf_in.extractfile(member).read())  # type: ignore[union-attr]
                mf["signature"] = "AAAAAAAAAA"
                raw = json.dumps(mf).encode()
                member.size = len(raw)
                tf_out.addfile(member, fileobj=io.BytesIO(raw))
            else:
                tf_out.addfile(member, tf_in.extractfile(member))


def test_restore_rejects_tampered_db_artifact(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    tampered = tmp_path / "tampered.tar.gz"
    _tamper_artifact(out, _DB_ARTIFACT, tampered)

    with pytest.raises(SnapshotVerificationError, match="hash mismatch"):
        snapshot_restore(tarball_path=tampered, db_path=str(tmp_path / "x.db"))


def test_restore_rejects_tampered_signature(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    tampered = tmp_path / "tampered_sig.tar.gz"
    _tamper_manifest_signature(out, tampered)

    with pytest.raises(SnapshotVerificationError, match="signature is invalid"):
        snapshot_restore(tarball_path=tampered, db_path=str(tmp_path / "x.db"))


def test_restore_rejects_wrong_trusted_key(db_file: str, tmp_path: Path) -> None:
    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    unrelated_priv = Ed25519PrivateKey.generate()
    unrelated_pub = _b64url_encode(unrelated_priv.public_key().public_bytes_raw())
    trusted = tmp_path / "trusted_wrong.json"
    trusted.write_text(json.dumps([unrelated_pub]))

    # node_meta won't contain a matching key when db_path is a fresh file
    fresh_db = str(tmp_path / "fresh.db")
    _make_db(fresh_db)

    with pytest.raises(SnapshotVerificationError, match="signature is invalid"):
        snapshot_restore(
            tarball_path=out, db_path=fresh_db, trusted_keys_path=trusted
        )


def test_force_unverified_restores_despite_tamper(
    db_file: str, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    out = tmp_path / "snap.tar.gz"
    snapshot_create(db_path=db_file, out_path=out)

    tampered = tmp_path / "tampered.tar.gz"
    _tamper_artifact(out, _CURSOR_ARTIFACT, tampered)

    restore_db = str(tmp_path / "forced.db")
    with caplog.at_level(logging.WARNING, logger="stigmem_node.snapshot"):
        snapshot_restore(tarball_path=tampered, db_path=restore_db, force_unverified=True)

    assert Path(restore_db).exists()
    assert "SECURITY WARNING" in caplog.text


# ---------------------------------------------------------------------------
# CLI integration — argument parsing
# ---------------------------------------------------------------------------


def test_cli_snapshot_create_parses(db_file: str, tmp_path: Path) -> None:
    import sys
    from unittest.mock import patch

    out = str(tmp_path / "via_cli.tar.gz")
    with patch.object(sys, "argv", ["stigmem", "snapshot", "create", "--out", out, "--db", db_file]):
        from stigmem_node.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["snapshot", "create", "--out", out, "--db", db_file])
        assert args.out == out
        assert args.db == db_file


def test_cli_snapshot_restore_parses(tmp_path: Path) -> None:
    snap = str(tmp_path / "snap.tar.gz")
    from stigmem_node.cli import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        ["snapshot", "restore", "--from", snap, "--db", str(tmp_path / "r.db")]
    )
    assert args.from_path == snap
    assert not args.force_unverified
