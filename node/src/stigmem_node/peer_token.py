"""Ed25519 peer-token creation and verification (spec §3.5, §6.6).

Peer tokens are short-lived Ed25519-signed JWTs used for machine-to-machine
federation auth. They are distinct from long-lived API keys.

exp/iat in the JWT payload are epoch_ms (not epoch_s) per spec §3.5.
We skip PyJWT's built-in exp check and validate manually at ms resolution.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .db import db, get_or_create_federation_keypair, get_or_create_node_id
from .settings import settings

_cached_pub: str | None = None
_cached_priv: str | None = None


def _pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def init_federation_keys() -> tuple[str, str]:
    """Load or generate the node's Ed25519 keypair. Must be called after migrations."""
    global _cached_pub, _cached_priv
    if settings.federation_pubkey and settings.federation_privkey:
        _cached_pub = settings.federation_pubkey
        _cached_priv = settings.federation_privkey
    else:
        _cached_pub, _cached_priv = get_or_create_federation_keypair()
    return _cached_pub, _cached_priv


def get_local_pubkey() -> str:
    if _cached_pub:
        return _cached_pub
    pub, _ = init_federation_keys()
    return pub


def _get_privkey_obj() -> Ed25519PrivateKey:
    _, priv_b64 = init_federation_keys()
    raw = base64.urlsafe_b64decode(_pad(priv_b64))
    return Ed25519PrivateKey.from_private_bytes(raw)


def _pubkey_obj_from_b64(b64: str) -> Ed25519PublicKey:
    raw = base64.urlsafe_b64decode(_pad(b64))
    return Ed25519PublicKey.from_public_bytes(raw)


def create_peer_token(
    target_node_id: str,
    scopes: list[str],
    ttl_ms: int = 3_600_000,
) -> str:
    """Mint a signed peer token addressed to target_node_id."""
    private_key = _get_privkey_obj()
    our_node_id = get_or_create_node_id()
    now_ms = int(time.time() * 1000)
    payload: dict[str, Any] = {
        "iss": our_node_id,
        "sub": target_node_id,
        "iat": now_ms,
        "exp": now_ms + ttl_ms,
        "nonce": str(uuid.uuid4()),
        "scopes": scopes,
    }
    return jwt.encode(payload, private_key, algorithm="EdDSA")


class TokenError(Exception):
    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(kind)


def verify_peer_token(
    raw_token: str,
    peer_pubkey_b64: str,
    peer_db_id: str,
) -> dict[str, Any]:
    """Verify Ed25519 peer JWT against peer's stored pubkey.

    Checks (spec §6.6):
      1. Signature
      2. sub == our node_id
      3. exp not passed (epoch_ms)
      4. nonce not seen within window

    Returns payload dict on success. Raises TokenError on any failure.
    Writes nonce to cache on success (replay protection).
    """
    our_node_id = get_or_create_node_id()
    try:
        public_key = _pubkey_obj_from_b64(peer_pubkey_b64)
        payload: dict[str, Any] = jwt.decode(
            raw_token,
            public_key,
            algorithms=["EdDSA"],
            options={
                # exp/iat are epoch_ms per spec §3.5 — disable library checks, validate manually below
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.exceptions.InvalidSignatureError as exc:
        raise TokenError("invalid_signature") from exc
    except jwt.exceptions.PyJWTError as exc:
        raise TokenError("invalid_token") from exc

    now_ms = int(time.time() * 1000)
    exp = payload.get("exp", 0)
    if now_ms > exp:
        raise TokenError("token_expired")

    if payload.get("sub") != our_node_id:
        raise TokenError("invalid_sub")

    nonce = payload.get("nonce")
    if not nonce:
        raise TokenError("missing_nonce")

    # Atomically insert nonce (UNIQUE constraint rejects replays)
    window_ms = settings.federation_nonce_window_s * 1000
    expires_at = datetime.fromtimestamp(
        min(exp, now_ms + window_ms) / 1000, tz=UTC
    ).isoformat()
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO nonce_cache (nonce, peer_id, expires_at) VALUES (?, ?, ?)",
                (nonce, peer_db_id, expires_at),
            )
            # Opportunistic prune of expired nonces
            conn.execute(
                "DELETE FROM nonce_cache WHERE expires_at < ?",
                (datetime.now(UTC).isoformat(),),
            )
    except sqlite3.IntegrityError:
        raise TokenError("nonce_already_seen")

    return payload


def verify_declaration_sig(decl_fields: dict[str, Any], sig_b64: str, pubkey_b64: str) -> bool:
    """Verify the PeerDeclaration signature (spec §6.1).

    decl_fields must contain all signed fields (everything except declaration_sig itself),
    in lexicographic key order for canonical JSON.
    """
    from cryptography.exceptions import InvalidSignature

    canonical = json.dumps(decl_fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig_bytes = base64.urlsafe_b64decode(_pad(sig_b64))
    try:
        pub = _pubkey_obj_from_b64(pubkey_b64)
        pub.verify(sig_bytes, canonical)
        return True
    except (InvalidSignature, Exception):
        return False
