"""Node metadata endpoint — spec §5.3 /.well-known/stigmem."""

from __future__ import annotations

from fastapi import APIRouter

from ..db import get_or_create_node_id
from ..settings import settings

router = APIRouter(tags=["discovery"])

_NAMESPACES = [
    "stigmem:",
    "rel:",
    "memory:",
    "intent:",
    "roadmap:",
    "preference:",
]


@router.get("/.well-known/stigmem")
def node_metadata() -> dict[str, object]:
    """Return node identity, auth mode, and capability advertisement (spec §5.3)."""
    node_id = get_or_create_node_id()
    return {
        "version": "0.3",
        "node_id": node_id,
        "node_url": settings.node_url,
        "auth": "required" if settings.auth_required else "none",
        "federation": "disabled",  # Phase 3
        "namespaces": _NAMESPACES,
        "spec": "https://github.com/giganomix/stigmem/blob/main/spec/stigmem-spec-v0.3-draft.md",
    }
