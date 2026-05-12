"""Federation protocol routes — spec §5.6–§5.9, §6, §19.2.3.

Routes:
  POST /v1/federation/peers             — register a peer (§5.6)
  GET  /v1/federation/peers             — list peers (§5.7)
  GET  /v1/federation/facts             — pull replication endpoint (§5.8)
  POST /v1/federation/facts/push        — optional push endpoint (§5.11)
  GET  /v1/federation/audit             — audit log (§6.4)
  GET  /v1/conflicts                    — list conflicts (§5.9)

Federation handshake extension (§19.2.3):
  register_peer checks for TL inclusion proof when trust_mode=strict (enforce).
  trust_mode=relaxed  → accept without proof, emit warning in audit log.
  trust_mode=off      → skip TL check entirely.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx  # noqa: F401  — re-exported for tests that patch federation.httpx.AsyncClient
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)

from ..auth import Identity, resolve_identity
from ..db import db
from ..federation_ingest import ingest_fact, write_audit_log
from ..hlc import node_hlc
from ..identity.capability import CapabilityTokenError, verify_token
from ..identity.trust_store import get_peer_manifest
from ..metrics import FEDERATION_EGRESS
from ..models import (
    ConflictResolveRequest,
    FederationFactsResponse,
    FederationTombstonesResponse,
    PeerRegisterRequest,
    PeerRegisterResponse,
    row_to_record,
)
from ..peer_token import TokenError, verify_peer_token
from ..plugins import Deny, TenantContext, get_registry
from ..settings import settings
from ..tls import check_peer_san
from ._federation_impl import (
    _check_tl_inclusion_for_peer,  # noqa: F401  — re-exported for tests
    federation_ingest_tombstone_impl,
    register_peer_impl,
)

logger = logging.getLogger("stigmem.federation")

router = APIRouter(tags=["federation"])


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------


def _allowed_output_scopes(peer: dict[str, Any], token_payload: dict[str, Any]) -> set[str]:
    """Intersection of peer's declaration allowed_scopes and token's scopes claim (§5.8)."""
    peer_scopes = set(json.loads(peer["allowed_scopes"]))
    token_scopes = set(token_payload.get("scopes", []))
    combined = peer_scopes & token_scopes
    combined.discard("local")
    if not settings.federation_allow_team:
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
            "SELECT * FROM peers WHERE node_id = ? AND status = 'active'",
            (iss,),
        ).fetchone()

    if peer_row is None:
        write_audit_log(iss, "rejected_token", {"reason": "peer_not_found_or_inactive", "iss": iss})
        raise HTTPException(status_code=401, detail="peer not registered or not active")

    peer = dict(peer_row)

    try:
        payload = verify_peer_token(raw_token, peer["federation_pubkey"], peer["id"])
    except TokenError as exc:
        event = "replay_attempt" if exc.kind == "nonce_already_seen" else "rejected_token"
        write_audit_log(peer["id"], event, {"reason": exc.kind})
        raise HTTPException(status_code=401, detail=exc.kind) from exc

    # §22.1.2.4 — bind TLS cert identity to JWT iss; rejects cert-swapping attacks.
    if settings.mtls_enabled:
        peer_cert = _get_mtls_peer_cert(request)
        if not check_peer_san(peer_cert, peer["node_id"]):
            write_audit_log(peer["id"], "san_mismatch", {"node_id": peer["node_id"]})
            raise HTTPException(
                status_code=401,
                detail="peer certificate URI SAN does not match node_id",
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
            "SELECT * FROM peers WHERE node_id = ? AND status = 'active'",
            (iss,),
        ).fetchone()

    if peer_row is None:
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


# ---------------------------------------------------------------------------
# POST /v1/federation/peers — register peer (§5.6)
# ---------------------------------------------------------------------------


@router.post(
    "/v1/federation/peers",
    response_model=PeerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_peer(
    req: PeerRegisterRequest,
    background_tasks: BackgroundTasks,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> PeerRegisterResponse:
    """Register a peer. Fetches its well-known doc and verifies declaration_sig (§5.6)."""
    # Implementation lives in _federation_impl.register_peer_impl.
    return await register_peer_impl(req, background_tasks, identity)


# ---------------------------------------------------------------------------
# GET /v1/federation/peers — list peers (§5.7)
# ---------------------------------------------------------------------------


@router.get("/v1/federation/peers")
def list_peers(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    if not identity.can_federate():
        raise HTTPException(status_code=403, detail="federate permission required")
    with db() as conn:
        rows = conn.execute(
            "SELECT id, node_id, node_url, status, allowed_scopes, established_at FROM peers"
        ).fetchall()
    return {
        "peers": [
            {
                "peer_id": r["id"],
                "node_id": r["node_id"],
                "node_url": r["node_url"],
                "status": r["status"],
                "allowed_scopes": json.loads(r["allowed_scopes"]),
                "established_at": r["established_at"],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# GET /v1/federation/facts — pull replication (§5.8)
# ---------------------------------------------------------------------------


@router.get("/v1/federation/facts", response_model=FederationFactsResponse)
def pull_facts(
    peer_and_token: PeerTokenDep,
    scope: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> FederationFactsResponse:
    """Return scope-filtered, HLC-cursor-paged facts to an authenticated peer (§5.8)."""
    peer, token_payload = peer_and_token

    permitted = _allowed_output_scopes(peer, token_payload)
    if not permitted:
        raise HTTPException(status_code=403, detail="no permitted scopes")

    if scope is not None:
        if scope not in permitted:
            write_audit_log(
                peer["id"], "scope_violation",
                {"requested_scope": scope, "permitted": list(permitted)},
            )
            raise HTTPException(status_code=403, detail="scope not permitted for this peer")
        query_scopes = {scope}
    else:
        query_scopes = permitted

    scope_placeholders = ",".join("?" * len(query_scopes))
    params: list[Any] = list(query_scopes)
    conditions: list[str] = [
        f"scope IN ({scope_placeholders})",
        "hlc IS NOT NULL",             # only facts with an HLC are replication-eligible
        "received_from IS NULL",       # do not re-federate inbound facts (§3.1)
        "entity NOT LIKE 'stigmem:conflict:%'",  # conflict entities are local (§6.5)
        "relation NOT LIKE 'stigmem:%'",         # meta-facts (received_from, ttl) are local
        "re_federation_blocked = 0",   # exclude company-scope relay-blocked facts (§6.8.2)
    ]
    if cursor:
        conditions.append("hlc > ?")
        params.append(cursor)

    where = " AND ".join(conditions)
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM facts WHERE {where} ORDER BY hlc ASC LIMIT ?",  # nosec B608 — where built from literal fragments; values in params
            params,
        ).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    seen: dict[tuple[str, str, str], int] = {}
    for r in rows:
        k = (r["entity"], r["relation"], r["scope"])
        seen[k] = seen.get(k, 0) + 1

    records = [
        row_to_record(r, contradicted=seen[(r["entity"], r["relation"], r["scope"])] > 1)
        for r in rows
    ]
    tenant = TenantContext(tenant_id="default")
    registry = get_registry()
    records = registry.fire_filter_chain(
        "federation_outbound_filter",
        records,
        peer=peer,
        token_payload=token_payload,
        tenant=tenant,
    )
    records = registry.fire_filter_chain(
        "federation_outbound_sign",
        records,
        peer=peer,
        token_payload=token_payload,
        tenant=tenant,
    )

    new_cursor: str | None = rows[-1]["hlc"] if rows else cursor
    FEDERATION_EGRESS.labels(peer_id=peer["node_id"], status="ok").inc(len(records))
    return FederationFactsResponse(facts=records, cursor=new_cursor, has_more=has_more)


# ---------------------------------------------------------------------------
# POST /v1/federation/facts/push — optional push (§5.11)
# ---------------------------------------------------------------------------


def _verify_push_cap_token(x_stigmem_capability: str) -> dict[str, Any]:
    """Verify a capability-token header for the push path (H-SEC-2).

    On verification failure logs ``capability_rejected`` and raises 401.
    On success returns the decoded token dict and logs ``capability_verified``.
    """
    try:
        verify_token(
            x_stigmem_capability,
            lambda uri: get_peer_manifest(
                uri, refresh_if_expired=True, trust_mode=settings.trust_mode
            ),
            trust_mode=settings.trust_mode,
        )
    except CapabilityTokenError as exc:
        # M-SEC-4: log capability_rejected
        import uuid as _uuid
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        _now = _datetime.now(_UTC).isoformat()
        try:
            import json as _json
            with db() as conn:
                conn.execute(
                    """INSERT INTO fact_audit_log
                       (id, fact_id, event_type, entity_uri, oidc_sub, source,
                        attested_key_id, detail, ts)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        str(_uuid.uuid4()),
                        "capability:rejected",
                        "capability_rejected",
                        None,
                        None,
                        "system:capability",
                        None,
                        _json.dumps({"reason": str(exc)}),
                        _now,
                    ),
                )
        except Exception as audit_exc:  # nosec B110 — audit log best-effort
            logger.debug("capability_rejected audit log failed: %s", audit_exc)
        raise HTTPException(
            status_code=401, detail=f"capability token invalid: {exc}"
        ) from exc

    try:
        cap_token: dict[str, Any] = json.loads(x_stigmem_capability)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"malformed capability token JSON: {exc}"
        ) from exc

    if cap_token.get("verb") != "write":
        raise HTTPException(
            status_code=403,
            detail="insufficient_capability: token verb must be 'write' for push",
        )

    # M-SEC-4: log capability_verified
    import uuid as _uuid2
    from datetime import UTC as _UTC2
    from datetime import datetime as _datetime2
    _now2 = _datetime2.now(_UTC2).isoformat()
    try:
        with db() as conn:
            conn.execute(
                """INSERT INTO fact_audit_log
                   (id, fact_id, event_type, entity_uri, oidc_sub, source,
                    attested_key_id, detail, ts)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    str(_uuid2.uuid4()),
                    cap_token.get("token_id", "unknown"),
                    "capability_verified",
                    cap_token.get("subject"),
                    None,
                    "system:capability",
                    None,
                    json.dumps({
                        "token_id": cap_token.get("token_id"),
                        "issuer": cap_token.get("issuer"),
                        "verb": cap_token.get("verb"),
                        "object": cap_token.get("object"),
                    }),
                    _now2,
                ),
            )
    except Exception as audit_exc:  # nosec B110 — audit log best-effort
        logger.debug("capability_verified audit log failed: %s", audit_exc)

    return cap_token


@router.post("/v1/federation/facts/push", status_code=202)
def push_facts(
    request: Request,
    body: dict[str, Any],
    authorization: Annotated[str | None, Header(alias="authorization")] = None,
    x_stigmem_capability: Annotated[str | None, Header(alias="x-stigmem-capability")] = None,
) -> dict[str, Any]:
    """Receive push-replicated facts from a peer (§5.11). Off by default.

    Auth (H-SEC-2): peer JWT first; if that fails and X-Stigmem-Capability is
    present, fall through to capability-token verification.  Capability tokens
    must carry verb=write and an object that covers all pushed fact scopes.
    """
    if not settings.federation_push_enabled:
        raise HTTPException(status_code=405, detail="push replication not enabled on this node")

    # --- Phase 1: try peer JWT auth ---
    peer_auth = _try_peer_token_auth(authorization)

    peer: dict[str, Any] | None = None
    token_payload: dict[str, Any] | None = None
    cap_token: dict[str, Any] | None = None
    using_cap_token = False

    if peer_auth is not None:
        peer, token_payload = peer_auth
        # §22.1.2.4 — enforce SAN on the push path too
        if settings.mtls_enabled:
            peer_cert = _get_mtls_peer_cert(request)
            if not check_peer_san(peer_cert, peer["node_id"]):
                write_audit_log(peer["id"], "san_mismatch", {"node_id": peer["node_id"]})
                raise HTTPException(
                status_code=401,
                detail="peer certificate URI SAN does not match node_id",
            )
    elif x_stigmem_capability is not None:
        cap_token = _verify_push_cap_token(x_stigmem_capability)
        using_cap_token = True
    else:
        raise HTTPException(
            status_code=401,
            detail="peer token or X-Stigmem-Capability header required",
        )

    facts = body.get("facts", [])
    accepted = 0
    rejected = 0
    errors: list[dict[str, Any]] = []

    for fact in facts:
        fact_scope = fact.get("scope", "")

        if using_cap_token:
            assert cap_token is not None
            ok, err = _push_fact_with_cap_token(fact, fact_scope, cap_token)
        else:
            assert peer is not None and token_payload is not None
            ok, err = _push_fact_with_peer_token(fact, fact_scope, peer, token_payload)

        if ok:
            accepted += 1
        else:
            rejected += 1
            if err is not None:
                errors.append(err)

    return {"accepted": accepted, "rejected": rejected, "errors": errors}


def _push_fact_with_cap_token(
    fact: dict[str, Any],
    fact_scope: str,
    cap_token: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Validate + ingest a single fact under capability-token auth.

    Returns (ok, error_dict_or_None).
    """
    # H-SEC-2: verify capability token object covers this fact's scope
    token_object = cap_token.get("object", "")
    if not _cap_token_covers_scope(token_object, fact_scope):
        return False, {
            "fact_id": fact.get("id"),
            "error": "insufficient_capability: token object does not cover scope",
        }

    sender_node_id = cap_token.get("subject", "")
    fact_source = fact.get("source", "")
    # Source non-forgery: source must match capability token subject
    if fact_source != sender_node_id:
        return False, {"fact_id": fact.get("id"), "error": "source_not_owned"}

    tenant = TenantContext(tenant_id="default")
    registry = get_registry()
    decision = registry.fire_voting(
        "federation_inbound_validate",
        fact=fact,
        fact_scope=fact_scope,
        cap_token=cap_token,
        tenant=tenant,
    )
    if isinstance(decision, Deny):
        return False, {"fact_id": fact.get("id"), "error": decision.reason}
    filtered_fact = registry.fire_filter_chain(
        "federation_inbound_filter",
        fact,
        fact_scope=fact_scope,
        cap_token=cap_token,
        tenant=tenant,
    )

    try:
        ingest_fact(
            filtered_fact,
            sender_node_id,
            identity_strength_boost=0.5,  # §19.4.2 boost for valid capability token
        )
        return True, None
    except Exception:
        return False, {"fact_id": fact.get("id"), "error": "ingest_error"}


def _push_fact_with_peer_token(
    fact: dict[str, Any],
    fact_scope: str,
    peer: dict[str, Any],
    token_payload: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Validate + ingest a single fact under peer-JWT auth.

    Returns (ok, error_dict_or_None).
    """
    permitted = _allowed_output_scopes(peer, token_payload)

    if fact_scope not in permitted:
        write_audit_log(
            peer["id"], "scope_violation",
            {"fact_id": fact.get("id"), "scope": fact_scope},
        )
        return False, {"fact_id": fact.get("id"), "error": "scope_not_permitted"}

    # Source non-forgery: source must match the sending peer's node_id (§6.4)
    fact_source = fact.get("source", "")
    if fact_source != peer["node_id"]:
        write_audit_log(
            peer["id"], "rejected_fact",
            {
                "fact_id": fact.get("id"),
                "reason": "source_not_owned",
                "source": fact_source,
                "peer_node_id": peer["node_id"],
            },
        )
        return False, {"fact_id": fact.get("id"), "error": "source_not_owned"}

    tenant = TenantContext(tenant_id="default")
    registry = get_registry()
    decision = registry.fire_voting(
        "federation_inbound_validate",
        fact=fact,
        fact_scope=fact_scope,
        peer=peer,
        token_payload=token_payload,
        tenant=tenant,
    )
    if isinstance(decision, Deny):
        return False, {"fact_id": fact.get("id"), "error": decision.reason}
    filtered_fact = registry.fire_filter_chain(
        "federation_inbound_filter",
        fact,
        fact_scope=fact_scope,
        peer=peer,
        token_payload=token_payload,
        tenant=tenant,
    )

    try:
        ingest_fact(
            filtered_fact,
            peer["node_id"],
            origin_allowed_scopes=json.loads(peer["allowed_scopes"]),
        )
        return True, None
    except Exception:
        return False, {"fact_id": fact.get("id"), "error": "ingest_error"}


# ---------------------------------------------------------------------------
# GET /v1/federation/audit — audit log (§6.4)
# ---------------------------------------------------------------------------


@router.get("/v1/federation/audit")
def get_audit_log(
    identity: Annotated[Identity, Depends(resolve_identity)],
    peer_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    if not identity.can_federate():
        raise HTTPException(status_code=403, detail="federate permission required")

    conditions: list[str] = []
    params: list[Any] = []
    if peer_id:
        conditions.append("peer_id = ?")
        params.append(peer_id)
    if cursor:
        conditions.append("id > ?")
        params.append(cursor)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM federation_audit {where} ORDER BY ts DESC, id DESC LIMIT ?",  # nosec B608 — where built from literal fragments; values in params
            params,
        ).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1]["id"] if has_more and rows else None

    return {
        "entries": [
            {
                "id": r["id"],
                "peer_id": r["peer_id"],
                "event_type": r["event_type"],
                "detail": json.loads(r["detail"]) if r["detail"] else None,
                "ts": r["ts"],
            }
            for r in rows
        ],
        "cursor": next_cursor,
        "has_more": has_more,
    }


# ---------------------------------------------------------------------------
# GET /v1/conflicts — list conflicts (§5.9)
# ---------------------------------------------------------------------------


@router.get("/v1/conflicts")
def list_conflicts(
    identity: Annotated[Identity, Depends(resolve_identity)],
    conflict_status: str | None = Query(None, alias="status"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    conditions: list[str] = []
    params: list[Any] = []
    if conflict_status:
        conditions.append("c.status = ?")
        params.append(conflict_status)
    if cursor:
        conditions.append("c.id > ?")
        params.append(cursor)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(
            "SELECT c.id, c.fact_a_id, c.fact_b_id, c.status, c.resolution_fact_id, c.detected_at"
            f" FROM conflicts c {where} ORDER BY c.detected_at DESC, c.id DESC LIMIT ?",  # nosec B608 — where built from literal fragments; values in params
            params,
        ).fetchall()

        conflicts: list[dict[str, Any]] = []
        for r in rows[:limit]:
            fa = conn.execute("SELECT * FROM facts WHERE id = ?", (r["fact_a_id"],)).fetchone()
            fb = conn.execute("SELECT * FROM facts WHERE id = ?", (r["fact_b_id"],)).fetchone()
            conflicts.append(
                {
                    "conflict_id": r["id"],
                    "fact_a": row_to_record(fa).model_dump() if fa else None,
                    "fact_b": row_to_record(fb).model_dump() if fb else None,
                    "status": r["status"],
                    "resolved_by": r["resolution_fact_id"],
                    "detected_at": r["detected_at"],
                }
            )

    has_more = len(rows) > limit
    next_cursor = rows[limit - 1]["id"] if has_more and len(rows) >= limit else None
    return {"conflicts": conflicts, "cursor": next_cursor, "has_more": has_more}


# ---------------------------------------------------------------------------
# POST /v1/conflicts/:conflict_id/resolve — resolve a conflict (§5.10)
# ---------------------------------------------------------------------------


def _encode_value(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)


@router.post("/v1/conflicts/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: str,
    req: ConflictResolveRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Assert a canonical resolution fact and close the conflict (spec §5.10)."""
    if not identity.can_write():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="write permission required"
        )

    with db() as conn:
        conflict = conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
        ).fetchone()

        if conflict is None:
            raise HTTPException(status_code=404, detail="conflict not found")
        if conflict["status"] == "resolved":
            raise HTTPException(status_code=409, detail="conflict already resolved")

        fact_a = conn.execute(
            "SELECT * FROM facts WHERE id = ?", (conflict["fact_a_id"],)
        ).fetchone()
        fact_b = conn.execute(
            "SELECT * FROM facts WHERE id = ?", (conflict["fact_b_id"],)
        ).fetchone()

        if fact_a is None or fact_b is None:
            raise HTTPException(status_code=500, detail="conflicting facts not found in store")

        # Determine value for the resolution fact
        if req.new_value is not None:
            res_type = req.new_value.type
            res_v = _encode_value(req.new_value.type, req.new_value.v)
        elif req.winning_fact_id is not None:
            if req.winning_fact_id == fact_a["id"]:
                winner = fact_a
            elif req.winning_fact_id == fact_b["id"]:
                winner = fact_b
            else:
                raise HTTPException(
                    status_code=422,
                    detail="winning_fact_id must be one of the conflicting facts",
                )
            res_type = winner["value_type"]
            res_v = winner["value_v"]
        else:
            raise HTTPException(
                status_code=422, detail="provide winning_fact_id or new_value"
            )

        resolution_fact_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        caller = identity.entity_uri

        # 1. Assert resolution fact under a namespaced entity so it never shares the
        #    (entity, relation, scope) triple with the conflicting facts. Writing under
        #    the original entity+relation would trigger a new contradiction wave when the
        #    fact is federated to peers (spec §resolution-semantics, EG-51).
        resolution_entity = f"stigmem:resolution:{conflict_id}"
        hlc_res = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                resolution_fact_id,
                resolution_entity,
                fact_a["relation"],
                res_type,
                res_v,
                caller,
                now,
                None,
                1.0,
                fact_a["scope"],
                hlc_res,
                None,
            ),
        )

        # 2. Assert stigmem:resolves meta-fact (spec §5.10)
        hlc_meta = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                resolution_fact_id,
                "stigmem:resolves",
                "ref",
                conflict_id,
                "system:stigmem",
                now,
                None,
                1.0,
                fact_a["scope"],
                hlc_meta,
                None,
            ),
        )

        # 3. Record updated conflict:status as a new fact (status changes are immutable appends)
        hlc_status = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                conflict_id,
                "stigmem:conflict:status",
                "string",
                "resolved",
                "system:stigmem",
                now,
                None,
                1.0,
                fact_a["scope"],
                hlc_status,
                None,
            ),
        )

        # 4. Update conflicts table
        conn.execute(
            "UPDATE conflicts SET status = 'resolved', resolution_fact_id = ? WHERE id = ?",
            (resolution_fact_id, conflict_id),
        )

    return {"resolution_fact_id": resolution_fact_id, "conflict_status": "resolved"}


# ---------------------------------------------------------------------------
# Tombstone federation routes (spec §23.4)
# ---------------------------------------------------------------------------

@router.get("/v1/federation/tombstones", response_model=FederationTombstonesResponse)
def federation_list_tombstones(
    request: Request,
    since: str | None = None,
    limit: int = 200,
    token_header: Annotated[str | None, Header(alias="Authorization")] = None,
) -> FederationTombstonesResponse:
    """Tombstone poll route (§23.4.3). Requires tombstone:read capability token."""
    from ..identity.capability import CapabilityTokenError, verify_token
    from ..tombstones import list_revocations, list_tombstones

    raw_token = None
    if token_header and token_header.startswith("Bearer "):
        raw_token = token_header[7:]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="capability token required",
        )

    if settings.trust_mode != "off":
        try:
            import json as _json
            token_data = _json.loads(raw_token) if raw_token.startswith("{") else {}
            verbs = token_data.get("verbs", token_data.get("verb", ""))
            if isinstance(verbs, str):
                verbs = [v.strip() for v in verbs.split(",")] if verbs else []
            if "tombstone:read" not in verbs and "admin" not in verbs:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="tombstone:read capability required",
                )
            verify_token(
                raw_token,
                lambda uri: get_peer_manifest(
                    uri, refresh_if_expired=True, trust_mode=settings.trust_mode
                ),
                trust_mode=settings.trust_mode,
            )
        except CapabilityTokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    else:
        import logging as _logging
        _logging.getLogger("stigmem.federation").warning(
            "tombstone poll: trust_mode=off — token signature verification skipped"
        )

    tombstone_list = list_tombstones(since=since)[:limit]
    revocation_list = list_revocations(since=since)[:limit]
    cursor = tombstone_list[-1].created_at if tombstone_list else None
    return FederationTombstonesResponse(
        tombstones=tombstone_list,
        revocations=revocation_list,
        cursor=cursor,
    )


@router.post("/v1/federation/tombstones/ingest", status_code=status.HTTP_200_OK)
def federation_ingest_tombstone(
    request: Request,
    payload: dict[str, Any],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_stigmem_capability: Annotated[str | None, Header(alias="x-stigmem-capability")] = None,
) -> dict[str, Any]:
    """Inbound tombstone push from a federation peer (§23.4.2).

    Auth: peer JWT or capability token with tombstone:write verb (mirrors push_facts).
    Verifies signature against org manifest, writes to local tombstones table.
    """
    # Implementation lives in _federation_impl.federation_ingest_tombstone_impl.
    return federation_ingest_tombstone_impl(
        request,
        payload,
        authorization,
        x_stigmem_capability,
        _try_peer_token_auth,
        _get_mtls_peer_cert,
    )
