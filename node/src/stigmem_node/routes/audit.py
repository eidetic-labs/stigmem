"""Track C / C3 — fact audit log surface.

Exposes the fact_audit_log table for end-to-end identity verification:
  principal (entity_uri, oidc_sub)
    → attested source (attested_key_id → agent_keys.entity_uri)
    → fact_id (facts.entity, relation, value, scope)

GET /v1/audit/facts/{fact_id}  — audit trail for a single fact (enriched join)
GET /v1/audit                  — paginated enriched audit log with optional filters
GET /v1/audit/export           — compliance CSV export (all join fields)
"""

from __future__ import annotations

import csv
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from ..auth import Identity, resolve_identity
from ..db import db
from ..models import AuditLogEntry, AuditLogResponse

router = APIRouter(prefix="/v1/audit", tags=["audit"])

# Full SELECT joining principal → attested key → fact in a single pass.
_JOIN_SELECT = """
    SELECT
        al.id,
        al.fact_id,
        al.event_type,
        al.entity_uri,
        al.oidc_sub,
        al.source,
        al.attested_key_id,
        al.ts,
        ak.entity_uri  AS attested_key_entity_uri,
        ak.description AS attested_key_description,
        f.entity       AS fact_entity,
        f.relation     AS fact_relation,
        f.value_type   AS fact_value_type,
        f.value_v      AS fact_value_v,
        f.scope        AS fact_scope
    FROM fact_audit_log al
    LEFT JOIN agent_keys ak ON al.attested_key_id = ak.id
    LEFT JOIN facts      f  ON al.fact_id = f.id
"""

_CSV_HEADERS = [
    "id", "fact_id", "event_type",
    "principal_entity_uri", "principal_oidc_sub",
    "source",
    "attested_key_id", "attested_key_entity_uri", "attested_key_description",
    "fact_entity", "fact_relation", "fact_value_type", "fact_value_v", "fact_scope",
    "ts",
]


def _row_to_entry(row: Any) -> AuditLogEntry:
    return AuditLogEntry(
        id=row["id"],
        fact_id=row["fact_id"],
        event_type=row["event_type"],
        entity_uri=row["entity_uri"],
        oidc_sub=row["oidc_sub"],
        source=row["source"],
        attested_key_id=row["attested_key_id"],
        ts=row["ts"],
        attested_key_entity_uri=row["attested_key_entity_uri"],
        attested_key_description=row["attested_key_description"],
        fact_entity=row["fact_entity"],
        fact_relation=row["fact_relation"],
        fact_value_type=row["fact_value_type"],
        fact_value_v=row["fact_value_v"],
        fact_scope=row["fact_scope"],
    )


def _encode_cursor(ts: str, entry_id: str) -> str:
    """Encode a keyset cursor as '{ts}|{id}' for DESC pagination."""
    return f"{ts}|{entry_id}"


def _decode_cursor(cursor: str) -> tuple[str, str] | None:
    """Return (ts, id) from a cursor string, or None if malformed."""
    parts = cursor.split("|", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def _build_where(
    entity_uri: str | None,
    oidc_sub: str | None,
    source: str | None,
    fact_id: str | None,
    attested: bool | None,
    cursor: str | None,
) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []

    if entity_uri:
        conditions.append("al.entity_uri = ?")
        params.append(entity_uri)
    if oidc_sub:
        conditions.append("al.oidc_sub = ?")
        params.append(oidc_sub)
    if source:
        conditions.append("al.source = ?")
        params.append(source)
    if fact_id:
        conditions.append("al.fact_id = ?")
        params.append(fact_id)
    if attested is True:
        conditions.append("al.attested_key_id IS NOT NULL")
    elif attested is False:
        conditions.append("al.attested_key_id IS NULL")
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            cur_ts, cur_id = decoded
            # Keyset pagination for ORDER BY ts DESC, id DESC
            conditions.append("(al.ts < ? OR (al.ts = ? AND al.id < ?))")
            params.extend([cur_ts, cur_ts, cur_id])

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


@router.get("/facts/{fact_id}", response_model=list[AuditLogEntry])
def get_fact_audit(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[AuditLogEntry]:
    """Return the complete enriched audit trail for a specific fact."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    with db() as conn:
        rows = conn.execute(
            _JOIN_SELECT + " WHERE al.fact_id = ? ORDER BY al.ts ASC",
            (fact_id,),
        ).fetchall()

    if not rows:
        with db() as conn:
            exists = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fact not found")

    return [_row_to_entry(r) for r in rows]


@router.get("/export")
def export_audit_csv(
    identity: Annotated[Identity, Depends(resolve_identity)],
    entity_uri: str | None = Query(None, description="Filter by asserting entity"),
    oidc_sub: str | None = Query(None, description="Filter by OIDC subject"),
    source: str | None = Query(None, description="Filter by fact source"),
    fact_id: str | None = Query(None, description="Filter by fact ID"),
    attested: bool | None = Query(None, description="true = attested only; false = unattested only"),
    limit: int = Query(5000, ge=1, le=50000),
) -> StreamingResponse:
    """Export the enriched audit log as CSV for compliance (principal → key → fact)."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    where, params = _build_where(entity_uri, oidc_sub, source, fact_id, attested, None)
    params.append(limit)
    sql = _JOIN_SELECT + where + " ORDER BY al.ts ASC LIMIT ?"

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_HEADERS)
    for r in rows:
        writer.writerow([
            r["id"], r["fact_id"], r["event_type"],
            r["entity_uri"] or "", r["oidc_sub"] or "",
            r["source"],
            r["attested_key_id"] or "",
            r["attested_key_entity_uri"] or "",
            r["attested_key_description"] or "",
            r["fact_entity"] or "",
            r["fact_relation"] or "",
            r["fact_value_type"] or "",
            r["fact_value_v"] or "",
            r["fact_scope"] or "",
            r["ts"],
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stigmem-audit.csv"},
    )


@router.get("", response_model=AuditLogResponse)
def query_audit(
    identity: Annotated[Identity, Depends(resolve_identity)],
    entity_uri: str | None = Query(None, description="Filter by asserting entity"),
    oidc_sub: str | None = Query(None, description="Filter by OIDC subject"),
    source: str | None = Query(None, description="Filter by fact source"),
    fact_id: str | None = Query(None, description="Filter by fact ID"),
    attested: bool | None = Query(None, description="true = attested only; false = unattested only"),
    cursor: str | None = Query(None, description="Opaque pagination cursor (audit entry id)"),
    limit: int = Query(50, ge=1, le=500),
) -> AuditLogResponse:
    """Query the enriched fact audit log (principal → attested-source → fact) with optional filters."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    where, params = _build_where(entity_uri, oidc_sub, source, fact_id, attested, cursor)
    params.append(limit + 1)
    sql = _JOIN_SELECT + where + " ORDER BY al.ts DESC, al.id DESC LIMIT ?"

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = _encode_cursor(rows[-1]["ts"], rows[-1]["id"]) if has_more and rows else None

    return AuditLogResponse(
        entries=[_row_to_entry(r) for r in rows],
        total=len(rows),
        cursor=next_cursor,
    )
