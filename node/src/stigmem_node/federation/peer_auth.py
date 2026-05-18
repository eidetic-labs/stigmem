"""Ed25519 federation keypair management and peer-token authentication.

Spec §3.5 (peer tokens), §6.6 (security invariants).

PeerToken JWT payload:
  iss:    issuing node_id (URI)
  sub:    target node_id (URI)
  iat:    issued-at (milliseconds since epoch)
  exp:    expiry (milliseconds since epoch; MUST be <= iat + 3_600_000)
  nonce:  UUID for replay protection
  scopes: list[FactScope]
"""

from __future__ import annotations

import base64
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_der_private_key,
)
from fastapi import HTTPException, status

from ..db import db

# ---------------------------------------------------------------------------
# Base64url helpers
# ---------------------------------------------------------------------------


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


# ---------------------------------------------------------------------------
# Node federation keypair (stored in node_meta)
# ---------------------------------------------------------------------------


def get_or_create_keypair() -> tuple[Ed25519PrivateKey, str]:
    """Return (private_key, base64url_pubkey). Creates and persists on first call."""
    with db() as conn:
        row = conn.execute("SELECT value FROM node_meta WHERE key='federation_privkey'").fetchone()
        if row:
            der_bytes = b64url_decode(row["value"])
            priv: Ed25519PrivateKey = load_der_private_key(der_bytes, password=None)  # type: ignore[assignment]
            pub_raw = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            return priv, b64url_encode(pub_raw)

        priv = Ed25519PrivateKey.generate()
        der_bytes = priv.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        pub_raw = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        conn.execute(
            "INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_privkey', ?)",
            (b64url_encode(der_bytes),),
        )
        return priv, b64url_encode(pub_raw)


def get_federation_pubkey() -> str:
    """Return the local node's base64url-encoded Ed25519 public key."""
    _, pubkey = get_or_create_keypair()
    return pubkey


# ---------------------------------------------------------------------------
# Peer token minting (subscriber → publisher)
# ---------------------------------------------------------------------------


def mint_peer_token(
    local_node_id: str,
    target_node_id: str,
    scopes: list[str],
    ttl_ms: int = 3_600_000,
) -> str:
    """Mint a signed Ed25519 JWT peer token for pull replication."""
    priv, _ = get_or_create_keypair()
    now_ms = int(time.time() * 1000)
    payload: dict[str, Any] = {
        "iss": local_node_id,
        "sub": target_node_id,
        "iat": now_ms,
        "exp": now_ms + min(ttl_ms, 3_600_000),
        "nonce": str(uuid.uuid4()),
        "scopes": scopes,
    }
    return jwt.encode(payload, priv, algorithm="EdDSA")


# ---------------------------------------------------------------------------
# Peer token verification (inbound — called by federation/facts endpoint)
# ---------------------------------------------------------------------------


class PeerTokenClaims:
    def __init__(self, iss: str, sub: str, scopes: list[str], nonce: str) -> None:
        self.iss = iss
        self.sub = sub
        self.scopes = scopes
        self.nonce = nonce


def verify_peer_token(
    raw_token: str,
    local_node_id: str,
    audit_writer: Any | None = None,
) -> PeerTokenClaims:
    """Verify a peer JWT and return its claims.

    Raises HTTPException 401/403 on any verification failure.
    Nonce is NOT consumed here; caller must call consume_nonce() after successful auth.
    """
    # Step 1 — decode header/payload without verification to extract iss
    try:
        unverified = jwt.decode(
            raw_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["EdDSA"],
        )
    except jwt.exceptions.DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"malformed_token: {e}"
        ) from e

    iss = unverified.get("iss", "")
    nonce = unverified.get("nonce", "")
    exp = unverified.get("exp", 0)
    scopes = unverified.get("scopes", [])

    # Step 2 — expiry check (before touching DB)
    now_ms = int(time.time() * 1000)
    if exp <= now_ms:
        _write_audit(audit_writer, iss, "rejected_token", {"reason": "token_expired", "exp": exp})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired")

    # Step 3 — look up peer by iss
    with db() as conn:
        peer_row = conn.execute(
            "SELECT id, federation_pubkey, status, allowed_scopes FROM peers WHERE node_id = ?",
            (iss,),
        ).fetchone()

    if peer_row is None or peer_row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown_or_inactive_peer"
        )

    # Step 4 — verify signature
    try:
        pub_bytes = b64url_decode(peer_row["federation_pubkey"])
        public_key: Ed25519PublicKey = Ed25519PublicKey.from_public_bytes(pub_bytes)
        verified = jwt.decode(
            raw_token,
            public_key,
            algorithms=["EdDSA"],
            options={
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
            },
        )
    except (
        jwt.exceptions.InvalidSignatureError,
        InvalidSignature,
        jwt.exceptions.DecodeError,
    ) as e:
        _write_audit(audit_writer, iss, "rejected_token", {"reason": "invalid_signature"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature"
        ) from e

    # Step 5 — sub must match local node
    if verified.get("sub") != local_node_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub_mismatch")

    # Step 6 — replay check (nonce must not be in nonce_cache)
    now_iso = datetime.now(UTC).isoformat()
    with db() as conn:
        # Prune expired nonces opportunistically
        conn.execute("DELETE FROM nonce_cache WHERE expires_at < ?", (now_iso,))
        existing = conn.execute(
            "SELECT nonce FROM nonce_cache WHERE nonce = ?", (nonce,)
        ).fetchone()

    if existing is not None:
        _write_audit(
            audit_writer,
            peer_row["id"],
            "replay_attempt",
            {"nonce": nonce, "reason": "nonce_already_seen"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="nonce_already_seen")

    return PeerTokenClaims(
        iss=iss,
        sub=verified["sub"],
        scopes=scopes,
        nonce=nonce,
    )


def consume_nonce(peer_id: str, nonce: str, exp: int) -> None:
    """Persist nonce to prevent replay. Call after successful auth."""
    expires_iso = datetime.fromtimestamp(exp / 1000, UTC).isoformat()
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO nonce_cache (nonce, peer_id, expires_at) VALUES (?,?,?)",
            (nonce, peer_id, expires_iso),
        )


# ---------------------------------------------------------------------------
# Declaration signature helpers (§5.6, §6.1)
# ---------------------------------------------------------------------------


def canonical_declaration_json(
    node_url: str,
    node_id: str,
    federation_pubkey: str,
    allowed_scopes: list[str],
    signed_at: str,
) -> bytes:
    """Canonical JSON for declaration signing — lexicographic key order, no whitespace."""
    obj = {
        "allowed_scopes": allowed_scopes,
        "federation_pubkey": federation_pubkey,
        "node_id": node_id,
        "node_url": node_url,
        "signed_at": signed_at,
    }
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()


def sign_declaration(
    node_url: str,
    node_id: str,
    allowed_scopes: list[str],
) -> tuple[str, str, str]:
    """Sign a peer declaration. Returns (federation_pubkey, declaration_sig, signed_at)."""
    priv, pubkey = get_or_create_keypair()
    signed_at = datetime.now(UTC).isoformat()
    message = canonical_declaration_json(node_url, node_id, pubkey, allowed_scopes, signed_at)
    sig_bytes = priv.sign(message)
    return pubkey, b64url_encode(sig_bytes), signed_at


def verify_declaration_sig(
    node_url: str,
    node_id: str,
    federation_pubkey: str,
    allowed_scopes: list[str],
    signed_at: str,
    declaration_sig: str,
) -> bool:
    """Return True if the declaration signature is valid."""
    try:
        pub_bytes = b64url_decode(federation_pubkey)
        public_key: Ed25519PublicKey = Ed25519PublicKey.from_public_bytes(pub_bytes)
        message = canonical_declaration_json(
            node_url, node_id, federation_pubkey, allowed_scopes, signed_at
        )
        sig_bytes = b64url_decode(declaration_sig)
        public_key.verify(sig_bytes, message)
        return True
    except (InvalidSignature, Exception):
        return False


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------


def _write_audit(
    audit_writer: Any | None,
    peer_id: str,
    event_type: str,
    detail: dict[str, Any],
) -> None:
    if audit_writer is not None:
        audit_writer(peer_id, event_type, detail)
