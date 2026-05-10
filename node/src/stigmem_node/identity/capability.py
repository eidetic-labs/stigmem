"""Capability token signing and verification — spec §19.3.2–§19.3.3 (C-SEC-1 / M-SEC-2).

Public surface:
    CapabilityTokenError   — raised on any token structural or cryptographic violation
    load_node_private_key() -> Ed25519PrivateKey | None
    sign_token(token_body)        -> str   (base64url signature)
    sign_revocation_event(event)  -> str   (base64url signature)
    verify_token(token_json, get_manifest, *, trust_mode) -> bool

Security requirements:
    - JCS via canonicaljson (RFC 8785) for both signing and verification
    - token_version must equal 1; tokens without it are rejected (M-SEC-2)
    - Signature covers all token fields except "signature" itself
    - Revocation check via DB (step 6 of §19.3.3)
    - Private key singleton is seed-keyed to correctly reflect settings changes in tests
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import canonicaljson
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .manifest import ManifestError, OrgManifest, verify_manifest

logger = logging.getLogger("stigmem.identity.capability")

_TOKEN_VERSION = 1
# Dual-trust window: old key stays in accept_set for this many days after rotation.
# Must be ≥ max token TTL (90 days per §19.3.2 / §22.2.2).
_DUAL_TRUST_DAYS = 90

# Seed-keyed singleton: cache is invalidated automatically when settings change.
_node_private_key: Ed25519PrivateKey | None = None
_node_private_key_seed: str = ""


class CapabilityTokenError(ValueError):
    """Raised when a capability token fails any verification step."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _pubkey_from_b64(b64: str) -> Ed25519PublicKey:
    raw = base64.urlsafe_b64decode(_pad(b64))
    return Ed25519PublicKey.from_public_bytes(raw)


def _token_signing_body(token_body: dict[str, Any]) -> bytes:
    """JCS-canonical bytes over all token_body fields except 'signature'."""
    body = {k: v for k, v in token_body.items() if k != "signature"}
    return canonicaljson.encode_canonical_json(body)


def _revocation_signing_body(event: dict[str, Any]) -> bytes:
    """JCS-canonical bytes over all event fields except 'signature'."""
    body = {k: v for k, v in event.items() if k != "signature"}
    return canonicaljson.encode_canonical_json(body)


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------


def load_node_private_key() -> Ed25519PrivateKey | None:
    """Return the cached node Ed25519 private key, re-loading when settings change.

    Returns None when STIGMEM_NODE_PRIVATE_KEY is not configured (dev/test mode).
    Raises ValueError if the configured value cannot be decoded.
    """
    global _node_private_key, _node_private_key_seed

    from ..settings import settings  # lazy — reflects test patches

    current_seed = settings.node_private_key

    if hmac.compare_digest(current_seed, _node_private_key_seed):  # nosec CT001 — cache invalidation; neither operand is attacker-controlled
        return _node_private_key  # cache hit

    if not current_seed:
        _node_private_key = None
        _node_private_key_seed = current_seed
        return None

    raw = base64.urlsafe_b64decode(_pad(current_seed))
    _node_private_key = Ed25519PrivateKey.from_private_bytes(raw)
    _node_private_key_seed = current_seed
    logger.debug("node private key loaded (seed changed)")
    return _node_private_key


# ---------------------------------------------------------------------------
# Signing helpers
# ---------------------------------------------------------------------------


def sign_token(token_body: dict[str, Any]) -> str:
    """Sign *token_body* with the node private key. Returns base64url signature.

    Raises RuntimeError if STIGMEM_NODE_PRIVATE_KEY is not configured.
    """
    key = load_node_private_key()
    if key is None:
        raise RuntimeError(
            "STIGMEM_NODE_PRIVATE_KEY is not configured; cannot sign capability token"
        )
    sig_bytes = key.sign(_token_signing_body(token_body))
    return base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")


def sign_revocation_event(event: dict[str, Any]) -> str:
    """Sign a revocation event with the node private key. Returns base64url signature.

    Raises RuntimeError if STIGMEM_NODE_PRIVATE_KEY is not configured.
    """
    key = load_node_private_key()
    if key is None:
        raise RuntimeError(
            "STIGMEM_NODE_PRIVATE_KEY is not configured; cannot sign revocation event"
        )
    sig_bytes = key.sign(_revocation_signing_body(event))
    return base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


def _verify_token_signature(
    token: dict[str, Any], manifest: OrgManifest, sig_b64: str
) -> None:
    """Verify token signature against the current key or a dual-trust window key.

    Tries manifest.public_key first.  On failure, walks manifest.rotation_events
    in reverse and checks any previous_public_key that is still within the
    _DUAL_TRUST_DAYS window (§22.2).  Raises CapabilityTokenError if no key
    verifies the signature.
    """
    signing_body = _token_signing_body(token)
    sig_bytes = base64.urlsafe_b64decode(_pad(sig_b64))

    # Try current key
    try:
        _pubkey_from_b64(manifest.public_key).verify(sig_bytes, signing_body)
        return
    except InvalidSignature:
        pass
    except Exception as exc:
        raise CapabilityTokenError(f"token signature error: {exc}") from exc

    # Dual-trust fallback: try retiring keys whose window has not yet closed
    now = datetime.now(UTC)
    for evt in reversed(manifest.rotation_events):
        if not evt.previous_public_key:
            continue  # pre-§22.2 event — no stored retiring pubkey
        try:
            rotated_at = datetime.fromisoformat(evt.rotated_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if now >= rotated_at + timedelta(days=_DUAL_TRUST_DAYS):
            continue  # dual-trust window closed
        try:
            _pubkey_from_b64(evt.previous_public_key).verify(sig_bytes, signing_body)
            logger.debug(
                "token verified under dual-trust key %s (window open until %s)",
                evt.previous_key_id,
                (rotated_at + timedelta(days=_DUAL_TRUST_DAYS)).isoformat(),
            )
            return
        except InvalidSignature:
            continue
        except Exception as exc:
            raise CapabilityTokenError(f"dual-trust signature error: {exc}") from exc

    raise CapabilityTokenError("token signature verification failed")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_token(
    token_json: str,
    get_manifest: Callable[[str], OrgManifest | None],
    *,
    trust_mode: str = "relaxed",
) -> bool:
    """Verify a capability token — spec §19.3.3 steps 1–6.

    Args:
        token_json:   Full token JSON string (including "signature" field).
        get_manifest: Callable returning OrgManifest for an entity_uri, or None.
                      Pass get_peer_manifest from trust_store for production use;
                      pass a dict lookup lambda for unit tests.
        trust_mode:   Forwarded to manifest verification.

    Returns True on success.
    Raises CapabilityTokenError for any failure (including expired, revoked, bad sig).
    """
    try:
        token = json.loads(token_json)
    except json.JSONDecodeError as exc:
        raise CapabilityTokenError(f"invalid token JSON: {exc}") from exc

    # M-SEC-2: token_version must be present and equal to 1
    token_version = token.get("token_version")
    if token_version != _TOKEN_VERSION:
        raise CapabilityTokenError(
            f"unsupported token_version: {token_version!r} (expected {_TOKEN_VERSION})"
        )

    issuer: str = token.get("issuer", "")
    subject: str = token.get("subject", "")
    expiry_str: str = token.get("expiry", "")
    token_id: str = token.get("token_id", "")
    sig_b64: str = token.get("signature", "")

    if not all([issuer, subject, expiry_str, token_id, sig_b64]):
        raise CapabilityTokenError("token missing required fields")

    # Step 1: resolve issuer manifest (includes expiry check and refresh in get_peer_manifest)
    manifest = get_manifest(issuer)
    if manifest is None:
        raise CapabilityTokenError(
            f"issuer manifest not found or expired: {issuer!r}"
        )

    # Step 2: verify manifest self-signature
    try:
        verify_manifest(manifest, trust_mode=trust_mode)
    except ManifestError as exc:
        raise CapabilityTokenError(f"issuer manifest verification failed: {exc}") from exc

    # Step 3: verify token signature under manifest public_key or a dual-trust window key.
    # §22.2: tokens issued under the prior key MUST be accepted for dual_trust_days after
    # rotation.  We try the current key first; on InvalidSignature we walk rotation_events
    # in reverse and try each previous_public_key that is still within its trust window.
    _verify_token_signature(token, manifest, sig_b64)

    # Step 4: C1 — subject must be in issuer's entities list
    if subject not in manifest.entities:
        raise CapabilityTokenError(
            f"subject {subject!r} not in issuer {issuer!r} entities list (C1)"
        )

    # Step 5: expiry check
    now = datetime.now(UTC)
    try:
        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CapabilityTokenError(f"invalid expiry format: {exc}") from exc

    if expiry <= now:
        raise CapabilityTokenError(f"token expired at {expiry_str}")

    # Step 6: revocation check (DB lookup)
    from ..db import db

    with db() as conn:
        row = conn.execute(
            "SELECT revoked_at FROM capability_tokens WHERE id = ?",
            (token_id,),
        ).fetchone()

    if row is None:
        raise CapabilityTokenError(f"token {token_id!r} not found in store")
    if row["revoked_at"] is not None:
        raise CapabilityTokenError(f"token {token_id!r} has been revoked")

    return True
