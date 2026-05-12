"""Phase 12 key-rotation tests — spec §22.2.

Covers the four acceptance paths:
  1. Single rotation — new-manifest dual-trust accepts old-key tokens; rejects post-window.
  2. Double rollover (A→B→C) — A-key tokens accepted in A's window; B-key tokens in B's window.
  3. Expired prior key — old-key tokens rejected once the dual-trust window closes.
  4. Mid-flight federation handshake — token issued just before rotation accepted after
     the peer receives the new manifest (dual-trust window still open).

Also covers:
  - KeyRotationLogEntry signing and structure.
  - rotate_key() dry-run produces correct artefacts without TL writes.
  - rotate_key() with local TL produces two log entries.
  - dual_trust_days < 90 is rejected.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

import stigmem_node.db as db_mod
from stigmem_node.identity.capability import (
    _DUAL_TRUST_DAYS,
    CapabilityTokenError,
    _token_signing_body,
    _verify_token_signature,
)
from stigmem_node.identity.key_rotation import (
    KeyRotationLogEntry,
    generate_key_id,
    rotate_key,
    sign_key_rotation_entry,
)
from stigmem_node.identity.manifest import (
    OrgManifest,
    RotationEvent,
    manifest_to_dict,
    sign_manifest,
    sign_rotation_event,
    verify_manifest,
    verify_rotation_chain,
)

apply_migrations = db_mod.apply_migrations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[Ed25519PrivateKey, str, str]:
    """Return (private_key, pub_b64url, priv_b64url)."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(
            priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        )
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return priv, pub_b64, priv_b64


def _make_manifest(
    priv: Ed25519PrivateKey,
    pub_b64: str,
    *,
    entity_uri: str = "https://example.org",
    entities: list[str] | None = None,
    key_id: str | None = None,
    days_valid: int = 365,
    rotation_events: list[RotationEvent] | None = None,
) -> OrgManifest:
    if key_id is None:
        key_id = generate_key_id(priv.public_key())
    now = datetime.now(UTC)
    m = OrgManifest(
        entity_uri=entity_uri,
        key_id=key_id,
        public_key=pub_b64,
        issued_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=(now + timedelta(days=days_valid)).isoformat().replace("+00:00", "Z"),
        entities=entities if entities is not None else [entity_uri],
        rotation_events=rotation_events or [],
    )
    sign_manifest(m, priv)
    return m


def _insert_token(conn: sqlite3.Connection, token_body: dict, priv: Ed25519PrivateKey) -> str:
    """Sign and insert a capability token into the DB. Returns the token JSON string."""
    signing_body = _token_signing_body(token_body)
    sig_bytes = priv.sign(signing_body)
    sig_b64 = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
    token_with_sig = {**token_body, "signature": sig_b64}
    token_json = json.dumps(token_with_sig, separators=(",", ":"))
    conn.execute(
        """INSERT INTO capability_tokens
           (id, token_json, issuer, subject, verb, object, issued_at, expiry, nonce, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            token_body["token_id"],
            token_json,
            token_body["issuer"],
            token_body["subject"],
            token_body.get("verb", "read"),
            token_body.get("object", "*"),
            datetime.now(UTC).isoformat(),
            token_body["expiry"],
            token_body["nonce"],
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    return token_json


def _make_token_body(
    issuer: str,
    subject: str,
    *,
    days_valid: int = 30,
) -> dict:
    now = datetime.now(UTC)
    return {
        "token_version": 1,
        "token_id": str(uuid.uuid4()),
        "issuer": issuer,
        "subject": subject,
        "verb": "read",
        "object": "*",
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expiry": (now + timedelta(days=days_valid)).isoformat().replace("+00:00", "Z"),
        "nonce": uuid.uuid4().hex + uuid.uuid4().hex,  # 64 hex chars
    }


def _setup_db(tmp_path: Path) -> tuple[sqlite3.Connection, str]:
    """Create a minimal DB with the capability_tokens table. Returns (conn, db_path)."""
    db_path = str(tmp_path / "test.db")
    apply_migrations(db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, db_path


# ---------------------------------------------------------------------------
# Unit tests — key_rotation module
# ---------------------------------------------------------------------------


class TestGenerateKeyId:
    def test_deterministic(self) -> None:
        priv, _, _ = _gen_keypair()
        kid1 = generate_key_id(priv.public_key())
        kid2 = generate_key_id(priv.public_key())
        assert kid1 == kid2

    def test_different_keys_different_ids(self) -> None:
        priv_a, _, _ = _gen_keypair()
        priv_b, _, _ = _gen_keypair()
        assert generate_key_id(priv_a.public_key()) != generate_key_id(priv_b.public_key())

    def test_format(self) -> None:
        priv, _, _ = _gen_keypair()
        kid = generate_key_id(priv.public_key())
        assert len(kid) == 16
        assert all(c in "0123456789abcdef" for c in kid)


class TestRotateKeyDryRun:
    def test_dry_run_no_tl_required(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        result = rotate_key(
            entity_uri="https://example.org",
            old_manifest=manifest_a,
            old_private_key=priv_a,
            dry_run=True,
        )
        assert result.manifest_log_entry is None
        assert result.rotation_tl_entry is None
        assert result.rotation_log_entry.manifest_log_index == -1

    def test_dry_run_new_manifest_valid(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        result = rotate_key(
            entity_uri="https://example.org",
            old_manifest=manifest_a,
            old_private_key=priv_a,
            dry_run=True,
        )
        verify_manifest(result.new_manifest)

    def test_dry_run_rotation_event_chain_valid(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)
        old_key_id = manifest_a.key_id

        result = rotate_key(
            entity_uri="https://example.org",
            old_manifest=manifest_a,
            old_private_key=priv_a,
            dry_run=True,
        )
        verify_rotation_chain(result.new_manifest, old_key_id, pub_a)

    def test_dry_run_rotation_event_stores_previous_pubkey(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        result = rotate_key(
            entity_uri="https://example.org",
            old_manifest=manifest_a,
            old_private_key=priv_a,
            dry_run=True,
        )
        evt = result.new_manifest.rotation_events[-1]
        assert evt.previous_public_key == pub_a

    def test_dual_trust_days_minimum_enforced(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        with pytest.raises(ValueError, match="dual_trust_days"):
            rotate_key(
                entity_uri="https://example.org",
                old_manifest=manifest_a,
                old_private_key=priv_a,
                dual_trust_days=89,
                dry_run=True,
            )

    def test_key_rotation_log_entry_fields(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        result = rotate_key(
            entity_uri="https://example.org",
            old_manifest=manifest_a,
            old_private_key=priv_a,
            dry_run=True,
        )
        entry = result.rotation_log_entry
        assert entry.event_type == "key_rotation"
        assert entry.entity_uri == "https://example.org"
        assert entry.old_key_id == manifest_a.key_id
        assert entry.new_key_id == result.new_manifest.key_id
        assert entry.manifest_log_index == -1


class TestRotateKeyWithLocalTL:
    def test_produces_two_tl_entries(self, tmp_path: Path) -> None:
        tl_path = tmp_path / "tl.jsonl"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        import stigmem_node.settings as settings_module

        Settings = settings_module.Settings

        orig = settings_module.settings
        settings_module.settings = Settings(tl_backend="local", tl_local_path=str(tl_path))  # type: ignore[assignment]
        try:
            result = rotate_key(
                entity_uri="https://example.org",
                old_manifest=manifest_a,
                old_private_key=priv_a,
            )
        finally:
            settings_module.settings = orig  # type: ignore[assignment]

        assert result.manifest_log_entry is not None
        assert result.rotation_tl_entry is not None
        lines = tl_path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_rotation_log_entry_signed_by_old_key(self, tmp_path: Path) -> None:
        tl_path = tmp_path / "tl.jsonl"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a)

        import stigmem_node.settings as settings_module

        Settings = settings_module.Settings

        orig = settings_module.settings
        settings_module.settings = Settings(tl_backend="local", tl_local_path=str(tl_path))  # type: ignore[assignment]
        try:
            result = rotate_key(
                entity_uri="https://example.org",
                old_manifest=manifest_a,
                old_private_key=priv_a,
            )
        finally:
            settings_module.settings = orig  # type: ignore[assignment]

        entry = result.rotation_log_entry
        # Re-sign with old key and compare — proves rotation_sig is by old key
        expected_sig = sign_key_rotation_entry(
            KeyRotationLogEntry(
                event_type=entry.event_type,
                entity_uri=entry.entity_uri,
                old_key_id=entry.old_key_id,
                new_key_id=entry.new_key_id,
                rotated_at=entry.rotated_at,
                dual_trust_expires_at=entry.dual_trust_expires_at,
                manifest_log_index=entry.manifest_log_index,
                rotation_sig="",
            ),
            priv_a,
        )
        assert entry.rotation_sig == expected_sig


# ---------------------------------------------------------------------------
# Path 1: Single rotation — dual-trust window acceptance and post-window rejection
# ---------------------------------------------------------------------------


class TestPath1SingleRotation:
    """§22.2 acceptance path 1: single A→B rotation."""

    def test_old_key_token_accepted_in_window(self, tmp_path: Path) -> None:
        conn, db_path = _setup_db(tmp_path)

        # Set up entity with key A
        entity_uri = "https://example.org"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a, entity_uri=entity_uri)

        # Issue token signed by key A
        token_body = _make_token_body(entity_uri, entity_uri)
        token_json = _insert_token(conn, token_body, priv_a)

        # Rotate to key B — rotated_at is NOW → window still open
        priv_b, pub_b, _ = _gen_keypair()
        key_b_id = generate_key_id(priv_b.public_key())
        rotated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        rot_sig = sign_rotation_event(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key_b64=pub_b,
            rotated_at=rotated_at,
            private_key=priv_a,
        )
        rotation_evt = RotationEvent(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=rot_sig,
            previous_public_key=pub_a,  # dual-trust key stored here
        )
        manifest_b = _make_manifest(
            priv_b,
            pub_b,
            entity_uri=entity_uri,
            rotation_events=[rotation_evt],
        )

        import stigmem_node.db as db_mod
        import stigmem_node.settings as settings_module

        Settings = settings_module.Settings

        orig = settings_module.settings
        settings_module.settings = Settings(db_path=db_path)  # type: ignore[assignment]
        db_mod.settings = settings_module.settings  # type: ignore[assignment]

        try:
            from stigmem_node.identity.capability import verify_token

            result = verify_token(token_json, lambda _uri: manifest_b)
            assert result is True
        finally:
            settings_module.settings = orig  # type: ignore[assignment]
            db_mod.settings = orig  # type: ignore[assignment]

        conn.close()

    def test_old_key_token_rejected_after_window(self, tmp_path: Path) -> None:
        entity_uri = "https://example.org"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a, entity_uri=entity_uri)

        # Rotation happened 91 days ago — window is closed
        rotated_at = (datetime.now(UTC) - timedelta(days=91)).isoformat().replace("+00:00", "Z")
        priv_b, pub_b, _ = _gen_keypair()
        key_b_id = generate_key_id(priv_b.public_key())
        rot_sig = sign_rotation_event(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key_b64=pub_b,
            rotated_at=rotated_at,
            private_key=priv_a,
        )
        rotation_evt = RotationEvent(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=rot_sig,
            previous_public_key=pub_a,
        )
        manifest_b = _make_manifest(
            priv_b,
            pub_b,
            entity_uri=entity_uri,
            rotation_events=[rotation_evt],
        )

        # Token was signed by key A
        token_body = {
            "token_version": 1,
            "token_id": str(uuid.uuid4()),
            "issuer": entity_uri,
            "subject": entity_uri,
            "verb": "read",
            "object": "*",
            "issued_at": datetime.now(UTC).isoformat(),
            "expiry": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "nonce": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        signing_body = _token_signing_body(token_body)
        sig_b64 = base64.urlsafe_b64encode(priv_a.sign(signing_body)).decode().rstrip("=")
        token_body["signature"] = sig_b64

        with pytest.raises(CapabilityTokenError, match="signature verification failed"):
            _verify_token_signature(token_body, manifest_b, sig_b64)


# ---------------------------------------------------------------------------
# Path 2: Double rollover A→B→C
# ---------------------------------------------------------------------------


class TestPath2DoubleRollover:
    """§22.2 acceptance path 2: double rollover A→B→C."""

    def _build_double_rotation_manifest(
        self,
    ) -> tuple[OrgManifest, Ed25519PrivateKey, Ed25519PrivateKey]:
        """Build a manifest that has gone through two rotations: A→B→C.

        Returns (manifest_c, priv_a, priv_b) so callers can issue tokens
        under either retiring key.
        """
        entity_uri = "https://example.org"
        priv_a, pub_a, _ = _gen_keypair()
        priv_b, pub_b, _ = _gen_keypair()
        priv_c, pub_c, _ = _gen_keypair()

        key_a_id = generate_key_id(priv_a.public_key())
        key_b_id = generate_key_id(priv_b.public_key())
        key_c_id = generate_key_id(priv_c.public_key())

        rotated_at_ab = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        rotated_at_bc = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        evt_ab = RotationEvent(
            previous_key_id=key_a_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at_ab,
            signature=sign_rotation_event(key_a_id, key_b_id, pub_b, rotated_at_ab, priv_a),
            previous_public_key=pub_a,
        )
        evt_bc = RotationEvent(
            previous_key_id=key_b_id,
            new_key_id=key_c_id,
            new_public_key=pub_c,
            rotated_at=rotated_at_bc,
            signature=sign_rotation_event(key_b_id, key_c_id, pub_c, rotated_at_bc, priv_b),
            previous_public_key=pub_b,
        )
        manifest_c = _make_manifest(
            priv_c,
            pub_c,
            entity_uri=entity_uri,
            key_id=key_c_id,
            rotation_events=[evt_ab, evt_bc],
        )
        return manifest_c, priv_a, priv_b

    def test_a_key_token_accepted_in_window(self) -> None:
        manifest_c, priv_a, _ = self._build_double_rotation_manifest()

        token_body = {
            "token_version": 1,
            "token_id": str(uuid.uuid4()),
            "issuer": "https://example.org",
            "subject": "https://example.org",
            "verb": "read",
            "object": "*",
            "issued_at": datetime.now(UTC).isoformat(),
            "expiry": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "nonce": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        signing_body = _token_signing_body(token_body)
        sig_b64 = base64.urlsafe_b64encode(priv_a.sign(signing_body)).decode().rstrip("=")
        token_body["signature"] = sig_b64

        # Should NOT raise — A's window is still open (rotated_at is now)
        _verify_token_signature(token_body, manifest_c, sig_b64)

    def test_b_key_token_accepted_in_window(self) -> None:
        manifest_c, _, priv_b = self._build_double_rotation_manifest()

        token_body = {
            "token_version": 1,
            "token_id": str(uuid.uuid4()),
            "issuer": "https://example.org",
            "subject": "https://example.org",
            "verb": "read",
            "object": "*",
            "issued_at": datetime.now(UTC).isoformat(),
            "expiry": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "nonce": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        signing_body = _token_signing_body(token_body)
        sig_b64 = base64.urlsafe_b64encode(priv_b.sign(signing_body)).decode().rstrip("=")
        token_body["signature"] = sig_b64

        _verify_token_signature(token_body, manifest_c, sig_b64)


# ---------------------------------------------------------------------------
# Path 3: Expired prior key
# ---------------------------------------------------------------------------


class TestPath3ExpiredPriorKey:
    """§22.2 acceptance path 3: dual-trust window expires, old key rejected."""

    def test_expired_window_rejects_old_key_token(self) -> None:
        entity_uri = "https://example.org"
        priv_a, pub_a, _ = _gen_keypair()
        priv_b, pub_b, _ = _gen_keypair()

        key_a_id = generate_key_id(priv_a.public_key())
        key_b_id = generate_key_id(priv_b.public_key())

        # Rotation 91 days ago — window is definitively closed
        rotated_at = (datetime.now(UTC) - timedelta(days=91)).isoformat().replace("+00:00", "Z")
        evt = RotationEvent(
            previous_key_id=key_a_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=sign_rotation_event(key_a_id, key_b_id, pub_b, rotated_at, priv_a),
            previous_public_key=pub_a,
        )
        manifest_b = _make_manifest(priv_b, pub_b, entity_uri=entity_uri, rotation_events=[evt])

        token_body = {
            "token_version": 1,
            "token_id": str(uuid.uuid4()),
            "issuer": entity_uri,
            "subject": entity_uri,
            "verb": "read",
            "object": "*",
            "issued_at": datetime.now(UTC).isoformat(),
            "expiry": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "nonce": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        signing_body = _token_signing_body(token_body)
        sig_b64 = base64.urlsafe_b64encode(priv_a.sign(signing_body)).decode().rstrip("=")
        token_body["signature"] = sig_b64

        with pytest.raises(CapabilityTokenError, match="signature verification failed"):
            _verify_token_signature(token_body, manifest_b, sig_b64)

    def test_window_boundary_exact_90_days(self) -> None:
        """Token at exactly 90 days post-rotation is rejected (boundary is exclusive)."""
        entity_uri = "https://example.org"
        priv_a, pub_a, _ = _gen_keypair()
        priv_b, pub_b, _ = _gen_keypair()

        key_a_id = generate_key_id(priv_a.public_key())
        key_b_id = generate_key_id(priv_b.public_key())

        # Rotation exactly _DUAL_TRUST_DAYS ago
        rotated_at = (
            (datetime.now(UTC) - timedelta(days=_DUAL_TRUST_DAYS))
            .isoformat()
            .replace("+00:00", "Z")
        )
        evt = RotationEvent(
            previous_key_id=key_a_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=sign_rotation_event(key_a_id, key_b_id, pub_b, rotated_at, priv_a),
            previous_public_key=pub_a,
        )
        manifest_b = _make_manifest(priv_b, pub_b, entity_uri=entity_uri, rotation_events=[evt])

        token_body = {
            "token_version": 1,
            "token_id": str(uuid.uuid4()),
            "issuer": entity_uri,
            "subject": entity_uri,
            "verb": "read",
            "object": "*",
            "issued_at": datetime.now(UTC).isoformat(),
            "expiry": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "nonce": uuid.uuid4().hex + uuid.uuid4().hex,
        }
        signing_body = _token_signing_body(token_body)
        sig_b64 = base64.urlsafe_b64encode(priv_a.sign(signing_body)).decode().rstrip("=")

        # now >= rotated_at + 90 days → rejected
        with pytest.raises(CapabilityTokenError, match="signature verification failed"):
            _verify_token_signature(token_body, manifest_b, sig_b64)


# ---------------------------------------------------------------------------
# Path 4: Mid-flight federation handshake
# ---------------------------------------------------------------------------


class TestPath4MidFlightFederationHandshake:
    """§22.2 acceptance path 4: token in-flight during issuer key rotation.

    Scenario: peer P has manifest with key A.  Issuer I rotates to key B.
    P receives the new manifest.  A token issued just before rotation
    (signed by A) must still verify against the new manifest during the
    dual-trust window.
    """

    def test_in_flight_token_accepted_after_peer_gets_new_manifest(self, tmp_path: Path) -> None:
        conn, db_path = _setup_db(tmp_path)

        entity_uri = "https://issuer.example.org"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a, entity_uri=entity_uri)

        # Token issued under key A just before rotation
        token_body = _make_token_body(entity_uri, entity_uri, days_valid=30)
        token_json = _insert_token(conn, token_body, priv_a)

        # Issuer rotates A → B (rotation_at = now → window open)
        priv_b, pub_b, _ = _gen_keypair()
        key_b_id = generate_key_id(priv_b.public_key())
        rotated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        rot_sig = sign_rotation_event(manifest_a.key_id, key_b_id, pub_b, rotated_at, priv_a)
        evt = RotationEvent(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=rot_sig,
            previous_public_key=pub_a,
        )
        # Peer receives the new manifest from issuer
        manifest_b = _make_manifest(priv_b, pub_b, entity_uri=entity_uri, rotation_events=[evt])

        import stigmem_node.db as db_mod
        import stigmem_node.settings as settings_module

        Settings = settings_module.Settings

        orig = settings_module.settings
        settings_module.settings = Settings(db_path=db_path)  # type: ignore[assignment]
        db_mod.settings = settings_module.settings  # type: ignore[assignment]

        try:
            from stigmem_node.identity.capability import verify_token

            # Peer verifies old token against new manifest → must succeed (dual-trust)
            result = verify_token(token_json, lambda _uri: manifest_b)
            assert result is True
        finally:
            settings_module.settings = orig  # type: ignore[assignment]
            db_mod.settings = orig  # type: ignore[assignment]

        conn.close()

    def test_in_flight_token_rejected_when_window_closed(self, tmp_path: Path) -> None:
        conn, db_path = _setup_db(tmp_path)

        entity_uri = "https://issuer.example.org"
        priv_a, pub_a, _ = _gen_keypair()
        manifest_a = _make_manifest(priv_a, pub_a, entity_uri=entity_uri)

        # Token issued under key A
        token_body = _make_token_body(entity_uri, entity_uri, days_valid=30)
        token_json = _insert_token(conn, token_body, priv_a)

        # Rotation happened 91 days ago — window is closed
        priv_b, pub_b, _ = _gen_keypair()
        key_b_id = generate_key_id(priv_b.public_key())
        rotated_at = (datetime.now(UTC) - timedelta(days=91)).isoformat().replace("+00:00", "Z")
        rot_sig = sign_rotation_event(manifest_a.key_id, key_b_id, pub_b, rotated_at, priv_a)
        evt = RotationEvent(
            previous_key_id=manifest_a.key_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=rot_sig,
            previous_public_key=pub_a,
        )
        manifest_b = _make_manifest(priv_b, pub_b, entity_uri=entity_uri, rotation_events=[evt])

        import stigmem_node.db as db_mod
        import stigmem_node.settings as settings_module

        Settings = settings_module.Settings

        orig = settings_module.settings
        settings_module.settings = Settings(db_path=db_path)  # type: ignore[assignment]
        db_mod.settings = settings_module.settings  # type: ignore[assignment]

        try:
            from stigmem_node.identity.capability import verify_token

            with pytest.raises(CapabilityTokenError, match="signature verification failed"):
                verify_token(token_json, lambda _uri: manifest_b)
        finally:
            settings_module.settings = orig  # type: ignore[assignment]
            db_mod.settings = orig  # type: ignore[assignment]

        conn.close()


# ---------------------------------------------------------------------------
# Manifest serialisation round-trip with previous_public_key
# ---------------------------------------------------------------------------


class TestRotationEventSerialization:
    def test_roundtrip_preserves_previous_public_key(self) -> None:
        priv_a, pub_a, _ = _gen_keypair()
        priv_b, pub_b, _ = _gen_keypair()
        key_a_id = generate_key_id(priv_a.public_key())
        key_b_id = generate_key_id(priv_b.public_key())
        rotated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        evt = RotationEvent(
            previous_key_id=key_a_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=sign_rotation_event(key_a_id, key_b_id, pub_b, rotated_at, priv_a),
            previous_public_key=pub_a,
        )
        manifest = _make_manifest(priv_b, pub_b, rotation_events=[evt])

        from stigmem_node.identity.manifest import manifest_from_dict

        d = manifest_to_dict(manifest)
        restored = manifest_from_dict(d)

        assert restored.rotation_events[0].previous_public_key == pub_a

    def test_old_events_without_previous_public_key_still_valid(self) -> None:
        """Events without previous_public_key (pre-§22.2) serialise and verify correctly."""
        priv_a, pub_a, _ = _gen_keypair()
        priv_b, pub_b, _ = _gen_keypair()
        key_a_id = generate_key_id(priv_a.public_key())
        key_b_id = generate_key_id(priv_b.public_key())
        rotated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        evt = RotationEvent(
            previous_key_id=key_a_id,
            new_key_id=key_b_id,
            new_public_key=pub_b,
            rotated_at=rotated_at,
            signature=sign_rotation_event(key_a_id, key_b_id, pub_b, rotated_at, priv_a),
            # previous_public_key intentionally absent (empty string default)
        )
        manifest = _make_manifest(priv_b, pub_b, rotation_events=[evt])

        verify_manifest(manifest)
        verify_rotation_chain(manifest, key_a_id, pub_a)
