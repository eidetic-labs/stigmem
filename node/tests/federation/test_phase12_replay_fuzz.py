"""§22.5 — Replay-protection fuzz + constant-time crypto audit.

Property/fuzz tests covering:
  1. verify_token: mangled signature always rejected
  2. verify_token: unknown issuer always rejected
  3. verify_token: past-expiry tokens always rejected (clock-skew boundary)
  4. verify_token: arbitrary JSON never raises unexpected exception types
  5. verify_token: mutating any signed field after signing always rejected
  6. verify_peer_token: arbitrary payloads never raise unexpected exception types
  7. verify_peer_token: nonce already in replay-cache always rejected

CI: runs under HYPOTHESIS_SEED=0 for reproducible seeds.
Total budget: max_examples are tuned so the full suite runs well under 60 s.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import canonicaljson
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from fastapi import HTTPException
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import stigmem_node.db as db_mod
import stigmem_node.settings as settings_module
from stigmem_node.identity.capability import CapabilityTokenError, verify_token
from stigmem_node.identity.manifest import OrgManifest, sign_manifest
from stigmem_node.peer_auth import verify_peer_token

apply_migrations = db_mod.apply_migrations
Settings = settings_module.Settings


@contextmanager
def _patched_test_settings(test_settings: Any) -> Iterator[None]:
    original_settings = settings_module.settings
    original_db_settings = db_mod.settings
    settings_module.settings = test_settings
    db_mod.settings = test_settings
    try:
        yield
    finally:
        settings_module.settings = original_settings
        db_mod.settings = original_db_settings


# ---------------------------------------------------------------------------
# Module-level fixed keypair (generated once; reused across all Hypothesis
# examples to avoid per-example key generation overhead).
# ---------------------------------------------------------------------------

_FUZZ_PRIV: Ed25519PrivateKey = Ed25519PrivateKey.generate()
_FUZZ_PUB_B64: str = (
    base64.urlsafe_b64encode(_FUZZ_PRIV.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    .decode()
    .rstrip("=")
)
_FUZZ_ISSUER = "https://fuzz.example.org"


def _make_fuzz_manifest(entity_uri: str = _FUZZ_ISSUER) -> OrgManifest:
    now = datetime.now(UTC)
    m = OrgManifest(
        entity_uri=entity_uri,
        key_id="fuzz-key-1",
        public_key=_FUZZ_PUB_B64,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=365)).isoformat(),
        entities=[entity_uri],
    )
    sign_manifest(m, _FUZZ_PRIV)
    return m


def _make_valid_token_dict(
    entity_uri: str = _FUZZ_ISSUER,
    expiry_delta: timedelta | None = None,
) -> dict[str, object]:
    """Build a correctly signed token dict (no DB insert).

    All fields except 'signature' are canonical-JSON-signed with _FUZZ_PRIV.
    """
    if expiry_delta is None:
        expiry_delta = timedelta(hours=1)
    now = datetime.now(UTC)
    body: dict[str, object] = {
        "token_id": str(uuid.uuid4()),
        "token_version": 1,
        "issuer": entity_uri,
        "subject": entity_uri,
        "verb": "read",
        "object": "stigmem://facts",
        "issued_at": now.isoformat(),
        "expiry": (now + expiry_delta).isoformat(),
        "nonce": uuid.uuid4().hex * 2,  # 64-char lowercase hex
    }
    signing_body = canonicaljson.encode_canonical_json(body)
    sig_bytes = _FUZZ_PRIV.sign(signing_body)
    body["signature"] = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
    return body


def _b64url_json(value: object) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _encode_eddsa_jwt(payload: dict[str, object], private_key: Ed25519PrivateKey) -> str:
    """Build an EdDSA JWT directly so malformed claim shapes reach the verifier."""
    signing_input = ".".join(
        [
            _b64url_json({"alg": "EdDSA", "typ": "JWT"}),
            _b64url_json(payload),
        ]
    ).encode("ascii")
    signature = (
        base64.urlsafe_b64encode(private_key.sign(signing_input)).decode("ascii").rstrip("=")
    )
    return f"{signing_input.decode('ascii')}.{signature}"


# Single manifest instance shared across all no-DB examples.
_FUZZ_MANIFEST: OrgManifest = _make_fuzz_manifest()


def _manifest_lookup(uri: str) -> OrgManifest | None:
    return _FUZZ_MANIFEST if uri == _FUZZ_ISSUER else None


# ---------------------------------------------------------------------------
# 1. Mangled-signature: any random bytes as signature must be rejected
# ---------------------------------------------------------------------------


@given(sig_bytes=st.binary(min_size=0, max_size=128))
@settings(
    max_examples=500,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_mangled_signature_always_rejected(sig_bytes: bytes) -> None:
    """Random bytes used as the Ed25519 signature must cause CapabilityTokenError.

    The probability of a random 64-byte string being a genuine Ed25519 signature
    for a given (key, message) pair is 1/2^256 — negligible for a fuzz harness.
    Wrong-length signatures are rejected outright by the underlying library.
    """
    token = _make_valid_token_dict()
    token["signature"] = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
    if not token["signature"]:
        # Empty sig triggers "missing required fields" which is also CapabilityTokenError
        pass

    with pytest.raises(CapabilityTokenError):
        verify_token(json.dumps(token), _manifest_lookup, trust_mode="relaxed")


# ---------------------------------------------------------------------------
# 2. Unknown issuer: manifest not found → always rejected
# ---------------------------------------------------------------------------


@given(
    bad_issuer=st.text(
        min_size=1,
        max_size=200,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters=":/._-@",
        ),
    )
)
@settings(
    max_examples=300,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_unknown_issuer_always_rejected(bad_issuer: str) -> None:
    """A token whose issuer URI is not in the manifest store must be rejected."""
    if bad_issuer == _FUZZ_ISSUER:
        return  # skip: this is the valid issuer

    token = _make_valid_token_dict()
    token["issuer"] = bad_issuer
    # Re-sign so signature is valid for the mutated body
    body_without_sig = {k: v for k, v in token.items() if k != "signature"}
    signing_body = canonicaljson.encode_canonical_json(body_without_sig)
    sig_bytes = _FUZZ_PRIV.sign(signing_body)
    token["signature"] = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")

    with pytest.raises(CapabilityTokenError):
        verify_token(json.dumps(token), _manifest_lookup, trust_mode="relaxed")


# ---------------------------------------------------------------------------
# 3. Clock-skew bounds: past-expiry tokens always rejected
# ---------------------------------------------------------------------------


@given(seconds_past=st.integers(min_value=1, max_value=86400 * 365 * 10))
@settings(
    max_examples=300,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_expired_token_always_rejected(seconds_past: int) -> None:
    """Tokens whose expiry lies in the past must be rejected regardless of how long ago."""
    token = _make_valid_token_dict(expiry_delta=-timedelta(seconds=seconds_past))

    with pytest.raises(CapabilityTokenError, match="expired"):
        verify_token(json.dumps(token), _manifest_lookup, trust_mode="relaxed")


# ---------------------------------------------------------------------------
# 4. Arbitrary JSON: verify_token must only raise CapabilityTokenError, never crash
# ---------------------------------------------------------------------------


@given(
    payload=st.dictionaries(
        keys=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters="_",
            ),
        ),
        values=st.one_of(
            st.none(),
            st.booleans(),
            st.integers(min_value=-(10**9), max_value=10**9),
            st.text(max_size=200),
            st.lists(st.text(max_size=20), max_size=5),
        ),
        min_size=0,
        max_size=20,
    )
)
@settings(
    max_examples=200,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_arbitrary_json_never_crashes(payload: dict[str, object]) -> None:
    """verify_token on arbitrary JSON must only raise CapabilityTokenError, not crash."""
    token_json = json.dumps(payload)
    expected_error: CapabilityTokenError | None

    try:
        verify_token(token_json, lambda _: None, trust_mode="relaxed")
    except CapabilityTokenError as exc:
        expected_error = exc
    except Exception as exc:
        raise AssertionError(
            f"verify_token raised unexpected {type(exc).__name__}: {exc}\nInput: {token_json[:300]}"
        ) from exc
    else:
        expected_error = None

    required_fields = {
        "token_id",
        "token_version",
        "issuer",
        "subject",
        "verb",
        "object",
        "issued_at",
        "expiry",
        "nonce",
        "signature",
    }
    is_malformed = not required_fields.issubset(payload.keys())
    if is_malformed:
        assert expected_error is not None
    else:
        assert expected_error is None or isinstance(expected_error, CapabilityTokenError)


# ---------------------------------------------------------------------------
# 5. Field mutation: changing any signed field after signing must be rejected
# ---------------------------------------------------------------------------


_MUTABLE_FIELDS = ["issuer", "subject", "verb", "object", "expiry", "nonce", "token_id"]


@given(
    field_name=st.sampled_from(_MUTABLE_FIELDS),
    new_value=st.text(min_size=1, max_size=200),
)
@settings(
    max_examples=300,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_mutated_signed_field_rejected(field_name: str, new_value: str) -> None:
    """Mutating any field covered by the Ed25519 signature must cause rejection.

    The signature is computed over the canonical JSON of all fields except
    'signature', so any change to a covered field invalidates the signature.
    """
    token = _make_valid_token_dict()
    if new_value == str(token.get(field_name)):
        return  # identical mutation — no change, nothing to test

    token[field_name] = new_value
    token_json = json.dumps(token)
    expected_error: CapabilityTokenError | None

    try:
        verify_token(token_json, _manifest_lookup, trust_mode="relaxed")
    except CapabilityTokenError as exc:
        expected_error = exc
    except Exception as exc:
        raise AssertionError(
            f"unexpected exception {type(exc).__name__}: {exc} "
            f"when mutating {field_name!r}={new_value!r}"
        ) from exc
    else:
        expected_error = None

    assert expected_error is not None, (
        f"verify_token accepted a token with mutated {field_name!r}={new_value!r}"
    )


# ---------------------------------------------------------------------------
# 6. Peer-token arbitrary payloads: validation failures are controlled HTTP errors
# ---------------------------------------------------------------------------


_PEER_CLAIM_VALUE = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**15),
    st.text(max_size=80),
    st.lists(st.text(max_size=24), max_size=5),
)


@given(
    exp=st.one_of(
        st.integers(min_value=int(time.time() * 1000) + 1, max_value=10**15),
        _PEER_CLAIM_VALUE,
    ),
    iat=st.one_of(
        st.integers(min_value=0, max_value=int(time.time() * 1000)),
        _PEER_CLAIM_VALUE,
    ),
    nbf=st.one_of(_PEER_CLAIM_VALUE, st.just(None)),
    iss=st.one_of(st.just("stigmem://payload-fuzz-peer"), _PEER_CLAIM_VALUE),
    sub=st.one_of(st.just("stigmem://payload-fuzz-local"), _PEER_CLAIM_VALUE),
    nonce=st.one_of(st.uuids().map(str), _PEER_CLAIM_VALUE),
    scopes=st.one_of(st.lists(st.text(max_size=24), max_size=5), _PEER_CLAIM_VALUE),
)
@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow],
)
def _check_peer_token_arbitrary_payload(
    peer_priv: Ed25519PrivateKey,
    local_node_id: str,
    exp: object,
    iat: object,
    nbf: object,
    iss: object,
    sub: object,
    nonce: object,
    scopes: object,
) -> None:
    payload: dict[str, object] = {
        "iss": iss,
        "sub": sub,
        "iat": iat,
        "exp": exp,
        "nonce": nonce,
        "scopes": scopes,
    }
    if nbf is not None:
        payload["nbf"] = nbf
    raw_token = _encode_eddsa_jwt(payload, peer_priv)
    expected_error: HTTPException | None

    try:
        verify_peer_token(raw_token, local_node_id)
    except HTTPException as exc:
        expected_error = exc
    except Exception as exc:
        raise AssertionError(
            f"verify_peer_token raised unexpected {type(exc).__name__}: {exc}"
        ) from exc
    else:
        expected_error = None

    assert expected_error is None or isinstance(expected_error, HTTPException)


def test_fuzz_peer_token_arbitrary_payload_never_crashes(tmp_path: Path) -> None:
    """Signed peer JWTs with varied claim shapes must fail with HTTPException only."""
    db_file = str(tmp_path / "peer_payload_fuzz.db")
    apply_migrations(db_path=db_file)

    peer_priv = Ed25519PrivateKey.generate()
    peer_pub_b64 = (
        base64.urlsafe_b64encode(
            peer_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        )
        .decode()
        .rstrip("=")
    )
    peer_node_id = "stigmem://payload-fuzz-peer"
    local_node_id = "stigmem://payload-fuzz-local"
    now_iso = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO peers "
        "(id, node_id, node_url, federation_pubkey, status, allowed_scopes, "
        "created_at, declaration_sig, signed_at) "
        "VALUES (?, ?, ?, ?, 'active', '[]', ?, 'test-sig', ?)",
        (
            str(uuid.uuid4()),
            peer_node_id,
            "http://payload-fuzz-peer",
            peer_pub_b64,
            now_iso,
            now_iso,
        ),
    )
    conn.commit()
    conn.close()

    test_settings = Settings(db_path=db_file, auth_required=False, node_url=local_node_id)
    with _patched_test_settings(test_settings):
        _check_peer_token_arbitrary_payload(peer_priv, local_node_id)


# ---------------------------------------------------------------------------
# 7. Peer-token nonce replay: nonce already in replay-cache is always rejected
# ---------------------------------------------------------------------------


def test_fuzz_peer_nonce_replay_rejected(tmp_path: Path) -> None:
    """A peer JWT whose nonce is already in nonce_cache must be rejected (nonce_already_seen).

    For each Hypothesis example, the nonce is pre-inserted into the cache
    before calling verify_peer_token. This directly tests the replay-guard
    predicate without the cross-example contamination that arises from
    consuming nonces inside the loop.
    """
    db_file = str(tmp_path / "nonce_fuzz.db")
    apply_migrations(db_path=db_file)

    peer_priv = Ed25519PrivateKey.generate()
    peer_pub_b64 = (
        base64.urlsafe_b64encode(
            peer_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        )
        .decode()
        .rstrip("=")
    )
    peer_node_id = "stigmem://fuzz-peer"
    local_node_id = "stigmem://fuzz-local"
    peer_db_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    # Insert peer row so verify_peer_token can resolve the issuer.
    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO peers "
        "(id, node_id, node_url, federation_pubkey, status, allowed_scopes, "
        "created_at, declaration_sig, signed_at) "
        "VALUES (?, ?, ?, ?, 'active', '[]', ?, 'test-sig', ?)",
        (peer_db_id, peer_node_id, "http://fuzz-peer", peer_pub_b64, now_iso, now_iso),
    )
    conn.commit()
    conn.close()

    test_settings = Settings(db_path=db_file, auth_required=False, node_url=local_node_id)
    with _patched_test_settings(test_settings):
        @given(nonce_val=st.uuids().map(str))
        @settings(
            max_examples=50,
            deadline=5000,
            suppress_health_check=[HealthCheck.too_slow],
        )
        def inner(nonce_val: str) -> None:
            now_ts = int(time.time() * 1000)
            exp_ts = now_ts + 3_600_000
            expires_iso = datetime.fromtimestamp(exp_ts / 1000, UTC).isoformat()

            # Pre-populate the nonce cache (simulates "already seen").
            inner_conn = sqlite3.connect(db_file)
            inner_conn.execute(
                "INSERT OR IGNORE INTO nonce_cache (nonce, peer_id, expires_at) "
                "VALUES (?, ?, ?)",
                (nonce_val, peer_db_id, expires_iso),
            )
            inner_conn.commit()
            inner_conn.close()

            # Mint a fresh, validly-signed JWT with this nonce.
            payload = {
                "iss": peer_node_id,
                "sub": local_node_id,
                "iat": now_ts,
                "exp": exp_ts,
                "nonce": nonce_val,
                "scopes": ["read"],
            }
            raw_token = jwt.encode(payload, peer_priv, algorithm="EdDSA")

            # Verification must fail because the nonce is already in the cache.
            with pytest.raises(HTTPException) as exc_info:
                verify_peer_token(raw_token, local_node_id)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "nonce_already_seen"

        inner()
