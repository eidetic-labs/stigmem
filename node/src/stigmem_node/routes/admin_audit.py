"""Admin audit log export — spec §22.3.

GET /v1/admin/audit   Paginated export of all audit event types across all
                      principals.  Gated by the ``audit.read`` capability.

Query parameters:
  since       RFC3339 timestamp — return events with ts >= since
  until       RFC3339 timestamp — return events with ts <= until
  principal   entity_uri filter
  event_type  filter to one event type (e.g. "quota_breach")
  cursor      opaque seq-based cursor for forward pagination
  limit       page size (1–1000, default 200)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..auth import Identity, resolve_identity
from ..db import db

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class AdminAuditEntry(BaseModel):
    seq: int | None
    id: str
    event_type: str
    entity_uri: str | None
    oidc_sub: str | None
    fact_id: str | None
    source: str
    attested_key_id: str | None
    ts: str
    tenant_id: str | None
    detail: str | None


class AdminAuditResponse(BaseModel):
    entries: list[AdminAuditEntry]
    total: int
    next_cursor: int | None


def _row_to_entry(row: Any) -> AdminAuditEntry:
    return AdminAuditEntry(
        seq=row["seq"],
        id=row["id"],
        event_type=row["event_type"],
        entity_uri=row["entity_uri"],
        oidc_sub=row["oidc_sub"],
        fact_id=row["fact_id"],
        source=row["source"],
        attested_key_id=row["attested_key_id"],
        ts=row["ts"],
        tenant_id=row["tenant_id"],
        detail=row["detail"],
    )


@router.get("/audit", response_model=AdminAuditResponse)
def admin_audit_export(
    identity: Annotated[Identity, Depends(resolve_identity)],
    since: str | None = Query(None, description="RFC3339 lower bound on ts (inclusive)"),
    until: str | None = Query(None, description="RFC3339 upper bound on ts (inclusive)"),
    principal: str | None = Query(None, description="Filter by entity_uri"),
    event_type: str | None = Query(None, description="Filter by event_type"),
    cursor: int | None = Query(
        None, description="Seq-based forward pagination cursor (exclusive lower bound)"
    ),
    limit: int = Query(200, ge=1, le=1000),
) -> AdminAuditResponse:
    """Export the full audit log.  Requires ``audit.read`` capability."""
    if not identity.can_audit():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="audit.read capability required",
        )

    params: list[Any] = []
    clauses: list[str] = []

    clauses.append("tenant_id = ?")
    params.append(identity.tenant_id)

    if since:
        clauses.append("ts >= ?")
        params.append(since)
    if until:
        clauses.append("ts <= ?")
        params.append(until)
    if principal:
        clauses.append("entity_uri = ?")
        params.append(principal)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if cursor is not None:
        clauses.append("(seq > ? OR seq IS NULL)")
        params.append(cursor)

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit + 1)

    sql = f"""
        SELECT seq, id, event_type, entity_uri, oidc_sub, fact_id, source,
               attested_key_id, ts, tenant_id, detail
        FROM fact_audit_log
        {where}
        ORDER BY seq ASC NULLS LAST, ts ASC, id ASC
        LIMIT ?
    """  # noqa: S608  # nosec B608

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor: int | None = None
    if has_more and rows:
        last_seq = rows[-1]["seq"]
        next_cursor = last_seq

    return AdminAuditResponse(
        entries=[_row_to_entry(r) for r in rows],
        total=len(rows),
        next_cursor=next_cursor,
    )
