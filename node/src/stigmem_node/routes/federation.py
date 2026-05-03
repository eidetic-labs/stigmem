"""Federation protocol routes — spec §5.6–§5.9, §6.

Routes:
  POST /v1/federation/peers             — register a peer (§5.6)
  GET  /v1/federation/peers             — list peers (§5.7)
  GET  /v1/federation/facts             — pull replication endpoint (§5.8)
  POST /v1/federation/facts/push        — optional push endpoint (§5.11)
  GET  /v1/federation/audit             — audit log (§6.4)
  GET  /v1/conflicts                    — list conflicts (§5.9)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..auth import Identity, resolve_identity
from ..db import db, get_or_create_node_id
from ..federation_ingest import ingest_fact, write_audit_log
from ..hlc import node_hlc
from ..models import (
    ConflictResolveRequest,
    FederationFactsResponse,
    FactRecord,
    PeerRecord,
    PeerRegisterRequest,
    PeerRegisterResponse,
    row_to_record,
)
from ..peer_token import TokenError, verify_declaration_sig, verify_peer_token
from ..settings import settings

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


def _require_peer_token(
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
    except Exception:
        raise HTTPException(status_code=401, detail="malformed token")

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
        raise HTTPException(status_code=401, detail=exc.kind)

    return peer, payload


PeerTokenDep = Annotated[tuple[dict[str, Any], dict[str, Any]], Depends(_require_peer_token)]


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
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> PeerRegisterResponse:
    """Register a peer. Fetches its well-known doc and verifies declaration_sig (§5.6)."""
    if not identity.can_federate():
        raise HTTPException(status_code=403, detail="federate permission required")

    peer_id = str(uuid.uuid4())
    allowed_scopes_json = json.dumps(sorted(req.allowed_scopes))

    with db() as conn:
        existing = conn.execute(
            "SELECT id, status FROM peers WHERE node_id = ?", (req.node_id,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"peer already registered (status={existing['status']})",
            )
        conn.execute(
            """INSERT INTO peers
               (id, node_id, node_url, federation_pubkey, allowed_scopes,
                status, established_at, declaration_sig, signed_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                peer_id,
                req.node_id,
                req.node_url,
                req.federation_pubkey,
                allowed_scopes_json,
                "pending_verification",
                None,
                req.declaration_sig,
                req.signed_at,
            ),
        )

    # Fetch peer's /.well-known/stigmem to retrieve their published pubkey (§5.6 step 1–3)
    fetched_pubkey: str | None = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            wk_resp = await client.get(f"{req.node_url}/.well-known/stigmem")
        if wk_resp.status_code == 200:
            fetched_pubkey = wk_resp.json().get("federation_pubkey")
    except Exception:
        pass  # fetched_pubkey stays None → rejected below

    final_status = "rejected"
    verified_at: str | None = None

    if fetched_pubkey and fetched_pubkey == req.federation_pubkey:
        # Signed fields are everything except declaration_sig itself (spec §6.1 struct "above fields")
        signed_fields: dict[str, Any] = {
            "allowed_scopes": req.allowed_scopes,
            "federation_pubkey": req.federation_pubkey,
            "node_id": req.node_id,
            "node_url": req.node_url,
            "signed_at": req.signed_at,
        }
        if verify_declaration_sig(signed_fields, req.declaration_sig, fetched_pubkey):
            final_status = "active"
            verified_at = datetime.now(UTC).isoformat()

    with db() as conn:
        conn.execute(
            "UPDATE peers SET status = ?, established_at = ? WHERE id = ?",
            (final_status, verified_at, peer_id),
        )

    return PeerRegisterResponse(peer_id=peer_id, status=final_status, verified_at=verified_at)


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
    ]
    if cursor:
        conditions.append("hlc > ?")
        params.append(cursor)

    where = " AND ".join(conditions)
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM facts WHERE {where} ORDER BY hlc ASC LIMIT ?",
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

    new_cursor: str | None = rows[-1]["hlc"] if rows else cursor
    return FederationFactsResponse(facts=records, cursor=new_cursor, has_more=has_more)


# ---------------------------------------------------------------------------
# POST /v1/federation/facts/push — optional push (§5.11)
# ---------------------------------------------------------------------------


@router.post("/v1/federation/facts/push", status_code=202)
def push_facts(
    peer_and_token: PeerTokenDep,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Receive push-replicated facts from a peer (§5.11). Off by default."""
    if not settings.federation_push_enabled:
        raise HTTPException(status_code=405, detail="push replication not enabled on this node")

    peer, token_payload = peer_and_token
    permitted = _allowed_output_scopes(peer, token_payload)

    facts = body.get("facts", [])
    accepted = 0
    rejected = 0
    errors: list[dict[str, Any]] = []

    for fact in facts:
        fact_scope = fact.get("scope", "")
        if fact_scope not in permitted:
            write_audit_log(
                peer["id"], "scope_violation",
                {"fact_id": fact.get("id"), "scope": fact_scope},
            )
            rejected += 1
            errors.append({"fact_id": fact.get("id"), "error": "scope_not_permitted"})
            continue

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
            rejected += 1
            errors.append({"fact_id": fact.get("id"), "error": "source_not_owned"})
            continue

        try:
            ingest_fact(fact, peer["node_id"])
            accepted += 1
        except Exception as exc:
            rejected += 1
            errors.append({"fact_id": fact.get("id"), "error": str(exc)})

    return {"accepted": accepted, "rejected": rejected, "errors": errors}


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
            f"SELECT * FROM federation_audit {where} ORDER BY ts DESC, id DESC LIMIT ?",
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
            f"""SELECT c.id, c.fact_a_id, c.fact_b_id, c.status, c.resolution_fact_id, c.detected_at
                FROM conflicts c {where}
                ORDER BY c.detected_at DESC, c.id DESC LIMIT ?""",
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="write permission required")

    with db() as conn:
        conflict = conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
        ).fetchone()

        if conflict is None:
            raise HTTPException(status_code=404, detail="conflict not found")
        if conflict["status"] == "resolved":
            raise HTTPException(status_code=409, detail="conflict already resolved")

        fact_a = conn.execute("SELECT * FROM facts WHERE id = ?", (conflict["fact_a_id"],)).fetchone()
        fact_b = conn.execute("SELECT * FROM facts WHERE id = ?", (conflict["fact_b_id"],)).fetchone()

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
        #    fact is federated to peers (spec §resolution-semantics, ISSUE-51).
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
