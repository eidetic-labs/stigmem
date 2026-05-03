"""Garden ACL enforcement — spec §17.3."""

from __future__ import annotations

from fastapi import HTTPException, status

from .auth import Identity
from .db import db


def get_garden_by_slug_or_id(slug_or_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM gardens WHERE slug = ? OR id = ?",
            (slug_or_id, slug_or_id),
        ).fetchone()
    return dict(row) if row is not None else None


def get_member_role(garden_id: str, entity_uri: str) -> str | None:
    with db() as conn:
        row = conn.execute(
            "SELECT role FROM garden_members WHERE garden_id = ? AND entity_uri = ?",
            (garden_id, entity_uri),
        ).fetchone()
    return row["role"] if row is not None else None


def is_node_admin(identity: Identity) -> bool:
    return identity.entity_uri in {"anon:trusted"} or "admin" in identity.permissions


def require_garden_read(garden: dict, identity: Identity) -> None:
    if is_node_admin(identity):
        return
    role = get_member_role(garden["id"], identity.entity_uri)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not a member of this garden",
        )


def require_garden_write(garden: dict, identity: Identity) -> None:
    if is_node_admin(identity):
        return
    role = get_member_role(garden["id"], identity.entity_uri)
    if role not in ("admin", "writer"):
        if role == "reader":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reader role cannot write facts; requires writer or admin",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not a member of this garden",
        )


def require_garden_admin(garden: dict, identity: Identity) -> None:
    if is_node_admin(identity):
        return
    role = get_member_role(garden["id"], identity.entity_uri)
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role required for this operation",
        )


def caller_can_see_garden(garden: dict, identity: Identity) -> bool:
    if is_node_admin(identity):
        return True
    return get_member_role(garden["id"], identity.entity_uri) is not None
