"""Shared helpers and compatibility exports for federation route modules."""

from __future__ import annotations

import json
import logging
import sys
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ...db import db
from ...federation.peer_token import TokenError, verify_peer_token
from ...federation.tls import check_peer_san

logger = logging.getLogger("stigmem.federation")

router = APIRouter(tags=["federation"])


def _public_module() -> Any:
    """Return the public federation module so test monkey-patches stay visible."""
    return sys.modules["stigmem_node.routes.federation"]

def _allowed_output_scopes(peer: dict[str, Any], token_payload: dict[str, Any]) -> set[str]:
    """Intersection of peer's declaration allowed_scopes and token's scopes claim (§5.8)."""
    peer_scopes = set(json.loads(peer["allowed_scopes"]))
    token_scopes = set(token_payload.get("scopes", []))
    combined = peer_scopes & token_scopes
    combined.discard("local")
    if not _public_module().settings.federation_allow_team:
        combined.discard("team")
    return combined


# ---------------------------------------------------------------------------
# Peer-token dependency
# ---------------------------------------------------------------------------


def _get_mtls_peer_cert(request: Request) -> dict[str, Any]:
    """Extract the TLS peer certificate dict from the ASGI transport (uvicorn).

    Returns an empty dict when not running under TLS (tests, plaintext mode).
    """
    transport = request.scope.get("transport")
    if transport is None:
        return {}
    ssl_obj = transport.get_extra_info("ssl_object")
    if ssl_obj is None:
        return {}
    return ssl_obj.getpeercert() or {}


def _require_peer_token(
    request: Request,
    authorization: Annotated[str | None, Header(alias="authorization")] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify incoming peer token. Returns (peer_dict, token_payload) or raises 401."""
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="peer token required")

    raw_token = authorization[7:]

    # Decode header without sig verification to extract iss
    import jwt as _jwt

    try:
        # exp/iat are epoch_ms per spec §3.5; disable all claim validation for header-only peek
        unverified: dict[str, Any] = _jwt.decode(
            raw_token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": False,
            },
            algorithms=["EdDSA"],
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="malformed token") from exc

    iss = unverified.get("iss", "")

    with db() as conn:
        peer_row = conn.execute(
            "SELECT * FROM peers WHERE node_id = ?",
            (iss,),
        ).fetchone()

    if peer_row is None:
        _public_module().write_audit_log(
            iss, "rejected_token", {"reason": "peer_not_found", "iss": iss}
        )
        raise HTTPException(status_code=401, detail="peer not registered")

    if peer_row["status"] != "active":
        _public_module().write_audit_log(
            peer_row["id"],
            "rejected_token",
            {"reason": "peer_not_approved", "iss": iss, "status": peer_row["status"]},
        )
        raise HTTPException(status_code=401, detail="peer_not_approved")

    peer = dict(peer_row)

    try:
        payload = verify_peer_token(raw_token, peer["federation_pubkey"], peer["id"])
    except TokenError as exc:
        event = "replay_attempt" if exc.kind == "nonce_already_seen" else "rejected_token"
        _public_module().write_audit_log(peer["id"], event, {"reason": exc.kind})
        raise HTTPException(status_code=401, detail=exc.kind) from exc

    # §22.1.2.4 — bind TLS cert identity to JWT iss; rejects cert-swapping attacks.
    if _public_module().settings.mtls_enabled:
        peer_cert = _get_mtls_peer_cert(request)
        if peer_cert and not check_peer_san(peer_cert, peer["node_id"]):
            _public_module().write_audit_log(
                peer["id"], "san_mismatch", {"node_id": peer["node_id"]}
            )
            raise HTTPException(
                status_code=401,
                detail="peer certificate URI SAN does not match node_id",
            )
        if not peer_cert:
            logger.warning(
                "mTLS peer certificate was not exposed by the ASGI server; "
                "falling back to TLS-layer client certificate verification for %s",
                peer["node_id"],
            )

    return peer, payload


PeerTokenDep = Annotated[tuple[dict[str, Any], dict[str, Any]], Depends(_require_peer_token)]


def _try_peer_token_auth(
    authorization: str | None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Soft peer-JWT auth: returns (peer, payload) on success, None on failure.

    Unlike _require_peer_token, never raises — used so push_facts can fall
    through to the capability-token path when peer JWT is absent or invalid.
    """
    if authorization is None or not authorization.lower().startswith("bearer "):
        return None

    raw_token = authorization[7:]

    import jwt as _jwt

    try:
        unverified: dict[str, Any] = _jwt.decode(
            raw_token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": False,
            },
            algorithms=["EdDSA"],
        )
    except Exception:
        return None

    iss = unverified.get("iss", "")
    with db() as conn:
        peer_row = conn.execute(
            "SELECT * FROM peers WHERE node_id = ?",
            (iss,),
        ).fetchone()

    if peer_row is None or peer_row["status"] != "active":
        return None

    peer = dict(peer_row)
    try:
        payload = verify_peer_token(raw_token, peer["federation_pubkey"], peer["id"])
    except TokenError:
        return None

    return peer, payload


def _cap_token_covers_scope(token_object: str, scope: str) -> bool:
    """Return True if the capability token's object covers the given fact scope (H-SEC-2)."""
    # "stigmem://facts" is a wildcard covering all scopes
    if token_object == "stigmem://facts":  # nosec B105 — URI scheme constant, not a password
        return True
    # "stigmem://facts/scope:X" covers exactly scope X
    return token_object == f"stigmem://facts/scope:{scope}"
