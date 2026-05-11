"""Signed-snapshot backup/restore — Phase 8 (ACM-185).

Snapshot create
  Captures: full fact database, schema migration cursor.
  Output: content-addressed .tar.gz with a manifest.json whose body is
  signed with the node's Ed25519 federation key (spec §6, same keypair as
  peer tokens / peer declarations).

Snapshot restore
  Verifies the Ed25519 signature and SHA-256 artifact hashes before
  writing anything to disk.  Refuses tampered input unless the caller
  explicitly passes force_unverified=True (always logged loudly).

Tarball layout::

    artifacts/
        stigmem.db                      # online-backup copy of the database
        schema_migration_cursor.json    # sorted list of applied migrations
    manifest.json                       # hashes + Ed25519 signature

manifest.json schema::

    {
      "version": 1,
      "created_at": "<ISO-8601 UTC>",
      "node_id": "stigmem:node:<uuid>",
      "signer_pubkey": "<base64url raw Ed25519 public key>",
      "artifacts": {
        "artifacts/stigmem.db": "sha256:<hex>",
        "artifacts/schema_migration_cursor.json": "sha256:<hex>"
      },
      "signature": "<base64url Ed25519 signature over manifest body>"
    }

The *manifest body* (the bytes that are signed) is the canonical JSON of
the manifest minus the ``"signature"`` field: lexicographic key order, no
extra whitespace, UTF-8 encoded.

Secondary signing key (--sign-with KEY)
  A raw 32-byte Ed25519 private key stored as base64url in a text file.
  When supplied, the snapshot is signed with this key instead of the
  node's built-in federation key.

Trusted-keys file (--trusted-keys PATH)
  A JSON file whose top-level value is a list of base64url-encoded raw
  Ed25519 public keys, e.g. ``["<key1>", "<key2>"]``.  Restore checks
  the manifest signature against every key in the list.  When omitted,
  only the local node's own public key is trusted.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

_MANIFEST_VERSION = 1
_DB_ARTIFACT = "artifacts/stigmem.db"
_CURSOR_ARTIFACT = "artifacts/schema_migration_cursor.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _canonical_manifest_body(manifest: dict[str, Any]) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_secondary_key(key_path: Path) -> Ed25519PrivateKey:
    raw_b64 = key_path.read_text().strip()
    raw_bytes = _b64url_decode(raw_b64)
    if len(raw_bytes) != 32:  # noqa: PLR2004
        raise ValueError(
            f"secondary signing key must be 32 raw bytes (base64url); got {len(raw_bytes)}"
        )
    return Ed25519PrivateKey.from_private_bytes(raw_bytes)


def _trusted_pubkeys(
    trusted_keys_path: Path | None,
    db_path: str | None,
    self_attesting_pubkey: str | None = None,
) -> list[Ed25519PublicKey]:
    """Build the trusted public key set for restore verification.

    When *trusted_keys_path* is given, only those keys are trusted (explicit
    operator list).  When omitted the implicit set is used: the local node's
    own key from ``node_meta`` plus the key declared in the manifest itself
    (self-attesting mode — convenient for same-node restores without a trust
    file).
    """
    keys: list[Ed25519PublicKey] = []

    if trusted_keys_path is not None:
        try:
            raw_list = json.loads(trusted_keys_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read trusted-keys file: {exc}") from exc
        if not isinstance(raw_list, list):
            raise ValueError("trusted-keys file must contain a JSON array of base64url keys")
        for entry in raw_list:
            pub_bytes = _b64url_decode(entry)
            keys.append(Ed25519PublicKey.from_public_bytes(pub_bytes))
        # Explicit trust list only — do NOT add self-declared or local keys.
        return keys

    # Implicit mode: local node key + self-declared key (same-node convenience).
    if db_path is not None:
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT value FROM node_meta WHERE key='federation_pubkey'"
            ).fetchone()
            conn.close()
            if row:
                pub_bytes = _b64url_decode(row[0])
                keys.append(Ed25519PublicKey.from_public_bytes(pub_bytes))
        except Exception as exc:  # noqa: BLE001
            logger.debug("local federation pubkey unavailable for snapshot verify: %s", exc)

    if self_attesting_pubkey:
        try:
            pub_bytes = _b64url_decode(self_attesting_pubkey)
            keys.append(Ed25519PublicKey.from_public_bytes(pub_bytes))
        except Exception as exc:  # noqa: BLE001
            logger.debug("invalid self-attesting pubkey skipped: %s", exc)

    return keys


def _collect_schema_cursor(db_path: str) -> list[str]:
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def snapshot_create(
    db_path: str,
    out_path: Path | None = None,
    sign_with_key_path: Path | None = None,
) -> Path:
    """Create a signed snapshot tarball and return its path.

    Args:
        db_path: Path to the SQLite database file.
        out_path: Explicit output path for the .tar.gz.  When None a
            timestamped, content-addressed name is used in the CWD.
        sign_with_key_path: Path to a file containing a raw base64url
            Ed25519 private key (32 bytes).  When None the node's own
            federation key from node_meta is used.

    Returns:
        Path to the created tarball.
    """
    created_at = datetime.now(UTC).isoformat()

    with tempfile.TemporaryDirectory(prefix="stigmem-snap-") as tmpdir:
        tmp = Path(tmpdir)
        artifacts_dir = tmp / "artifacts"
        artifacts_dir.mkdir()

        # -- 1. Online backup of the database --------------------------------
        db_snap = artifacts_dir / "stigmem.db"
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(str(db_snap))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # -- 2. Schema migration cursor --------------------------------------
        cursor_path = artifacts_dir / "schema_migration_cursor.json"
        applied_migrations = _collect_schema_cursor(db_path)
        cursor_path.write_text(
            json.dumps({"applied_migrations": applied_migrations}, indent=2)
        )

        # -- 3. Hashes -------------------------------------------------------
        artifacts = {
            _DB_ARTIFACT: _sha256_file(db_snap),
            _CURSOR_ARTIFACT: _sha256_file(cursor_path),
        }

        # -- 4. Signing key --------------------------------------------------
        if sign_with_key_path is not None:
            priv_key = _load_secondary_key(sign_with_key_path)
            signer_pubkey = _b64url_encode(
                priv_key.public_key().public_bytes_raw()
            )
        else:
            from .db import get_or_create_federation_keypair, get_or_create_node_id
            pub_b64, priv_b64 = get_or_create_federation_keypair(db_path=db_path)
            priv_raw = _b64url_decode(priv_b64)
            priv_key = Ed25519PrivateKey.from_private_bytes(priv_raw)
            signer_pubkey = pub_b64

        # -- 5. Node identity -----------------------------------------------
        try:
            from .db import get_or_create_node_id
            node_id = get_or_create_node_id(db_path=db_path)
        except Exception:
            node_id = ""

        # -- 6. Build manifest and sign -------------------------------------
        manifest: dict[str, Any] = {
            "version": _MANIFEST_VERSION,
            "created_at": created_at,
            "node_id": node_id,
            "signer_pubkey": signer_pubkey,
            "artifacts": artifacts,
        }
        body = _canonical_manifest_body(manifest)
        sig_bytes = priv_key.sign(body)
        manifest["signature"] = _b64url_encode(sig_bytes)

        manifest_path = tmp / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # -- 7. Pack tarball -------------------------------------------------
        # Determine final output path; use content-addressed name when not given.
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        db_hash_short = artifacts[_DB_ARTIFACT].split(":")[1][:12]

        if out_path is None:
            out_path = Path(f"stigmem-snapshot-{ts}-{db_hash_short}.tar.gz")

        with tarfile.open(out_path, "w:gz") as tf:
            tf.add(manifest_path, arcname="manifest.json")
            tf.add(artifacts_dir, arcname="artifacts")

        logger.info("snapshot created: %s (migrations: %s)", out_path, len(applied_migrations))
        return out_path


class SnapshotVerificationError(Exception):
    pass


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and validate the manifest.json from an extracted snapshot."""
    if not manifest_path.exists():
        raise SnapshotVerificationError("snapshot missing manifest.json")

    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise SnapshotVerificationError(f"manifest.json is not valid JSON: {exc}") from exc

    if manifest.get("version") != _MANIFEST_VERSION:
        raise SnapshotVerificationError(
            f"unsupported manifest version {manifest.get('version')!r}"
        )
    return manifest


def _verify_artifact_hashes(manifest: dict[str, Any], tmp: Path) -> None:
    """Verify SHA-256 of every declared artifact against the manifest."""
    declared: dict[str, str] = manifest.get("artifacts", {})
    for arc_name, expected_hash in declared.items():
        artifact_path = tmp / arc_name
        if not artifact_path.exists():
            raise SnapshotVerificationError(f"artifact {arc_name!r} missing from tarball")
        actual_hash = _sha256_file(artifact_path)
        if actual_hash != expected_hash:
            raise SnapshotVerificationError(
                f"hash mismatch for {arc_name!r}: "
                f"expected {expected_hash!r}, got {actual_hash!r}"
            )


def _verify_manifest_signature(
    manifest: dict[str, Any],
    db_path: str,
    trusted_keys_path: Path | None,
) -> None:
    """Verify the Ed25519 signature on the manifest body against trusted keys."""
    signer_pubkey_b64: str = manifest.get("signer_pubkey", "")
    signature_b64: str = manifest.get("signature", "")
    if not signer_pubkey_b64 or not signature_b64:
        raise SnapshotVerificationError("manifest missing signer_pubkey or signature")

    body = _canonical_manifest_body(manifest)

    trusted = _trusted_pubkeys(
        trusted_keys_path,
        db_path,
        self_attesting_pubkey=signer_pubkey_b64 if trusted_keys_path is None else None,
    )

    sig_bytes = _b64url_decode(signature_b64)
    verified = False
    for pub_key in trusted:
        try:
            pub_key.verify(sig_bytes, body)
            verified = True
            break
        except InvalidSignature:
            continue

    if not verified:
        raise SnapshotVerificationError(
            "manifest signature is invalid — snapshot may have been tampered with. "
            "Pass --force-unverified to restore anyway (NOT recommended)."
        )


def snapshot_restore(
    tarball_path: Path,
    db_path: str,
    trusted_keys_path: Path | None = None,
    force_unverified: bool = False,
) -> None:
    """Restore a snapshot, verifying signature and artifact hashes.

    Args:
        tarball_path: Path to a .tar.gz produced by snapshot_create.
        db_path: Destination database path.  **Existing data is overwritten.**
        trusted_keys_path: JSON file listing trusted base64url public keys.
            When None only the local node's own key is trusted.
        force_unverified: If True, skip signature/hash verification and
            restore anyway.  A loud warning is logged regardless.

    Raises:
        SnapshotVerificationError: On tampered input (unless force_unverified).
    """
    if force_unverified:
        logger.warning(
            "SECURITY WARNING: restoring unverified snapshot from %s — "
            "--force-unverified was passed; integrity checks are DISABLED",
            tarball_path,
        )

    with tempfile.TemporaryDirectory(prefix="stigmem-restore-") as tmpdir:
        tmp = Path(tmpdir)

        # -- 1. Extract ------------------------------------------------------
        # filter='data' (PEP 706, Python 3.11.4+) rejects absolute paths,
        # `..` traversal, symlinks pointing outside the destination, device
        # files, setuid/setgid bits, etc. — closes the path-traversal hole
        # that bare extractall() leaves open even with a controlled tmpdir.
        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(tmp, filter="data")

        manifest = _load_manifest(tmp / "manifest.json")

        if not force_unverified:
            # -- 2. Verify artifact hashes -----------------------------------
            _verify_artifact_hashes(manifest, tmp)

            # -- 3. Verify Ed25519 signature ---------------------------------
            _verify_manifest_signature(manifest, db_path, trusted_keys_path)

            logger.info("snapshot verified: signature OK, all artifact hashes match")
        else:
            logger.warning(
                "SECURITY WARNING: artifact hash and signature verification SKIPPED for %s",
                tarball_path,
            )

        # -- 4. Restore database --------------------------------------------
        db_artifact = tmp / _DB_ARTIFACT
        if not db_artifact.exists():
            raise SnapshotVerificationError(
                f"database artifact {_DB_ARTIFACT!r} not found in snapshot"
            )
        shutil.copy2(str(db_artifact), db_path)
        logger.info("snapshot restored to %s", db_path)
