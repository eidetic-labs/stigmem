"""Garden CRUD + membership routes — spec §5.14–§5.18, §17."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import Identity, resolve_identity
from ..billing import BillingEvent, get_hook_bus
from ..db import db
from ..garden_acl import (
    get_garden_by_slug_or_id,
    get_member_role,
    is_node_admin,
    quarantine_garden_has_pending_facts,
    require_garden_admin,
    require_garden_read,
    require_quarantine_moderator_or_admin,
)
from ..models import (
    VALID_SCOPES,
    GardenCreateRequest,
    GardenMemberRecord,
    GardenMemberRequest,
    GardenMemberUpdateRequest,
    GardenRecord,
    QuarantinePromoteRequest,
    QuarantineRejectRequest,
)
from ..settings import settings

router = APIRouter(prefix="/v1/gardens", tags=["gardens"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")


def _build_garden_id_uri(slug: str) -> str:
    """Construct the canonical garden_id URI from a slug."""
    from urllib.parse import urlparse
    parsed = urlparse(settings.node_url)
    authority = parsed.netloc or parsed.path
    return f"stigmem://{authority}/garden/{slug}"


def _members_for_garden(garden_uuid: str) -> list[GardenMemberRecord]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM garden_members WHERE garden_id = ? ORDER BY added_at",
            (garden_uuid,),
        ).fetchall()
    return [
        GardenMemberRecord(
            entity_uri=r["entity_uri"],
            role=r["role"],
            added_by=r["added_by"],
            added_at=r["added_at"],
        )
        for r in rows
    ]


def _row_to_garden_record(row: dict[str, Any], include_members: bool = True) -> GardenRecord:
    members = _members_for_garden(row["id"]) if include_members else []
    return GardenRecord(
        id=row["id"],
        garden_id=_build_garden_id_uri(row["slug"]),
        slug=row["slug"],
        name=row["name"],
        scope=row["scope"],
        description=row.get("description"),
        created_by=row["created_by"],
        created_at=row["created_at"],
        members=members,
        quarantine=bool(row.get("quarantine", 0)),
    )


@router.post("", response_model=GardenRecord, status_code=status.HTTP_201_CREATED)
def create_garden(
    req: GardenCreateRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenRecord:
    """Create a new garden (spec §5.14). Creator is auto-added as admin."""
    if not identity.can_write():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="write permission required"
        )

    slug = req.slug.lower().strip()
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="slug must match ^[a-z0-9][a-z0-9\\-]{0,62}$",
        )
    if req.scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"scope must be one of {VALID_SCOPES}",
        )

    garden_uuid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM gardens WHERE slug = ? AND tenant_id = ?",
            (slug, identity.tenant_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")

        conn.execute(
            """INSERT INTO gardens
                 (id, slug, name, scope, description, created_by, created_at,
                  tenant_id, quarantine)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                garden_uuid,
                slug,
                req.name,
                req.scope,
                req.description,
                identity.entity_uri,
                now,
                identity.tenant_id,
                int(req.quarantine),
            ),
        )
        conn.execute(
            """INSERT INTO garden_members (garden_id, entity_uri, role, added_by, added_at)
               VALUES (?,?,?,?,?)""",
            (garden_uuid, identity.entity_uri, "admin", identity.entity_uri, now),
        )
        row = conn.execute("SELECT * FROM gardens WHERE id = ?", (garden_uuid,)).fetchone()

    get_hook_bus().emit(BillingEvent(
        event_type="garden_created",
        tenant_id=identity.tenant_id,
        entity_uri=identity.entity_uri,
        garden_id=_build_garden_id_uri(slug),
    ))

    return _row_to_garden_record(dict(row))


@router.get("", response_model=list[GardenRecord])
def list_gardens(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[GardenRecord]:
    """List accessible gardens (spec §5.15). Node admins see all; others see only their gardens."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="read permission required"
        )

    with db() as conn:
        if is_node_admin(identity):
            rows = conn.execute(
                "SELECT * FROM gardens WHERE tenant_id = ? ORDER BY created_at",
                (identity.tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT g.* FROM gardens g
                   JOIN garden_members m ON g.id = m.garden_id
                   WHERE m.entity_uri = ? AND g.tenant_id = ?
                   ORDER BY g.created_at""",
                (identity.entity_uri, identity.tenant_id),
            ).fetchall()

    return [_row_to_garden_record(dict(r), include_members=False) for r in rows]


@router.get("/{garden_slug_or_id}", response_model=GardenRecord)
def get_garden(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenRecord:
    """Get a garden by slug or UUID (spec §5.16)."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="read permission required"
        )

    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    if not is_node_admin(identity):
        require_garden_read(garden, identity)

    return _row_to_garden_record(garden)


@router.delete("/{garden_slug_or_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_garden(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    """Delete a garden (spec §5.17). Requires garden admin role. Facts are orphaned, not deleted.

    Quarantine gardens with pending facts cannot be deleted (§19.5.2 — HTTP 409).
    """
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    # Guard: quarantine garden cannot be deleted while it has pending facts (§19.5.2)
    if garden.get("quarantine") and quarantine_garden_has_pending_facts(garden["id"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="quarantine_has_pending_facts",
        )

    with db() as conn:
        conn.execute("DELETE FROM gardens WHERE id = ?", (garden["id"],))


# ---------------------------------------------------------------------------
# Membership routes (spec §5.18)
# ---------------------------------------------------------------------------

@router.get("/{garden_slug_or_id}/members", response_model=list[GardenMemberRecord])
def list_members(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[GardenMemberRecord]:
    """List members of a garden (spec §5.18). Requires any member role."""
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")
    require_garden_read(garden, identity)
    return _members_for_garden(garden["id"])


@router.post(
    "/{garden_slug_or_id}/members",
    response_model=GardenMemberRecord,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    garden_slug_or_id: str,
    req: GardenMemberRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenMemberRecord:
    """Add a member to a garden (spec §5.18). Requires admin role."""
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    existing_role = get_member_role(garden["id"], req.entity_uri)
    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"entity is already a member with role '{existing_role}'; "
                "use PATCH to change role"
            ),
        )

    now = datetime.now(UTC).isoformat()
    with db() as conn:
        conn.execute(
            """INSERT INTO garden_members (garden_id, entity_uri, role, added_by, added_at)
               VALUES (?,?,?,?,?)""",
            (garden["id"], req.entity_uri, req.role, identity.entity_uri, now),
        )

    return GardenMemberRecord(
        entity_uri=req.entity_uri,
        role=req.role,
        added_by=identity.entity_uri,
        added_at=now,
    )


@router.patch("/{garden_slug_or_id}/members/{entity_uri:path}", response_model=GardenMemberRecord)
def update_member_role(
    garden_slug_or_id: str,
    entity_uri: str,
    req: GardenMemberUpdateRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenMemberRecord:
    """Change a member's role (spec §5.18). Requires admin. Cannot demote last admin."""
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    existing_role = get_member_role(garden["id"], entity_uri)
    if existing_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    if existing_role == "admin" and req.role != "admin":
        _guard_last_admin(garden["id"], entity_uri)

    with db() as conn:
        conn.execute(
            "UPDATE garden_members SET role = ? WHERE garden_id = ? AND entity_uri = ?",
            (req.role, garden["id"], entity_uri),
        )
        row = conn.execute(
            "SELECT * FROM garden_members WHERE garden_id = ? AND entity_uri = ?",
            (garden["id"], entity_uri),
        ).fetchone()

    return GardenMemberRecord(
        entity_uri=row["entity_uri"],
        role=row["role"],
        added_by=row["added_by"],
        added_at=row["added_at"],
    )


@router.delete(
    "/{garden_slug_or_id}/members/{entity_uri:path}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    garden_slug_or_id: str,
    entity_uri: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    """Remove a member from a garden (spec §5.18). Cannot remove last admin."""
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    existing_role = get_member_role(garden["id"], entity_uri)
    if existing_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    if existing_role == "admin":
        _guard_last_admin(garden["id"], entity_uri)

    with db() as conn:
        conn.execute(
            "DELETE FROM garden_members WHERE garden_id = ? AND entity_uri = ?",
            (garden["id"], entity_uri),
        )


def _guard_last_admin(garden_uuid: str, entity_uri: str) -> None:
    """Raise 403 if removing/demoting entity_uri would leave the garden with no admins."""
    with db() as conn:
        admin_count: int = conn.execute(
            "SELECT COUNT(*) FROM garden_members WHERE garden_id = ? AND role = 'admin'",
            (garden_uuid,),
        ).fetchone()[0]
    if admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot remove or demote the last admin; promote another member first",
        )


def _guard_last_elevated_role(garden_uuid: str, entity_uri: str) -> None:
    """For quarantine gardens: raise 409 if removal would leave no admin or moderator (§19.5.3)."""
    with db() as conn:
        elevated_count: int = conn.execute(
            """SELECT COUNT(*) FROM garden_members
               WHERE garden_id = ? AND role IN ('admin', 'quarantine:moderator')""",
            (garden_uuid,),
        ).fetchone()[0]
    if elevated_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="quarantine garden must retain at least one admin or quarantine:moderator",
        )


# ---------------------------------------------------------------------------
# Quarantine promote / reject (spec §5.25, §19.5.5)
# ---------------------------------------------------------------------------

@router.post("/{garden_slug_or_id}/promote", status_code=status.HTTP_200_OK)
def promote_fact(
    garden_slug_or_id: str,
    req: QuarantinePromoteRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Promote a quarantined fact to a target garden (spec §5.25, §19.5.5).

    Requires quarantine:moderator or admin role.
    """
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    if not garden.get("quarantine"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="this endpoint is only valid for quarantine gardens",
        )

    require_quarantine_moderator_or_admin(garden, identity)

    now = datetime.now(UTC).isoformat()

    with db() as conn:
        fact_row = conn.execute(
            "SELECT id, quarantine_status, quarantine_garden_id FROM facts WHERE id = ?",
            (req.fact_id,),
        ).fetchone()

        if fact_row is None or fact_row["quarantine_garden_id"] != garden["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="fact not found in quarantine garden",
            )

        if fact_row["quarantine_status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="fact_not_quarantine_pending",
            )

        # Resolve target garden UUID if provided as slug
        target_garden_db_id: str | None = None
        if req.target_garden_id:
            tg = get_garden_by_slug_or_id(req.target_garden_id, tenant_id=identity.tenant_id)
            if tg is None:
                raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="target garden not found",
            )
            target_garden_db_id = tg["id"]

        conn.execute(
            """UPDATE facts
               SET garden_id = ?,
                   quarantine_status = 'promoted',
                   quarantine_acted_by = ?,
                   quarantine_acted_at = ?,
                   quarantine_reason = ?
               WHERE id = ?""",
            (
                target_garden_db_id,
                identity.entity_uri,
                now,
                req.reason or "promoted",
                req.fact_id,
            ),
        )

        # Audit log (§19.5.6)
        import uuid as _uuid
        audit_id = str(_uuid.uuid4())
        conn.execute(
            "INSERT INTO fact_audit_log"
            " (id, fact_id, event_type, entity_uri, oidc_sub, source,"
            "  attested_key_id, ts)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                audit_id,
                req.fact_id,
                "quarantine_promote",
                identity.entity_uri,
                identity.oidc_sub,
                identity.entity_uri,
                None,
                now,
            ),
        )

    return {
        "fact_id": req.fact_id,
        "action": "promoted",
        "target_garden_id": target_garden_db_id,
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }


@router.post("/{garden_slug_or_id}/reject", status_code=status.HTTP_200_OK)
def reject_fact(
    garden_slug_or_id: str,
    req: QuarantineRejectRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    """Reject a quarantined fact (spec §5.25, §19.5.5).

    Sets confidence = 0.0 and quarantine_status = 'rejected'.
    Requires quarantine:moderator or admin role.
    """
    garden = get_garden_by_slug_or_id(garden_slug_or_id, tenant_id=identity.tenant_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    if not garden.get("quarantine"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="this endpoint is only valid for quarantine gardens",
        )

    require_quarantine_moderator_or_admin(garden, identity)

    now = datetime.now(UTC).isoformat()

    with db() as conn:
        fact_row = conn.execute(
            "SELECT id, quarantine_status, quarantine_garden_id FROM facts WHERE id = ?",
            (req.fact_id,),
        ).fetchone()

        if fact_row is None or fact_row["quarantine_garden_id"] != garden["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="fact not found in quarantine garden",
            )

        if fact_row["quarantine_status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="fact_not_quarantine_pending",
            )

        conn.execute(
            """UPDATE facts
               SET confidence = 0.0,
                   quarantine_status = 'rejected',
                   quarantine_acted_by = ?,
                   quarantine_acted_at = ?,
                   quarantine_reason = ?
               WHERE id = ?""",
            (identity.entity_uri, now, req.reason or "rejected", req.fact_id),
        )

        # Append-only retraction log (§24.2.1 c.3)
        conn.execute(
            "INSERT INTO fact_retractions"
            " (id, fact_id, retracted_at, retracted_by) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), req.fact_id, now, identity.entity_uri),
        )

        # Audit log (§19.5.6)
        import uuid as _uuid
        audit_id = str(_uuid.uuid4())
        conn.execute(
            "INSERT INTO fact_audit_log"
            " (id, fact_id, event_type, entity_uri, oidc_sub, source,"
            "  attested_key_id, ts)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                audit_id,
                req.fact_id,
                "quarantine_reject",
                identity.entity_uri,
                identity.oidc_sub,
                identity.entity_uri,
                None,
                now,
            ),
        )

    return {
        "fact_id": req.fact_id,
        "action": "rejected",
        "acted_by": identity.entity_uri,
        "acted_at": now,
    }
