"""Garden CRUD + membership routes — spec §5.14–§5.18, §17."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..garden_acl import (
    get_garden_by_slug_or_id,
    get_member_role,
    is_node_admin,
    require_garden_admin,
    require_garden_read,
)
from ..models import (
    VALID_SCOPES,
    GardenCreateRequest,
    GardenMemberRecord,
    GardenMemberRequest,
    GardenMemberUpdateRequest,
    GardenRecord,
)
from ..settings import settings

router = APIRouter(prefix="/v1/gardens", tags=["gardens"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")


def _garden_id_uri(slug: str) -> str:
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


def _row_to_record(row: dict, include_members: bool = True) -> GardenRecord:
    members = _members_for_garden(row["id"]) if include_members else []
    return GardenRecord(
        id=row["id"],
        garden_id=_garden_id_uri(row["slug"]),
        slug=row["slug"],
        name=row["name"],
        scope=row["scope"],
        description=row.get("description"),
        created_by=row["created_by"],
        created_at=row["created_at"],
        members=members,
    )


@router.post("", response_model=GardenRecord, status_code=status.HTTP_201_CREATED)
def create_garden(
    req: GardenCreateRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenRecord:
    if not identity.can_write():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="write permission required")

    slug = req.slug.lower().strip()
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="slug must match ^[a-z0-9][a-z0-9\\-]{0,62}$",
        )
    if req.scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scope must be one of {VALID_SCOPES}",
        )

    garden_uuid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    with db() as conn:
        existing = conn.execute("SELECT id FROM gardens WHERE slug = ?", (slug,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")

        conn.execute(
            """INSERT INTO gardens (id, slug, name, scope, description, created_by, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (garden_uuid, slug, req.name, req.scope, req.description, identity.entity_uri, now),
        )
        conn.execute(
            """INSERT INTO garden_members (garden_id, entity_uri, role, added_by, added_at)
               VALUES (?,?,?,?,?)""",
            (garden_uuid, identity.entity_uri, "admin", identity.entity_uri, now),
        )
        row = conn.execute("SELECT * FROM gardens WHERE id = ?", (garden_uuid,)).fetchone()

    return _row_to_record(dict(row))


@router.get("", response_model=list[GardenRecord])
def list_gardens(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[GardenRecord]:
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    with db() as conn:
        if is_node_admin(identity):
            rows = conn.execute("SELECT * FROM gardens ORDER BY created_at").fetchall()
        else:
            rows = conn.execute(
                """SELECT g.* FROM gardens g
                   JOIN garden_members m ON g.id = m.garden_id
                   WHERE m.entity_uri = ?
                   ORDER BY g.created_at""",
                (identity.entity_uri,),
            ).fetchall()

    return [_row_to_record(dict(r), include_members=False) for r in rows]


@router.get("/{garden_slug_or_id}", response_model=GardenRecord)
def get_garden(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> GardenRecord:
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

    garden = get_garden_by_slug_or_id(garden_slug_or_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    if not is_node_admin(identity):
        require_garden_read(garden, identity)

    return _row_to_record(garden)


@router.delete("/{garden_slug_or_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_garden(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    garden = get_garden_by_slug_or_id(garden_slug_or_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    with db() as conn:
        conn.execute("DELETE FROM gardens WHERE id = ?", (garden["id"],))


@router.get("/{garden_slug_or_id}/members", response_model=list[GardenMemberRecord])
def list_members(
    garden_slug_or_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[GardenMemberRecord]:
    garden = get_garden_by_slug_or_id(garden_slug_or_id)
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
    garden = get_garden_by_slug_or_id(garden_slug_or_id)
    if garden is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")

    require_garden_admin(garden, identity)

    existing_role = get_member_role(garden["id"], req.entity_uri)
    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"entity is already a member with role '{existing_role}'; use PATCH to change role",
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
    garden = get_garden_by_slug_or_id(garden_slug_or_id)
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


@router.delete("/{garden_slug_or_id}/members/{entity_uri:path}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    garden_slug_or_id: str,
    entity_uri: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    garden = get_garden_by_slug_or_id(garden_slug_or_id)
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
