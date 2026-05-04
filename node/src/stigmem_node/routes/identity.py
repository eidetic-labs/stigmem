"""Org-identity API routes — spec §19.1–§19.3, §19.5.

Routes:
  PUT  /v1/federation/manifest                        — publish/update org manifest
  GET  /v1/federation/manifest/{entity_uri_encoded}   — resolve manifest
  POST /v1/federation/capability-tokens               — issue capability token
  POST /v1/federation/capability-tokens/{token_id}/revoke — revoke token
  POST /v1/gardens/{id}/promote                       — quarantine moderation (garden-scoped)
  POST /v1/gardens/{id}/reject                        — quarantine moderation (garden-scoped)

Security requirements enforced here:
  C1: token subject MUST appear in issuer's manifest entities list.
  H1: expired manifest → reject token issuance (handled via get_peer_manifest).
  H2: TL unavailable in strict mode → HTTP 503 (not silent fallback).
  Rate-limit manifest PUT: ≤ 10 per entity_uri per hour.
  Nonce: 64-char lowercase hex (secrets.token_hex(32)).
  Cleanup: expired tokens pruned opportunistically on issuance.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..garden_acl import get_garden_by_slug_or_id, require_quarantine_moderator_or_admin
from ..identity.manifest import (
    ManifestError,
    manifest_from_dict,
    manifest_to_dict,
    verify_manifest,
)
from ..identity.transparency_log import TransparencyLogUnavailable, make_transparency_log
from ..identity.trust_store import (
    cleanup_expired_tokens,
    get_peer_manifest,
    store_peer_manifest,
)
from ..models import QuarantinePromoteRequest, QuarantineRejectRequest, QUARANTINE_PENDING
from ..settings import settings

router = APIRouter(tags=["identity"])
logger = logging.getLogger("stigmem.routes.identity")

# ---------------------------------------------------------------------------
# Manifest-PUT rate limiter: { entity_uri: [epoch_s, ...] } (in-process)
# ---------------------------------------------------------------------------

_MANIFEST_SUBMIT_WINDOW_S = 3600
_MANIFEST_SUBMIT_LIMIT = 10
_manifest_submit_log: dict[str, list[float]] = {}


def _check_manifest_rate_limit(entity_uri: str) -> None:
    now = time.monotonic()
    window_start = now - _MANIFEST_SUBMIT_WINDOW_S
    timestamps = [t for t in _manifest_submit_log.get(entity_uri, []) if t > window_start]
    if len(timestamps) >= _MANIFEST_SUBMIT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"manifest PUT rate limit: max {_MANIFEST_SUBMIT_LIMIT} per hour per entity_uri",
        )
    timestamps.append(now)
    _manifest_submit_log[entity_uri] = timestamps


# ---------------------------------------------------------------------------
# PUT /v1/federation/manifest
# ---------------------------------------------------------------------------


@router.put("/v1/federation/manifest", status_code=status.HTTP_200_OK)
async def put_manifest(
    body: dict[str, Any],
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Publish or update an org manifest.

    Rate-limited to 10 submissions per entity_uri per hour.
    rotation_events arrays with > 100 entries are rejected.
    TL submission is attempted; in strict mode TL failure → 503.
    """
    if not identity.can_write():
        raise HTTPException(status_code=403, detail="write permission required")

    entity_uri = body.get("entity_uri", "")
    if not entity_uri:
        raise HTTPException(status_code=422, detail="entity_uri is required")

    _check_manifest_rate_limit(entity_uri)

    rotation_events = body.get("rotation_events", [])
    if len(rotation_events) > 100:
        raise HTTPException(
            status_code=422,
            detail="rotation_events must not exceed 100 entries",
        )

    try:
        manifest = manifest_from_dict(body)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid manifest: {exc}") from exc

    try:
        verify_manifest(manifest, trust_mode=settings.trust_mode)
    except ManifestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Attempt transparency-log submission
    tl = make_transparency_log()
    log_entry = None
    tl_error: str | None = None

    try:
        log_entry = tl.submit(manifest_to_dict(manifest))
    except TransparencyLogUnavailable as exc:
        tl_error = str(exc)
        if settings.trust_mode == "strict":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"transparency log unavailable (strict mode rejects): {exc}",
            )
        logger.warning("TL unavailable during manifest PUT (warn mode): %s", exc)

    try:
        store_peer_manifest(
            entity_uri, manifest, log_entry, trust_mode=settings.trust_mode
        )
    except ManifestError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    result: dict[str, Any] = {
        "entity_uri": entity_uri,
        "key_id": manifest.key_id,
        "issued_at": manifest.issued_at,
        "expires_at": manifest.expires_at,
    }
    if log_entry is not None:
        result["log_entry"] = {
            "log_id": log_entry.log_id,
            "log_index": log_entry.log_index,
            "leaf_hash": log_entry.leaf_hash,
            "integrated_time": log_entry.integrated_time,
        }
    if tl_error is not None:
        result["tl_warning"] = tl_error
    return result


# ---------------------------------------------------------------------------
# GET /v1/federation/manifest/{entity_uri_encoded}
# ---------------------------------------------------------------------------


@router.get("/v1/federation/manifest/{entity_uri_encoded:path}")
def get_manifest(
    entity_uri_encoded: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Resolve a peer manifest by entity_uri (URL-encoded or raw path)."""
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    entity_uri = unquote(entity_uri_encoded)
    manifest = get_peer_manifest(
        entity_uri, refresh_if_expired=True, trust_mode=settings.trust_mode
    )
    if manifest is None:
        raise HTTPException(status_code=404, detail="manifest not found or expired")

    with db() as conn:
        row = conn.execute(
            "SELECT log_entry_json FROM federation_manifests WHERE entity_uri = ?",
            (entity_uri,),
        ).fetchone()

    result = manifest_to_dict(manifest)
    if row and row["log_entry_json"]:
        result["log_entry"] = json.loads(row["log_entry_json"])
    return result


# ---------------------------------------------------------------------------
# POST /v1/federation/capability-tokens
# ---------------------------------------------------------------------------


@router.post(
    "/v1/federation/capability-tokens",
    status_code=status.HTTP_201_CREATED,
)
def issue_capability_token(
    body: dict[str, Any],
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Issue a capability token.

    C1: token subject must appear in the issuer's manifest entities list.
    H1: issuer manifest must not be expired.
    Nonce: 64-char lowercase hex enforced by DB CHECK constraint.
    """
    if not identity.can_write():
        raise HTTPException(status_code=403, detail="write permission required")

    issuer = body.get("issuer", "")
    subject = body.get("subject", "")
    verb = body.get("verb", "")
    obj = body.get("object", "")
    ttl_seconds: int = int(body.get("ttl_seconds", 3600))

    if not all([issuer, subject, verb, obj]):
        raise HTTPException(
            status_code=422, detail="issuer, subject, verb, and object are required"
        )

    # H1: resolve issuer manifest (checks expiry, refreshes if needed)
    issuer_manifest = get_peer_manifest(
        issuer, refresh_if_expired=True, trust_mode=settings.trust_mode
    )
    if issuer_manifest is None:
        raise HTTPException(
            status_code=422,
            detail=f"issuer manifest not found or expired for {issuer!r} "
                   "(H1: cannot issue tokens from expired manifests)",
        )

    # C1: subject must be in issuer's entities list
    if subject not in issuer_manifest.entities:
        raise HTTPException(
            status_code=403,
            detail=f"subject {subject!r} is not in issuer {issuer!r} entities list "
                   "(C1: external-entity delegation not permitted)",
        )

    now = datetime.now(UTC)
    issued_at = now.isoformat()
    expiry = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=UTC).isoformat()
    token_id = str(uuid.uuid4())
    nonce = secrets.token_hex(32)  # 64 lowercase hex chars — satisfies DB CHECK

    token_body: dict[str, Any] = {
        "token_id": token_id,
        "issuer": issuer,
        "subject": subject,
        "verb": verb,
        "object": obj,
        "issued_at": issued_at,
        "expiry": expiry,
        "nonce": nonce,
    }

    import canonicaljson
    token_json = canonicaljson.encode_canonical_json(token_body).decode()

    created_at = now.isoformat()
    with db() as conn:
        try:
            conn.execute(
                """INSERT INTO capability_tokens
                   (id, token_json, issuer, subject, verb, object,
                    issued_at, expiry, nonce, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (token_id, token_json, issuer, subject, verb, obj,
                 issued_at, expiry, nonce, created_at),
            )
        except Exception as exc:
            if "UNIQUE constraint" in str(exc):
                raise HTTPException(status_code=409, detail="nonce collision; retry")
            raise

    # Opportunistic cleanup of stale tokens
    try:
        cleanup_expired_tokens()
    except Exception:
        pass  # nosec B110 — cleanup is best-effort

    return {
        "token_id": token_id,
        "issuer": issuer,
        "subject": subject,
        "verb": verb,
        "object": obj,
        "issued_at": issued_at,
        "expiry": expiry,
        "nonce": nonce,
        "token_json": token_json,
    }


# ---------------------------------------------------------------------------
# POST /v1/federation/capability-tokens/{token_id}/revoke
# ---------------------------------------------------------------------------


@router.post(
    "/v1/federation/capability-tokens/{token_id}/revoke",
    status_code=status.HTTP_200_OK,
)
async def revoke_capability_token(
    token_id: str,
    body: dict[str, Any],
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Revoke a capability token and submit a revocation notice to the TL."""
    if not identity.can_write():
        raise HTTPException(status_code=403, detail="write permission required")

    now = datetime.now(UTC).isoformat()
    reason = body.get("reason", "")

    with db() as conn:
        row = conn.execute(
            "SELECT id, issuer, revoked_at FROM capability_tokens WHERE id = ?",
            (token_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="capability token not found")
    if row["revoked_at"] is not None:
        raise HTTPException(status_code=409, detail="token already revoked")

    revoke_event = {
        "token_id": token_id,
        "revoked_by": identity.entity_uri,
        "revoked_at": now,
        "reason": reason,
    }

    # Submit revocation to TL (best-effort; log warning in non-strict mode)
    tl = make_transparency_log()
    tl_error: str | None = None
    tl_entry = None
    try:
        tl_entry = tl.submit(revoke_event)
    except TransparencyLogUnavailable as exc:
        tl_error = str(exc)
        if settings.trust_mode == "strict":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"transparency log unavailable during revocation (strict mode): {exc}",
            )
        logger.warning("TL unavailable during token revocation (warn mode): %s", exc)

    revoke_log_json = json.dumps({
        **revoke_event,
        **({"tl_entry": {
            "log_id": tl_entry.log_id,
            "log_index": tl_entry.log_index,
            "leaf_hash": tl_entry.leaf_hash,
        }} if tl_entry else {}),
    })

    with db() as conn:
        conn.execute(
            "UPDATE capability_tokens SET revoked_at = ?, revoke_log = ? WHERE id = ?",
            (now, revoke_log_json, token_id),
        )

    result: dict[str, Any] = {"token_id": token_id, "revoked_at": now, "status": "revoked"}
    if tl_error:
        result["tl_warning"] = tl_error
    return result


# ---------------------------------------------------------------------------
# POST /v1/gardens/{id}/promote — garden-scoped quarantine moderation
# ---------------------------------------------------------------------------


@router.post("/v1/gardens/{garden_id}/promote", status_code=status.HTTP_200_OK)
def garden_promote_fact(
    garden_id: str,
    req: QuarantinePromoteRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Promote a quarantined fact from *garden_id* to a target garden.

    Requires quarantine:moderator or admin role in the quarantine garden.
    """
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    garden = get_garden_by_slug_or_id(garden_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=404, detail="garden not found")

    if not identity.can_write():
        require_quarantine_moderator_or_admin(garden, identity)

    now = datetime.now(UTC).isoformat()

    with db() as conn:
        fact_row = conn.execute(
            "SELECT id, quarantine_status, quarantine_garden_id FROM facts WHERE id = ?",
            (req.fact_id,),
        ).fetchone()

    if fact_row is None:
        raise HTTPException(status_code=404, detail="fact not found")
    if fact_row["quarantine_status"] != QUARANTINE_PENDING:
        raise HTTPException(status_code=409, detail="fact is not in quarantine_pending status")
    if fact_row["quarantine_garden_id"] != garden["id"]:
        raise HTTPException(
            status_code=409,
            detail="fact is not in the specified quarantine garden",
        )

    # Resolve target garden
    target_db_id: str | None = None
    if req.target_garden_id:
        tg = get_garden_by_slug_or_id(req.target_garden_id, tenant_id=identity.tenant_id)
        if tg is None:
            raise HTTPException(status_code=404, detail="target garden not found")
        target_db_id = tg["id"]

    with db() as conn:
        conn.execute(
            """UPDATE facts
               SET garden_id = ?,
                   quarantine_status = 'promoted',
                   quarantine_acted_by = ?,
                   quarantine_acted_at = ?,
                   quarantine_reason = ?
               WHERE id = ?""",
            (target_db_id, identity.entity_uri, now, req.reason or "promoted via garden API", req.fact_id),
        )
        _write_quarantine_audit(conn, req.fact_id, "quarantine_promote", identity, now)

    return {
        "fact_id": req.fact_id,
        "action": "promoted",
        "garden_id": garden_id,
        "target_garden_id": target_db_id,
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }


# ---------------------------------------------------------------------------
# POST /v1/gardens/{id}/reject — garden-scoped quarantine moderation
# ---------------------------------------------------------------------------


@router.post("/v1/gardens/{garden_id}/reject", status_code=status.HTTP_200_OK)
def garden_reject_fact(
    garden_id: str,
    req: QuarantineRejectRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Permanently reject a quarantined fact in *garden_id*.

    Sets confidence = 0.0 and quarantine_status = 'rejected'.
    Requires quarantine:moderator or admin role in the quarantine garden.
    """
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    garden = get_garden_by_slug_or_id(garden_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=404, detail="garden not found")

    if not identity.can_write():
        require_quarantine_moderator_or_admin(garden, identity)

    now = datetime.now(UTC).isoformat()

    with db() as conn:
        fact_row = conn.execute(
            "SELECT id, quarantine_status, quarantine_garden_id FROM facts WHERE id = ?",
            (req.fact_id,),
        ).fetchone()

    if fact_row is None:
        raise HTTPException(status_code=404, detail="fact not found")
    if fact_row["quarantine_status"] != QUARANTINE_PENDING:
        raise HTTPException(status_code=409, detail="fact is not in quarantine_pending status")
    if fact_row["quarantine_garden_id"] != garden["id"]:
        raise HTTPException(
            status_code=409,
            detail="fact is not in the specified quarantine garden",
        )

    with db() as conn:
        conn.execute(
            """UPDATE facts
               SET confidence = 0.0,
                   quarantine_status = 'rejected',
                   quarantine_acted_by = ?,
                   quarantine_acted_at = ?,
                   quarantine_reason = ?
               WHERE id = ?""",
            (identity.entity_uri, now, req.reason or "rejected via garden API", req.fact_id),
        )
        _write_quarantine_audit(conn, req.fact_id, "quarantine_reject", identity, now)

    return {
        "fact_id": req.fact_id,
        "action": "rejected",
        "garden_id": garden_id,
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _write_quarantine_audit(
    conn: Any, fact_id: str, event_type: str, identity: Identity, now: str
) -> None:
    audit_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO fact_audit_log "
        "(id, fact_id, event_type, entity_uri, oidc_sub, source, attested_key_id, ts) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (audit_id, fact_id, event_type, identity.entity_uri, identity.oidc_sub,
         identity.entity_uri, None, now),
    )
