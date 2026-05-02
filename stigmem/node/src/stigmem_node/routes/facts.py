"""Fact assertion and query routes — spec §5.1 and §5.2."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..models import (
    VALID_SCOPES,
    AssertRequest,
    FactRecord,
    QueryResponse,
    row_to_record,
)

router = APIRouter(prefix="/v1/facts", tags=["facts"])


@router.post("", response_model=FactRecord, status_code=status.HTTP_201_CREATED)
def assert_fact(
    req: AssertRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Assert a fact into the fabric (spec §5.1)."""
    if not identity.can_write():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="write permission required")

    fact_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    value_v = _encode_v(req.value.type, req.value.v)

    with db() as conn:
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp, valid_until, confidence, scope)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                fact_id,
                req.entity,
                req.relation,
                req.value.type,
                value_v,
                req.source,
                now,
                req.valid_until,
                req.confidence,
                req.scope,
            ),
        )
        row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
        sibling_count = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE entity=? AND relation=? AND scope=?",
            (req.entity, req.relation, req.scope),
        ).fetchone()[0]

    return row_to_record(row, contradicted=sibling_count > 1)


@router.get("", response_model=QueryResponse)
def query_facts(
    identity: Annotated[Identity, Depends(resolve_identity)],
    entity: str | None = Query(None),
    relation: str | None = Query(None),
    source: str | None = Query(None),
    scope: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_contradicted: bool = Query(False),
    include_expired: bool = Query(False),
    after: str | None = Query(None, description="Return facts with timestamp > this ISO 8601 value"),
    cursor: str | None = Query(None, description="Opaque pagination cursor (fact id)"),
    limit: int = Query(50, ge=1, le=500),
) -> QueryResponse:
    """Query facts by pattern (spec §5.2). Omitted fields are wildcards."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    conditions: list[str] = ["confidence >= ?"]
    params: list[Any] = [min_confidence]

    if entity:
        conditions.append("entity = ?")
        params.append(entity)
    if relation:
        conditions.append("relation = ?")
        params.append(relation)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if scope:
        if scope not in VALID_SCOPES:
            raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")
        conditions.append("scope = ?")
        params.append(scope)
    if after:
        conditions.append("timestamp > ?")
        params.append(after)
    if cursor:
        conditions.append("id > ?")
        params.append(cursor)

    # Enforce valid_until: filter expired facts unless caller opts in
    if not include_expired:
        now = datetime.now(UTC).isoformat()
        conditions.append("(valid_until IS NULL OR valid_until > ?)")
        params.append(now)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM facts WHERE {where} ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    # Per-group contradiction detection
    seen: dict[tuple[str, str, str], int] = {}
    for r in rows:
        key = (r["entity"], r["relation"], r["scope"])
        seen[key] = seen.get(key, 0) + 1

    records = [
        row_to_record(r, contradicted=seen[(r["entity"], r["relation"], r["scope"])] > 1)
        for r in rows
    ]

    next_cursor = rows[-1]["id"] if has_more and rows else None
    return QueryResponse(facts=records, total=len(records), cursor=next_cursor)


@router.get("/{fact_id}", response_model=FactRecord)
def get_fact(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Retrieve a single fact by ID (spec v0.4 §5.5)."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")
    with db() as conn:
        row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")
    sibling_count: int = 0
    with db() as conn:
        sibling_count = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE entity=? AND relation=? AND scope=?",
            (row["entity"], row["relation"], row["scope"]),
        ).fetchone()[0]
    return row_to_record(row, contradicted=sibling_count > 1)


def _encode_v(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)
