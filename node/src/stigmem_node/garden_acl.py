"""Garden ACL enforcement — spec §17.3, §19.5.3.

Gardens are named, ACL'd partitions above scope (v0.9).
ACL is checked at fact read and write time in addition to scope enforcement.
Quarantine gardens extend this with the quarantine:moderator role (v1.1).
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from .auth import Identity
from .db import db


def get_garden_by_slug_or_id(
    slug_or_id: str, tenant_id: str | None = None
) -> dict[str, Any] | None:
    """Return a garden row by slug or by its UUID id.

    When tenant_id is provided, slug lookups are scoped to that tenant so that
    the same slug used by different tenants resolves to the correct garden.
    UUID lookups are globally unique and do not require tenant scoping.
    """
    with db() as conn:
        if tenant_id is not None:
            # Slug lookup scoped to tenant; UUID lookup is always unique
            row = conn.execute(
                "SELECT * FROM gardens WHERE (slug = ? AND tenant_id = ?) OR id = ?",
                (slug_or_id, tenant_id, slug_or_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM gardens WHERE slug = ? OR id = ?",
                (slug_or_id, slug_or_id),
            ).fetchone()
    return dict(row) if row is not None else None


def get_garden_by_garden_uri(
    garden_uri: str, tenant_id: str | None = None
) -> dict[str, Any] | None:
    """Return a garden row by its stigmem://authority/garden/{slug} URI."""
    # Extract slug from URI: stigmem://authority/garden/{slug}
    parts = garden_uri.split("/garden/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    slug = parts[1].rstrip("/")
    return get_garden_by_slug_or_id(slug, tenant_id=tenant_id)


def get_member_role(garden_id: str, entity_uri: str) -> str | None:
    """Return the role of entity_uri in the given garden UUID, or None if not a member."""
    with db() as conn:
        row = conn.execute(
            "SELECT role FROM garden_members WHERE garden_id = ? AND entity_uri = ?",
            (garden_id, entity_uri),
        ).fetchone()
    return row["role"] if row is not None else None


def require_garden_write(garden: dict[str, Any], identity: Identity) -> None:
    """Raise 403 if identity cannot write facts into this garden (spec §17.3)."""
    role = get_member_role(garden["id"], identity.entity_uri)
    if role not in ("admin", "writer"):
        if role == "reader":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="write permission required — you are a reader in this garden",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not a member of this garden",
        )


def require_garden_read(garden: dict[str, Any], identity: Identity) -> None:
    """Raise 403 if identity cannot read facts from this garden (spec §17.3)."""
    role = get_member_role(garden["id"], identity.entity_uri)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not a member of this garden",
        )


def require_garden_admin(garden: dict[str, Any], identity: Identity) -> None:
    """Raise 403 if identity is not an admin of this garden."""
    role = get_member_role(garden["id"], identity.entity_uri)
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="garden admin permission required",
        )


def caller_can_see_garden(garden_id: str, identity: Identity) -> bool:
    """Return True if identity holds any role in the garden (for query-time filtering)."""
    role = get_member_role(garden_id, identity.entity_uri)
    return role is not None


def is_node_admin(identity: Identity) -> bool:
    """Node admin: any identity with write permission (spec §5.15)."""
    return identity.can_write()


def require_quarantine_moderator_or_admin(garden: dict[str, Any], identity: Identity) -> None:
    """Raise 403 if identity cannot promote/reject quarantined facts (spec §19.5.3).

    Allowed roles: 'admin' or 'quarantine:moderator'.
    """
    role = get_member_role(garden["id"], identity.entity_uri)
    if role not in ("admin", "quarantine:moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="quarantine:moderator or admin role required to promote/reject facts",
        )


def has_elevated_quarantine_role(garden: dict[str, Any], identity: Identity) -> bool:
    """True if identity holds admin or quarantine:moderator in a quarantine garden."""
    role = get_member_role(garden["id"], identity.entity_uri)
    return role in ("admin", "quarantine:moderator")


def quarantine_garden_has_pending_facts(garden_uuid: str) -> bool:
    """True if the quarantine garden holds at least one fact with quarantine_status='pending'."""
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM facts WHERE quarantine_garden_id = ? AND quarantine_status = 'pending' LIMIT 1",
            (garden_uuid,),
        ).fetchone()
    return row is not None
