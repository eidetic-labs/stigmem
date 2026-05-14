"""Quarantine admin API — spec §19.5.

GET  /v1/quarantine             — list quarantined facts (all or by garden)
POST /v1/quarantine/{fact_id}/admit  — shorthand: promote fact to main fabric
POST /v1/quarantine/{fact_id}/reject — shorthand: reject a quarantined fact

These endpoints are convenience wrappers over the garden-level promote/reject
endpoints (POST /v1/gardens/:id/promote|reject).  They operate node-globally:
the caller addresses a fact by ID without needing to know its quarantine garden.
Requires node admin (write) permission.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..garden_acl import get_garden_by_slug_or_id, require_quarantine_moderator_or_admin
from ..models import (
    QUARANTINE_PENDING,
    QuarantineListResponse,
    QuarantineRecord,
)

router = APIRouter(prefix="/v1/quarantine", tags=["quarantine"])


def _require_write(identity: Identity) -> None:
    if not identity.can_write():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="write permission required"
        )


# ---------------------------------------------------------------------------
# List quarantined facts
# ---------------------------------------------------------------------------


@router.get("", response_model=QuarantineListResponse)
def list_quarantined_facts(
    identity: Annotated[Identity, Depends(resolve_identity)],
    garden_id: str | None = Query(None, description="Filter by quarantine garden UUID or slug"),
    quarantine_status: str | None = Query(
        None, description="Filter by status: pending, promoted, rejected"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> QuarantineListResponse:
    """List facts in the quarantine system (Spec-08-Quarantine-Garden).

    Node admins see all quarantined facts across all gardens.
    Other callers see facts only in quarantine gardens where they hold a member role.
    """
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="read permission required"
        )

    filters: list[str] = ["f.quarantine_garden_id IS NOT NULL"]
    params: list[Any] = []

    if quarantine_status:
        filters.append("f.quarantine_status = ?")
        params.append(quarantine_status)
    else:
        filters.append("f.quarantine_status IS NOT NULL")

    if garden_id:
        # Resolve slug to UUID
        garden = get_garden_by_slug_or_id(garden_id, tenant_id=identity.tenant_id)
        if garden is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")
        filters.append("f.quarantine_garden_id = ?")
        params.append(garden["id"])
    elif not identity.can_write():
        # Non-admins: only see facts in gardens they're members of
        filters.append(
            "f.quarantine_garden_id IN ("
            "  SELECT gm.garden_id FROM garden_members gm"
            "  WHERE gm.entity_uri = ?"
            ")"
        )
        params.append(identity.entity_uri)

    where_clause = " AND ".join(filters)

    with db() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM facts f WHERE {where_clause}",  # nosec B608
            params,
        ).fetchone()
        total: int = count_row[0] if count_row else 0

        rows = conn.execute(
            f"""SELECT f.id, f.entity, f.relation, f.source,
                       f.quarantine_status, f.quarantine_garden_id, f.quarantine_reason,
                       f.quarantine_acted_by, f.quarantine_acted_at,
                       f.source_trust, f.received_from, f.timestamp
                FROM facts f
                WHERE {where_clause}
                ORDER BY f.timestamp DESC
                LIMIT ? OFFSET ?""",  # nosec B608
            [*params, limit, offset],
        ).fetchall()

    items = [
        QuarantineRecord(
            fact_id=r["id"],
            entity=r["entity"],
            relation=r["relation"],
            source=r["source"],
            quarantine_status=r["quarantine_status"] or "",
            quarantine_garden_id=r["quarantine_garden_id"],
            quarantine_reason=r["quarantine_reason"],
            quarantine_acted_by=r["quarantine_acted_by"],
            quarantine_acted_at=r["quarantine_acted_at"],
            source_trust=float(r["source_trust"]) if r["source_trust"] is not None else None,
            received_from=r["received_from"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]

    return QuarantineListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# Admit (promote) a fact from quarantine to the main fabric
# ---------------------------------------------------------------------------


@router.post("/{fact_id}/admit", status_code=status.HTTP_200_OK)
def admit_fact(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
    target_garden_id: str | None = Query(None, description="Target garden UUID or slug"),
    reason: str = Query("", description="Reason for admission"),
) -> dict[str, Any]:
    """Promote a quarantined fact to the main fabric (or a specific target garden).

    Requires quarantine:moderator or admin role in the fact's quarantine garden.
    """
    _require_write(identity)

    _get_quarantined_fact(fact_id, identity)
    now = datetime.now(UTC).isoformat()

    # Resolve target garden
    target_db_id: str | None = None
    if target_garden_id:
        tg = get_garden_by_slug_or_id(target_garden_id, tenant_id=identity.tenant_id)
        if tg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="target garden not found"
            )
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
            (target_db_id, identity.entity_uri, now, reason or "admitted via admin API", fact_id),
        )
        _write_quarantine_audit(conn, fact_id, "quarantine_promote", identity, now)

    return {
        "fact_id": fact_id,
        "action": "admitted",
        "target_garden_id": target_db_id,
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }


# ---------------------------------------------------------------------------
# Reject a quarantined fact
# ---------------------------------------------------------------------------


@router.post("/{fact_id}/reject", status_code=status.HTTP_200_OK)
def reject_fact(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
    reason: str = Query("", description="Reason for rejection"),
) -> dict[str, Any]:
    """Permanently reject a quarantined fact.

    Sets confidence = 0.0 and quarantine_status = 'rejected'.
    Requires quarantine:moderator or admin role in the fact's quarantine garden.
    """
    _require_write(identity)

    _get_quarantined_fact(fact_id, identity)
    now = datetime.now(UTC).isoformat()

    with db() as conn:
        conn.execute(
            """UPDATE facts
               SET confidence = 0.0,
                   quarantine_status = 'rejected',
                   quarantine_acted_by = ?,
                   quarantine_acted_at = ?,
                   quarantine_reason = ?
               WHERE id = ?""",
            (identity.entity_uri, now, reason or "rejected via admin API", fact_id),
        )
        # Append-only retraction log (§24.2.1 c.3)
        conn.execute(
            "INSERT INTO fact_retractions"
            " (id, fact_id, retracted_at, retracted_by) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), fact_id, now, identity.entity_uri),
        )
        _write_quarantine_audit(conn, fact_id, "quarantine_reject", identity, now)

    return {
        "fact_id": fact_id,
        "action": "rejected",
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_quarantined_fact(
    fact_id: str, identity: Identity
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (fact_row, garden_row) for a pending quarantined fact.

    Raises 404 or 409 as appropriate.  Checks moderator access.
    """
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM facts WHERE id = ? AND quarantine_garden_id IS NOT NULL",
            (fact_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="quarantined fact not found"
        )

    if row["quarantine_status"] != QUARANTINE_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="fact_not_quarantine_pending",
        )

    garden = get_garden_by_slug_or_id(row["quarantine_garden_id"])
    if garden is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="quarantine garden not found"
        )

    if not identity.can_write():
        require_quarantine_moderator_or_admin(garden, identity)

    return dict(row), garden


def _write_quarantine_audit(
    conn: Any, fact_id: str, event_type: str, identity: Identity, now: str
) -> None:
    audit_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO fact_audit_log"
        " (id, fact_id, event_type, entity_uri, oidc_sub, source,"
        "  attested_key_id, ts)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (
            audit_id,
            fact_id,
            event_type,
            identity.entity_uri,
            identity.oidc_sub,
            identity.entity_uri,
            None,
            now,
        ),
    )
