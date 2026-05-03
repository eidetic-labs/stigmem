"""Track B / B3 — OIDC → scoped API-key exchange bridge.

POST /v1/auth/oidc/exchange   validate id_token, mint/refresh a scoped key
GET  /v1/auth/keys            list caller's own keys
DELETE /v1/auth/keys/{key_id} revoke a specific key
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import Identity, create_api_key, resolve_identity
from ..db import db
from ..settings import settings

logger = logging.getLogger("stigmem.auth")
router = APIRouter(prefix="/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# JWKS cache — keyed by issuer URL, value = (jwks_client, fetched_at_unix)
# ---------------------------------------------------------------------------
_JWKS_CACHE: dict[str, tuple[jwt.PyJWKClient, float]] = {}
_JWKS_CACHE_TTL = 600  # 10 minutes


def _get_jwks_client(issuer_url: str) -> jwt.PyJWKClient:
    entry = _JWKS_CACHE.get(issuer_url)
    now = time.monotonic()
    if entry and (now - entry[1]) < _JWKS_CACHE_TTL:
        return entry[0]

    # Discover JWKS URI from OIDC metadata document
    disco_url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    try:
        resp = httpx.get(disco_url, timeout=5.0)
        resp.raise_for_status()
        jwks_uri: str = resp.json()["jwks_uri"]
    except Exception as exc:
        logger.warning("OIDC discovery failed for %s: %s", issuer_url, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC provider discovery failed",
        ) from exc

    client = jwt.PyJWKClient(jwks_uri)
    _JWKS_CACHE[issuer_url] = (client, now)
    return client


def _verify_id_token(id_token: str) -> dict[str, Any]:
    """Validate the id_token and return decoded claims. Raises HTTPException on failure."""
    jwks_client = _get_jwks_client(settings.oidc_issuer_url)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        claims: dict[str, Any] = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer_url,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="id_token expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="id_token audience mismatch") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"id_token invalid: {exc}") from exc
    return claims


def _check_domain(email: str | None) -> None:
    """Enforce oidc_allowed_domains if configured."""
    if not settings.oidc_allowed_domains or not email:
        return
    allowed = {d.strip().lower() for d in settings.oidc_allowed_domains.split(",") if d.strip()}
    if not allowed:
        return
    domain = email.split("@", 1)[-1].lower()
    if domain not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email domain '{domain}' is not permitted",
        )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

_ALLOWED_PERMISSIONS = {"read", "write"}


class ExchangeRequest(BaseModel):
    id_token: str
    permissions: list[str] = Field(default=["read", "write"])


class ExchangeResponse(BaseModel):
    api_key: str
    entity_uri: str
    expires_at: str


class KeyInfo(BaseModel):
    id: str
    entity_uri: str
    permissions: list[str]
    description: str | None
    created_at: str
    expires_at: str | None
    oidc_sub: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/oidc/exchange", response_model=ExchangeResponse)
def oidc_exchange(body: ExchangeRequest) -> ExchangeResponse:
    """Exchange an OIDC id_token for a scoped stigmem API key."""
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC authentication is not enabled on this node",
        )

    # Sanitise permissions: cap at read+write, no federate via OIDC
    requested = {p for p in body.permissions if p in _ALLOWED_PERMISSIONS}
    if not requested:
        requested = {"read"}
    permissions = sorted(requested, key=lambda p: ["read", "write"].index(p))

    claims = _verify_id_token(body.id_token)
    sub: str = claims["sub"]
    email: str | None = claims.get("email")
    _check_domain(email)

    entity_uri = f"oidc:{sub}"
    expires_at = (datetime.now(UTC) + timedelta(hours=settings.oidc_token_ttl_hours)).isoformat()

    # Rotate: revoke all previous OIDC-issued keys for this sub before minting
    # a new one.  This ensures a single valid session per sub so that IdP
    # session-termination (logout, account suspension) immediately invalidates
    # access — offboarding comes for free from the IdP.
    with db() as conn:
        conn.execute("DELETE FROM api_keys WHERE oidc_sub = ?", (sub,))

    raw_key = create_api_key(
        entity_uri=entity_uri,
        permissions=permissions,
        description=f"OIDC session for {email or sub}",
        expires_at=expires_at,
        oidc_sub=sub,
    )

    logger.info("OIDC exchange: sub=%s entity_uri=%s perms=%s", sub, entity_uri, permissions)
    return ExchangeResponse(api_key=raw_key, entity_uri=entity_uri, expires_at=expires_at)


@router.get("/keys", response_model=list[KeyInfo])
def list_keys(identity: Annotated[Identity, Depends(resolve_identity)]) -> list[KeyInfo]:
    """List all non-expired API keys belonging to the caller's entity_uri."""
    with db() as conn:
        rows = conn.execute(
            """SELECT id, entity_uri, permissions, description, created_at, expires_at, oidc_sub
               FROM api_keys
               WHERE entity_uri = ?
                 AND (expires_at IS NULL OR expires_at > ?)
               ORDER BY created_at DESC""",
            (identity.entity_uri, datetime.now(UTC).isoformat()),
        ).fetchall()
    return [
        KeyInfo(
            id=r["id"],
            entity_uri=r["entity_uri"],
            permissions=json.loads(r["permissions"]),
            description=r["description"],
            created_at=r["created_at"],
            expires_at=r["expires_at"],
            oidc_sub=r["oidc_sub"],
        )
        for r in rows
    ]


@router.delete("/keys/{key_id}", status_code=204)
def revoke_key(
    key_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    """Revoke a specific API key. Callers may only revoke their own keys."""
    with db() as conn:
        row = conn.execute(
            "SELECT entity_uri FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
        if row["entity_uri"] != identity.entity_uri:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke another entity's key")
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    logger.info("Key revoked: id=%s by entity=%s", key_id, identity.entity_uri)
