"""Intent Envelope route — spec §4, §5.14 (v0.8).

POST /v1/intents
  Accept a structured IntentEnvelope, validate it, decompose it into atomic
  facts in the fabric, and return a receipt with the generated intent ID and
  all written fact IDs.

GET /v1/intents/:intent_id
  Reconstruct and return the envelope by querying its reified facts.

Fact reification schema (all facts share the same intent_id entity, except
sub-entities for constraints/preferences/deferences/artifacts):

  (intent_id, "intent:from",           ref,    from_uri, scope)
  (intent_id, "intent:goal",           text,   from_uri, scope)
  (intent_id, "intent:to",             ref,    from_uri, scope)  — one per target
  (intent_id, "intent:escalation",     string, from_uri, scope)  — priority
  (intent_id, "intent:escalate_to",    ref,    from_uri, scope)
  (intent_id, "intent:escalation:channel",  string, ...)
  (intent_id, "intent:escalation:context",  string "true"|"false", ...)
  (intent_id, "intent:handoff_to",     ref,    from_uri, scope)  — to[0] when handoff present
  (intent_id, "intent:handoff_summary",text,   from_uri, scope)
  (intent_id, "intent:context_ref",    ref,    from_uri, scope)  — one per fact_ref
  (intent_id, "intent:continuation",   text,   from_uri, scope)
  (intent_id, "intent:constraint",     ref,    from_uri, scope)  — one per constraint sub-entity
  (intent_id, "intent:preference",     ref,    from_uri, scope)  — one per preference sub-entity
  (intent_id, "intent:deference",      ref,    from_uri, scope)  — one per deference sub-entity
  (intent_id, "intent:artifact",       ref,    from_uri, scope)  — one per artifact sub-entity

Sub-entities use the pattern "{intent_id}:{kind}:{index}" for stable referencing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..entity_normalizer import NormalizationError, normalize_entity_uri
from ..hlc import node_hlc
from ..models import (
    Constraint,
    DeferenceRule,
    EscalationPolicy,
    FactValue,
    HandoffArtifact,
    HandoffPayload,
    IntentEnvelopeRecord,
    IntentEnvelopeRequest,
    Preference,
    VALID_SCOPES,
)

router = APIRouter(prefix="/v1/intents", tags=["intents"])

# Relations that identify a fact row as the root of an IntentEnvelope.
_ROOT_RELATION = "intent:goal"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_v(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)


def _insert(
    conn: Any,
    entity: str,
    relation: str,
    vtype: str,
    vraw: Any,
    source: str,
    scope: str,
    valid_until: str | None,
    now: str,
) -> str:
    fact_id = str(uuid.uuid4())
    hlc = node_hlc.tick()
    conn.execute(
        """INSERT INTO facts
           (id, entity, relation, value_type, value_v, source, timestamp,
            valid_until, confidence, scope, hlc, received_from)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            fact_id, entity, relation,
            vtype, _encode_v(vtype, vraw),
            source, now, valid_until, 1.0, scope, hlc, None,
        ),
    )
    return fact_id


def _decompose(
    conn: Any,
    intent_id: str,
    req: IntentEnvelopeRequest,
    now: str,
) -> list[str]:
    """Write all atomic facts for an IntentEnvelope; return list of fact IDs."""
    src = req.from_uri
    scope = req.scope
    exp = req.expires_at
    ids: list[str] = []

    def ins(entity: str, relation: str, vtype: str, vraw: Any) -> None:
        ids.append(_insert(conn, entity, relation, vtype, vraw, src, scope, exp, now))

    # Core facts on intent_id
    ins(intent_id, "intent:from",  "ref",  req.from_uri)
    ins(intent_id, "intent:goal",  "text", req.goal)
    for to_uri in req.to:
        ins(intent_id, "intent:to", "ref", to_uri)

    # Escalation
    if req.escalation:
        esc = req.escalation
        ins(intent_id, "intent:escalation",          "string", esc.priority)
        ins(intent_id, "intent:escalate_to",         "ref",    esc.escalate_to)
        ins(intent_id, "intent:escalation:channel",  "string", esc.channel)
        ins(intent_id, "intent:escalation:context",  "string", "true" if esc.include_context else "false")

    # Handoff
    if req.handoff:
        h = req.handoff
        # Emit intent:handoff_to pointing at first `to` for adapter compat
        if req.to:
            ins(intent_id, "intent:handoff_to", "ref", req.to[0])
        ins(intent_id, "intent:handoff_summary", "text", h.summary)
        for ref_uri in h.fact_refs:
            ins(intent_id, "intent:context_ref", "ref", ref_uri)
        if h.continuation:
            ins(intent_id, "intent:continuation", "text", h.continuation)
        for i, artifact in enumerate(h.artifacts):
            art_id = f"{intent_id}:artifact:{i}"
            ins(art_id, "intent:artifact:name", "string", artifact.name)
            ins(art_id, "intent:artifact:ref",  "ref",    artifact.ref)
            ins(intent_id, "intent:artifact",   "ref",    art_id)

    # Constraints
    for i, c in enumerate(req.constraint):
        sub = f"{intent_id}:constraint:{i}"
        ins(sub, "intent:constraint:kind",  "string", c.kind)
        ins(sub, "intent:constraint:limit", c.limit.type, c.limit.v)
        if c.unit is not None:
            ins(sub, "intent:constraint:unit", "string", c.unit)
        ins(intent_id, "intent:constraint", "ref", sub)

    # Preferences
    for i, p in enumerate(req.preference):
        sub = f"{intent_id}:preference:{i}"
        ins(sub, "intent:preference:kind",   "string", p.kind)
        ins(sub, "intent:preference:value",  p.value.type, p.value.v)
        ins(sub, "intent:preference:weight", "number", p.weight)
        ins(intent_id, "intent:preference",  "ref", sub)

    # Deferences
    for i, d in enumerate(req.deference):
        sub = f"{intent_id}:deference:{i}"
        ins(sub, "intent:deference:condition", "text",   d.condition)
        ins(sub, "intent:deference:defer_to",  "ref",    d.defer_to)
        if d.timeout_s is not None:
            ins(sub, "intent:deference:timeout_s", "number", d.timeout_s)
        ins(intent_id, "intent:deference", "ref", sub)

    return ids


def _reconstruct(intent_id: str, rows_by_entity: dict[str, list[Any]]) -> IntentEnvelopeRecord | None:
    """Rebuild an IntentEnvelopeRecord from raw DB rows grouped by entity."""
    root = rows_by_entity.get(intent_id, [])
    if not root:
        return None

    by_rel: dict[str, list[str]] = {}
    created_at: str | None = None
    expires_at: str | None = None

    for row in root:
        rel = row["relation"]
        val = row["value_v"]
        by_rel.setdefault(rel, []).append(val)
        if created_at is None or row["timestamp"] < created_at:
            created_at = row["timestamp"]
        if row["valid_until"] is not None:
            expires_at = row["valid_until"]

    if _ROOT_RELATION not in by_rel:
        return None

    goal = by_rel[_ROOT_RELATION][0]
    from_uri = (by_rel.get("intent:from") or [""])[0]
    to = by_rel.get("intent:to", [])
    scope = rows_by_entity[intent_id][0]["scope"]

    # Escalation
    escalation: EscalationPolicy | None = None
    if "intent:escalation" in by_rel:
        escalation = EscalationPolicy(
            escalate_to=(by_rel.get("intent:escalate_to") or [""])[0],
            channel=(by_rel.get("intent:escalation:channel") or ["stigmem"])[0],
            priority=by_rel["intent:escalation"][0],
            include_context=(by_rel.get("intent:escalation:context") or ["true"])[0] == "true",
        )

    # Handoff
    handoff: HandoffPayload | None = None
    if "intent:handoff_summary" in by_rel:
        artifact_refs = by_rel.get("intent:artifact", [])
        artifacts: list[HandoffArtifact] = []
        for art_id in artifact_refs:
            art_rows = rows_by_entity.get(art_id, [])
            art_by_rel = {r["relation"]: r["value_v"] for r in art_rows}
            artifacts.append(HandoffArtifact(
                name=art_by_rel.get("intent:artifact:name", ""),
                ref=art_by_rel.get("intent:artifact:ref", ""),
            ))
        _cont = by_rel.get("intent:continuation")
        handoff = HandoffPayload(
            summary=by_rel["intent:handoff_summary"][0],
            fact_refs=by_rel.get("intent:context_ref", []),
            continuation=_cont[0] if _cont else None,
            artifacts=artifacts,
        )

    # Constraints
    constraints: list[Constraint] = []
    for sub_id in by_rel.get("intent:constraint", []):
        sub_rows = rows_by_entity.get(sub_id, [])
        sub_rel = {r["relation"]: r for r in sub_rows}
        kind_row = sub_rel.get("intent:constraint:kind")
        limit_row = sub_rel.get("intent:constraint:limit")
        unit_row = sub_rel.get("intent:constraint:unit")
        if kind_row and limit_row:
            constraints.append(Constraint(
                kind=kind_row["value_v"],
                limit=FactValue(type=limit_row["value_type"], v=limit_row["value_v"]),
                unit=unit_row["value_v"] if unit_row else None,
            ))

    # Preferences
    preferences: list[Preference] = []
    for sub_id in by_rel.get("intent:preference", []):
        sub_rows = rows_by_entity.get(sub_id, [])
        sub_rel = {r["relation"]: r for r in sub_rows}
        kind_row = sub_rel.get("intent:preference:kind")
        val_row = sub_rel.get("intent:preference:value")
        wt_row = sub_rel.get("intent:preference:weight")
        if kind_row and val_row:
            preferences.append(Preference(
                kind=kind_row["value_v"],
                value=FactValue(type=val_row["value_type"], v=val_row["value_v"]),
                weight=float(wt_row["value_v"]) if wt_row else 1.0,
            ))

    # Deferences
    deferences: list[DeferenceRule] = []
    for sub_id in by_rel.get("intent:deference", []):
        sub_rows = rows_by_entity.get(sub_id, [])
        sub_rel = {r["relation"]: r for r in sub_rows}
        cond_row = sub_rel.get("intent:deference:condition")
        defer_row = sub_rel.get("intent:deference:defer_to")
        timeout_row = sub_rel.get("intent:deference:timeout_s")
        if cond_row and defer_row:
            deferences.append(DeferenceRule(
                condition=cond_row["value_v"],
                defer_to=defer_row["value_v"],
                timeout_s=int(float(timeout_row["value_v"])) if timeout_row else None,
            ))

    return IntentEnvelopeRecord(
        id=intent_id,
        **{"from": from_uri},
        to=to,
        goal=goal,
        scope=scope,
        created_at=created_at or datetime.now(UTC).isoformat(),
        expires_at=expires_at,
        constraint=constraints,
        preference=preferences,
        deference=deferences,
        escalation=escalation,
        handoff=handoff,
        fact_ids=[],  # not returned on GET; fact_ids are a POST-only receipt
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=IntentEnvelopeRecord,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def submit_intent(
    req: IntentEnvelopeRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> IntentEnvelopeRecord:
    """Submit an IntentEnvelope (spec §5.14).

    Validates the envelope, normalizes URIs, decomposes it into atomic facts,
    and returns a receipt with the generated intent ID and all written fact IDs.
    Idempotent when the caller supplies a stable ``id``: if that intent_id already
    has a ``intent:goal`` fact in the fabric, returns 409 Conflict.
    """
    if not identity.can_write():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="write permission required")

    # Normalize URIs
    try:
        from_uri = normalize_entity_uri(req.from_uri)
    except NormalizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid_entity_uri: from — {exc}",
        ) from exc

    normalized_to: list[str] = []
    for i, t in enumerate(req.to):
        try:
            normalized_to.append(normalize_entity_uri(t))
        except NormalizationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid_entity_uri: to[{i}] — {exc}",
            ) from exc

    # Resolve intent_id
    intent_id = req.id if req.id else f"intent:{uuid.uuid4()}"

    now = datetime.now(UTC).isoformat()

    with db() as conn:
        # Idempotency check: reject if intent_id already exists
        existing = conn.execute(
            "SELECT id FROM facts WHERE entity=? AND relation=? LIMIT 1",
            (intent_id, _ROOT_RELATION),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"intent {intent_id!r} already exists; supply a new id or omit for auto-generation",
            )

        # Build a normalised copy for decomposition
        normalised_req = req.model_copy(update={"from_uri": from_uri, "to": normalized_to})
        fact_ids = _decompose(conn, intent_id, normalised_req, now)

    return IntentEnvelopeRecord(
        id=intent_id,
        **{"from": from_uri},
        to=normalized_to,
        goal=req.goal,
        scope=req.scope,
        created_at=now,
        expires_at=req.expires_at,
        constraint=req.constraint,
        preference=req.preference,
        deference=req.deference,
        escalation=req.escalation,
        handoff=req.handoff,
        fact_ids=fact_ids,
    )


@router.get(
    "/{intent_id:path}",
    response_model=IntentEnvelopeRecord,
    response_model_by_alias=True,
)
def get_intent(
    intent_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> IntentEnvelopeRecord:
    """Retrieve an IntentEnvelope by ID, reconstructed from its reified facts (spec §5.14)."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    now = datetime.now(UTC).isoformat()
    prefix = f"{intent_id}:%"

    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM facts
               WHERE (entity = ? OR entity LIKE ?)
                 AND confidence > 0.0
                 AND (valid_until IS NULL OR valid_until > ?)
               ORDER BY entity, relation""",
            (intent_id, prefix, now),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="intent not found")

    rows_by_entity: dict[str, list[Any]] = {}
    for row in rows:
        rows_by_entity.setdefault(row["entity"], []).append(row)

    record = _reconstruct(intent_id, rows_by_entity)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="intent not found")

    return record
