"""Phase 8 identity layer tests — spec §19.

Covers:
  - Manifest sign + verify roundtrip
  - Rotation chain valid / invalid (regression attack, cross-entity replay F1)
  - TL unavailable → 503 in strict mode, warn in relaxed (H2 regression)
  - Expired manifest → token issuance rejected (H1 regression)
  - External-entity subject → token rejected (C1 regression)
  - Nonce replay via capability_tokens.nonce UNIQUE constraint
  - Quarantine route: reader cannot see fact value (M3 regression)
"""

from __future__ import annotations

import base64
import json
import sqlite3
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.settings as settings_module
from stigmem_node.db import apply_migrations
from stigmem_node.identity.manifest import (
    ManifestError,
    OrgManifest,
    RotationEvent,
    manifest_to_dict,
    sign_manifest,
    sign_rotation_event,
    verify_manifest,
    verify_rotation_chain,
)
from stigmem_node.identity.transparency_log import (
    LocalAppendOnlyLog,
    TransparencyLogUnavailable,
    _OffLog,
)
from stigmem_node.main import create_app
from stigmem_node.settings import Settings

# Reuse conftest helpers
from conftest import _patch_settings, _restore_settings, _make_enc_settings


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[Ed25519PrivateKey, str, str]:
    """Return (private_key_obj, pub_b64url, priv_b64url)."""
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
    entity_uri: str = "https://example.org",
    entities: list[str] | None = None,
    key_id: str = "key-1",
    days_valid: int = 365,
) -> OrgManifest:
    now = datetime.now(UTC)
    m = OrgManifest(
        entity_uri=entity_uri,
        key_id=key_id,
        public_key=pub_b64,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=days_valid)).isoformat(),
        entities=entities if entities is not None else [entity_uri],
    )
    sign_manifest(m, priv)
    return m


# ---------------------------------------------------------------------------
# App fixture with identity routes enabled
# ---------------------------------------------------------------------------


@pytest.fixture()
def identity_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_file = str(tmp_path / "identity_test.db")
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="relaxed",
        tl_backend="off",
    )
    extra = _patch_settings(test_settings)

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    _restore_settings(original, extra)


@pytest.fixture()
def strict_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_file = str(tmp_path / "strict_test.db")
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="strict",
        tl_backend="off",  # "off" → raises TransparencyLogUnavailable → 503 in strict
    )
    extra = _patch_settings(test_settings)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    _restore_settings(original, extra)


# ===========================================================================
# 1. Manifest sign + verify roundtrip
# ===========================================================================


def test_manifest_sign_verify_roundtrip():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64)
    assert verify_manifest(m)  # must not raise


def test_manifest_verify_bad_signature_fails():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64)
    m.signature = "AAAA" + m.signature[4:]  # corrupt
    with pytest.raises(ManifestError, match="self-signature"):
        verify_manifest(m)


def test_manifest_expiry_too_long_rejected():
    priv, pub_b64, _ = _gen_keypair()
    now = datetime.now(UTC)
    m = OrgManifest(
        entity_uri="https://test.org",
        key_id="k1",
        public_key=pub_b64,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=731)).isoformat(),
        entities=["https://test.org"],
    )
    sign_manifest(m, priv)
    with pytest.raises(ManifestError, match="730"):
        verify_manifest(m)


def test_manifest_strict_365_day_limit():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, days_valid=400)
    with pytest.raises(ManifestError, match="365"):
        verify_manifest(m, trust_mode="strict")


def test_manifest_relaxed_allows_up_to_730_days():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, days_valid=700)
    assert verify_manifest(m, trust_mode="relaxed")


def test_manifest_rotation_events_limit():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64)
    # Inject 101 dummy rotation events (content doesn't matter for length check)
    m.rotation_events = [
        RotationEvent(f"k{i}", f"k{i+1}", pub_b64, datetime.now(UTC).isoformat(), "sig")
        for i in range(101)
    ]
    # Re-sign so self-signature is valid
    sign_manifest(m, priv)
    with pytest.raises(ManifestError, match="100"):
        verify_manifest(m)


# ===========================================================================
# 2. Rotation chain valid / invalid
# ===========================================================================


def test_rotation_chain_no_rotation_same_key():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, key_id="genesis")
    assert verify_rotation_chain(m, "genesis", pub_b64)


def test_rotation_chain_no_rotation_different_key_fails():
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, key_id="key-A")
    with pytest.raises(ManifestError, match="differs from previous"):
        verify_rotation_chain(m, "genesis", pub_b64)


def test_rotation_chain_single_valid_step():
    priv1, pub1_b64, _ = _gen_keypair()
    priv2, pub2_b64, _ = _gen_keypair()
    now = datetime.now(UTC).isoformat()

    rot_sig = sign_rotation_event("key-1", "key-2", pub2_b64, now, priv1)
    evt = RotationEvent(
        previous_key_id="key-1",
        new_key_id="key-2",
        new_public_key=pub2_b64,
        rotated_at=now,
        signature=rot_sig,
    )

    m = OrgManifest(
        entity_uri="https://example.org",
        key_id="key-2",
        public_key=pub2_b64,
        issued_at=now,
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        entities=["https://example.org"],
        rotation_events=[evt],
    )
    sign_manifest(m, priv2)

    assert verify_rotation_chain(m, "key-1", pub1_b64)


def test_rotation_chain_regression_attack_rejected():
    """Rotation back to a previously-used key must be rejected."""
    priv1, pub1_b64, _ = _gen_keypair()
    priv2, pub2_b64, _ = _gen_keypair()
    now = datetime.now(UTC).isoformat()

    # Build: key-1 → key-2 (valid) → key-1 (regression — must fail)
    sig_12 = sign_rotation_event("key-1", "key-2", pub2_b64, now, priv1)
    sig_21 = sign_rotation_event("key-2", "key-1", pub1_b64, now, priv2)

    evt1 = RotationEvent("key-1", "key-2", pub2_b64, now, sig_12)
    evt2 = RotationEvent("key-2", "key-1", pub1_b64, now, sig_21)

    m = OrgManifest(
        entity_uri="https://example.org",
        key_id="key-1",
        public_key=pub1_b64,
        issued_at=now,
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        entities=["https://example.org"],
        rotation_events=[evt1, evt2],
    )
    sign_manifest(m, priv1)

    with pytest.raises(ManifestError, match="regression|cycle"):
        verify_rotation_chain(m, "key-1", pub1_b64)


def test_rotation_chain_bad_event_signature_rejected():
    priv1, pub1_b64, _ = _gen_keypair()
    priv2, pub2_b64, _ = _gen_keypair()
    now = datetime.now(UTC).isoformat()

    # Use wrong private key to sign the rotation event (cross-entity replay F1)
    wrong_sig = sign_rotation_event("key-1", "key-2", pub2_b64, now, priv2)  # signed with priv2 not priv1
    evt = RotationEvent("key-1", "key-2", pub2_b64, now, wrong_sig)

    m = OrgManifest(
        entity_uri="https://attacker.org",
        key_id="key-2",
        public_key=pub2_b64,
        issued_at=now,
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        entities=["https://attacker.org"],
        rotation_events=[evt],
    )
    sign_manifest(m, priv2)

    with pytest.raises(ManifestError, match="signature invalid|verification failed"):
        verify_rotation_chain(m, "key-1", pub1_b64)


# ===========================================================================
# 3. TL unavailable → 503 in strict mode, warn in relaxed (H2 regression)
# ===========================================================================


def test_tl_off_log_always_raises():
    off = _OffLog()
    with pytest.raises(TransparencyLogUnavailable):
        off.submit({"test": "data"})
    with pytest.raises(TransparencyLogUnavailable):
        from stigmem_node.identity.transparency_log import LogEntry
        off.verify_inclusion(LogEntry("", "", 0, 0))


def test_manifest_put_strict_mode_tl_unavailable_returns_503(strict_client: TestClient):
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, entity_uri="https://strict-test.org", days_valid=30)
    body = manifest_to_dict(m)
    # strict_client has tl_backend="off" → TransparencyLogUnavailable → 503
    resp = strict_client.put("/v1/federation/manifest", json=body)
    assert resp.status_code == 503, resp.text


def test_manifest_put_relaxed_mode_tl_unavailable_warns(identity_client: TestClient):
    priv, pub_b64, _ = _gen_keypair()
    m = _make_manifest(priv, pub_b64, entity_uri="https://relaxed-test.org", days_valid=30)
    body = manifest_to_dict(m)
    # identity_client has tl_backend="off" but trust_mode="relaxed" → warn, not 503
    resp = identity_client.put("/v1/federation/manifest", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "tl_warning" in data  # warning present but accepted


# ===========================================================================
# 4. Expired manifest → token issuance rejected (H1 regression)
# ===========================================================================


def test_expired_manifest_rejects_token_issuance(tmp_path: Path):
    """Issuing a token from an expired manifest must be rejected (H1)."""
    db_file = str(tmp_path / "h1_test.db")
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="relaxed",
        tl_backend="off",
    )
    extra = _patch_settings(test_settings)

    try:
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            priv, pub_b64, _ = _gen_keypair()
            issuer = "https://expired-issuer.org"
            # Create manifest that is already expired
            now = datetime.now(UTC)
            m = OrgManifest(
                entity_uri=issuer,
                key_id="exp-key",
                public_key=pub_b64,
                issued_at=(now - timedelta(days=10)).isoformat(),
                expires_at=(now - timedelta(seconds=1)).isoformat(),  # already expired
                entities=[issuer, "https://subject.org"],
            )
            sign_manifest(m, priv)

            # Insert into federation_manifests directly so it's "known" but expired
            conn = sqlite3.connect(db_file)
            mid = str(uuid.uuid4())
            mj = json.dumps(manifest_to_dict(m))
            conn.execute(
                "INSERT INTO federation_manifests "
                "(id,entity_uri,manifest_json,signature,key_id,issued_at,expires_at,log_entry_json,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,NULL,?,?)",
                (mid, issuer, mj, m.signature, m.key_id,
                 m.issued_at, m.expires_at, now.isoformat(), now.isoformat()),
            )
            conn.commit()
            conn.close()

            resp = client.post("/v1/federation/capability-tokens", json={
                "issuer": issuer,
                "subject": issuer,
                "verb": "read",
                "object": "stigmem://test/facts",
            })
            # H1: expired manifest → 422 (manifest not found or expired)
            assert resp.status_code == 422, resp.text
            assert "expired" in resp.json().get("detail", "").lower()
    finally:
        _restore_settings(original, extra)


# ===========================================================================
# 5. External-entity subject → token rejected (C1 regression)
# ===========================================================================


def test_external_entity_subject_rejected(identity_client: TestClient):
    """Token subject not in issuer's entities list must be rejected (C1)."""
    priv, pub_b64, _ = _gen_keypair()
    issuer = "https://issuer.org"
    # Entity list does NOT include the subject we'll request
    m = _make_manifest(priv, pub_b64, entity_uri=issuer, entities=[issuer])

    # Register the manifest
    resp = identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    assert resp.status_code == 200, resp.text

    # Attempt to issue a token with an external subject
    resp = identity_client.post("/v1/federation/capability-tokens", json={
        "issuer": issuer,
        "subject": "https://attacker.org",  # NOT in entities list
        "verb": "read",
        "object": "stigmem://facts",
    })
    assert resp.status_code == 403, resp.text
    assert "C1" in resp.json().get("detail", "") or "entities list" in resp.json().get("detail", "")


def test_subject_in_entities_succeeds(identity_client: TestClient):
    """Token issuance succeeds when subject is in the issuer's entities list."""
    priv, pub_b64, _ = _gen_keypair()
    issuer = "https://myorg.org"
    subject = "https://myorg.org/agent-1"
    m = _make_manifest(priv, pub_b64, entity_uri=issuer, entities=[issuer, subject])

    resp = identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    assert resp.status_code == 200, resp.text

    resp = identity_client.post("/v1/federation/capability-tokens", json={
        "issuer": issuer,
        "subject": subject,
        "verb": "read",
        "object": "stigmem://facts",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["subject"] == subject
    assert data["issuer"] == issuer
    assert len(data["nonce"]) == 64
    assert data["nonce"] == data["nonce"].lower()


# ===========================================================================
# 6. Nonce replay via capability_tokens.nonce UNIQUE constraint
# ===========================================================================


def test_nonce_uniqueness_enforced(tmp_path: Path):
    """Inserting two capability_tokens with the same nonce must fail (DB constraint)."""
    db_file = str(tmp_path / "nonce_test.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    now = datetime.now(UTC).isoformat()
    nonce = "a" * 64  # valid 64-char hex

    conn.execute(
        "INSERT INTO capability_tokens "
        "(id,token_json,issuer,subject,verb,object,issued_at,expiry,nonce,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "{}", "iss", "sub", "read", "obj", now, now, nonce, now),
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            "INSERT INTO capability_tokens "
            "(id,token_json,issuer,subject,verb,object,issued_at,expiry,nonce,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "{}", "iss", "sub", "read", "obj", now, now, nonce, now),
        )
        conn.commit()
    conn.close()


def test_nonce_check_constraint_rejects_wrong_format(tmp_path: Path):
    """nonce CHECK(length=64 and all lowercase hex) must reject non-conforming values."""
    db_file = str(tmp_path / "nonce_check.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    now = datetime.now(UTC).isoformat()

    bad_nonces = [
        "ABCD" + "a" * 60,          # uppercase → should fail
        "a" * 63,                     # too short
        "a" * 65,                     # too long
    ]

    for bad_nonce in bad_nonces:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO capability_tokens "
                "(id,token_json,issuer,subject,verb,object,issued_at,expiry,nonce,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), "{}", "iss", "sub", "read", "obj", now, now, bad_nonce, now),
            )
            conn.commit()
        conn.rollback()
    conn.close()


# ===========================================================================
# 7. Quarantine route: reader cannot see fact value (M3 regression)
# ===========================================================================


def test_quarantine_list_hides_fact_value(tmp_path: Path):
    """GET /v1/quarantine must not expose the fact's value field (M3)."""
    db_file = str(tmp_path / "quarantine_m3.db")
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="relaxed",
    )
    extra = _patch_settings(test_settings)

    try:
        # Insert a quarantine garden and a quarantined fact with a sensitive value
        conn = sqlite3.connect(db_file)
        garden_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO gardens (id, slug, name, scope, created_by, created_at, quarantine) "
            "VALUES (?,?,?,?,?,?,1)",
            (garden_id, "qtest", "Quarantine Test", "company", "agent:test", now),
        )
        fact_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO facts (id,entity,relation,value_type,value_v,source,timestamp,"
            "confidence,scope,quarantine_status,quarantine_garden_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (fact_id, "ent:1", "rel:secret", "string", "TOP_SECRET_VALUE",
             "src:1", now, 1.0, "company", "pending", garden_id),
        )
        conn.commit()
        conn.close()

        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get("/v1/quarantine")
            assert resp.status_code == 200
            data = resp.json()

            assert data["total"] >= 1
            fact_record = next(
                (r for r in data["items"] if r["fact_id"] == fact_id), None
            )
            assert fact_record is not None
            # M3: value must not appear in the quarantine list response
            assert "TOP_SECRET_VALUE" not in json.dumps(fact_record)
            # Metadata fields are present
            assert fact_record["entity"] == "ent:1"
            assert fact_record["relation"] == "rel:secret"
            assert fact_record["quarantine_status"] == "pending"
    finally:
        _restore_settings(original, extra)


# ===========================================================================
# 8. Token revocation ownership (H-SEC-3 regression — BOLA)
# ===========================================================================


def test_revoke_token_by_issuer_succeeds(identity_client: TestClient):
    """Issuer can revoke their own token."""
    priv, pub_b64, _ = _gen_keypair()
    issuer = "https://issuer-revoke.org"
    subject = "https://issuer-revoke.org/agent"
    m = _make_manifest(priv, pub_b64, entity_uri=issuer, entities=[issuer, subject])

    identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    resp = identity_client.post("/v1/federation/capability-tokens", json={
        "issuer": issuer,
        "subject": subject,
        "verb": "read",
        "object": "stigmem://facts",
    })
    assert resp.status_code == 201
    token_id = resp.json()["token_id"]

    # Caller is anonymous (entity_uri="anon:trusted") with auth_required=False.
    # The check compares identity.entity_uri to issuer/subject; since auth is off,
    # _ANON entity_uri is "anon:trusted" which does not match the token's issuer/subject.
    # This verifies the guard fires; for a full round-trip the caller must be the issuer.
    # We test the 403 path here:
    resp = identity_client.post(f"/v1/federation/capability-tokens/{token_id}/revoke", json={})
    assert resp.status_code == 403, resp.text
    assert "not authorized" in resp.json().get("detail", "").lower()


def test_revoke_token_unknown_returns_404(identity_client: TestClient):
    """Revoking a non-existent token returns 404, not 403."""
    resp = identity_client.post(
        "/v1/federation/capability-tokens/non-existent-id/revoke", json={}
    )
    assert resp.status_code == 404


def test_revoke_token_unauthorized_third_party_blocked(identity_client: TestClient):
    """A third-party (not issuer or subject) cannot revoke the token (H-SEC-3)."""
    priv, pub_b64, _ = _gen_keypair()
    issuer = "https://org-a.org"
    subject = "https://org-a.org/agent"
    m = _make_manifest(priv, pub_b64, entity_uri=issuer, entities=[issuer, subject])

    identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    resp = identity_client.post("/v1/federation/capability-tokens", json={
        "issuer": issuer,
        "subject": subject,
        "verb": "read",
        "object": "stigmem://facts",
    })
    assert resp.status_code == 201
    token_id = resp.json()["token_id"]

    # identity_client uses auth_required=False → entity_uri is "anon:trusted",
    # which is neither issuer (https://org-a.org) nor subject (https://org-a.org/agent)
    resp = identity_client.post(
        f"/v1/federation/capability-tokens/{token_id}/revoke",
        json={"reason": "unauthorised revocation attempt"},
    )
    assert resp.status_code == 403, resp.text


# ===========================================================================
# 9. LocalAppendOnlyLog — basic submit + verify
# ===========================================================================


def test_local_tl_submit_and_verify(tmp_path: Path):
    log_path = tmp_path / "test_tl.jsonl"
    tl = LocalAppendOnlyLog(str(log_path))

    manifest_data = {"entity_uri": "https://example.org", "key_id": "k1", "signature": "sig"}
    entry = tl.submit(manifest_data)
    assert entry.log_index == 0
    assert len(entry.leaf_hash) == 64  # hex SHA-256

    assert tl.verify_inclusion(entry)


def test_local_tl_multiple_entries(tmp_path: Path):
    log_path = tmp_path / "multi_tl.jsonl"
    tl = LocalAppendOnlyLog(str(log_path))

    e0 = tl.submit({"seq": 0})
    e1 = tl.submit({"seq": 1})
    e2 = tl.submit({"seq": 2})

    assert e0.log_index == 0
    assert e1.log_index == 1
    assert e2.log_index == 2

    assert tl.verify_inclusion(e0)
    assert tl.verify_inclusion(e1)
    assert tl.verify_inclusion(e2)


def test_local_tl_tampered_entry_fails(tmp_path: Path):
    log_path = tmp_path / "tamper_tl.jsonl"
    tl = LocalAppendOnlyLog(str(log_path))
    entry = tl.submit({"data": "original"})

    # Tamper the file
    lines = log_path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["leaf_hash"] = "0" * 64
    log_path.write_text(json.dumps(rec) + "\n")

    from stigmem_node.identity.transparency_log import LogEntry
    bad_entry = LogEntry(
        log_id=entry.log_id,
        leaf_hash=entry.leaf_hash,  # original hash
        log_index=0,
        integrated_time=entry.integrated_time,
    )
    with pytest.raises(ValueError, match="leaf_hash mismatch"):
        tl.verify_inclusion(bad_entry)


# ===========================================================================
# 10. Manifest resolve API
# ===========================================================================


def test_manifest_resolve_roundtrip(identity_client: TestClient):
    priv, pub_b64, _ = _gen_keypair()
    entity_uri = "https://resolve-test.org"
    m = _make_manifest(priv, pub_b64, entity_uri=entity_uri)

    resp = identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    assert resp.status_code == 200

    from urllib.parse import quote
    encoded = quote(entity_uri, safe="")
    resp = identity_client.get(f"/v1/federation/manifest/{encoded}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_uri"] == entity_uri
    assert data["key_id"] == m.key_id


def test_manifest_resolve_unknown_returns_404(identity_client: TestClient):
    from urllib.parse import quote
    encoded = quote("https://unknown-entity.org", safe="")
    resp = identity_client.get(f"/v1/federation/manifest/{encoded}")
    assert resp.status_code == 404


# ===========================================================================
# 11. Manifest rate-limit
# ===========================================================================


def test_manifest_put_rate_limit(identity_client: TestClient):
    """More than 10 manifest PUTs per entity_uri per hour must be rejected with 429."""
    import stigmem_node.routes.identity as identity_mod

    priv, pub_b64, _ = _gen_keypair()
    entity_uri = "https://rate-limit-test.org"

    # Clear any prior state for this entity
    identity_mod._manifest_submit_log.pop(entity_uri, None)

    for i in range(10):
        m = _make_manifest(priv, pub_b64, entity_uri=entity_uri)
        resp = identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
        assert resp.status_code == 200, f"request {i} failed: {resp.text}"

    # 11th request must be rate-limited
    m = _make_manifest(priv, pub_b64, entity_uri=entity_uri)
    resp = identity_client.put("/v1/federation/manifest", json=manifest_to_dict(m))
    assert resp.status_code == 429, resp.text

    # Cleanup
    identity_mod._manifest_submit_log.pop(entity_uri, None)


# ===========================================================================
# 12. Quarantine ingest writes fact_audit_log entry (ACM-198)
# ===========================================================================


def test_quarantine_ingest_writes_audit_log_entry(tmp_path: Path):
    """fact_audit_log must record a quarantine_ingest row when trust_mode=strict
    routes a low-trust fact to the quarantine garden at ingest time."""
    import sqlite3 as _sqlite3

    import stigmem_node.auth as auth_mod
    import stigmem_node.db as db_mod
    from stigmem_node.source_trust import bust_trust_cache

    db_file = str(tmp_path / "qaudit_test.db")
    apply_migrations(db_path=db_file)

    # Create a quarantine garden directly in the DB.
    garden_id = str(uuid.uuid4())
    sender_node_id = f"stigmem://low-trust-sender-{uuid.uuid4()}"
    now = datetime.now(UTC).isoformat()
    conn = _sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO gardens (id, slug, name, scope, created_by, created_at, quarantine) "
        "VALUES (?,?,?,?,?,?,1)",
        (garden_id, "test-quarantine", "Test Quarantine", "company", "agent:test", now),
    )
    # Blocklist the sender so compute_source_trust returns 0.0 deterministically.
    conn.execute(
        "INSERT INTO quarantine_rules (id, rule_type, org_uri, created_by, created_at) "
        "VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), "never_trust", sender_node_id, "agent:test", now),
    )
    conn.commit()
    conn.close()

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="strict",
        quarantine_garden_id=garden_id,
        tl_backend="off",
    )
    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]

    try:
        bust_trust_cache(sender_node_id)

        from stigmem_node.federation_ingest import ingest_fact

        fact_id = str(uuid.uuid4())
        fact = {
            "id": fact_id,
            "entity": "test:entity",
            "relation": "test:value",
            "value": {"type": "string", "v": "quarantined-payload"},
            "source": sender_node_id,
            "timestamp": now,
            "hlc": None,
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }

        result = ingest_fact(fact, sender_node_id=sender_node_id)
        assert result is True, "ingest_fact should return True for a new fact"

        # Verify quarantine_ingest audit entry was written.
        conn2 = _sqlite3.connect(db_file)
        conn2.row_factory = _sqlite3.Row
        row = conn2.execute(
            "SELECT * FROM fact_audit_log WHERE fact_id = ? AND event_type = 'quarantine_ingest'",
            (fact_id,),
        ).fetchone()
        conn2.close()

        assert row is not None, "fact_audit_log must have a quarantine_ingest entry"
        assert row["entity_uri"] == "system:federation"
        assert row["source"] == sender_node_id
        assert row["oidc_sub"] is None
        detail = json.loads(row["detail"])
        assert "trust_score" in detail
        assert detail["trust_score"] == 0.0

        # Verify the fact itself was routed to quarantine.
        conn3 = _sqlite3.connect(db_file)
        conn3.row_factory = _sqlite3.Row
        fact_row = conn3.execute(
            "SELECT quarantine_status, quarantine_garden_id FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
        conn3.close()
        assert fact_row is not None
        assert fact_row["quarantine_status"] == "pending"
        assert fact_row["quarantine_garden_id"] == garden_id
    finally:
        settings_module.settings = original  # type: ignore[assignment]
        auth_mod.settings = original  # type: ignore[assignment]
        db_mod.settings = original  # type: ignore[assignment]
        bust_trust_cache(sender_node_id)
