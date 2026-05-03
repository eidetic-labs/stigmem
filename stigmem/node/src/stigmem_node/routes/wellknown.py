"""Node metadata endpoint — spec §5.3 /.well-known/stigmem (v0.5)."""

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
    """Return node identity, auth mode, and federation capability advertisement (spec §5.3)."""
    node_id = get_or_create_node_id()
    result: dict[str, object] = {
        "version": "0.5",
        "node_id": node_id,
        "node_url": settings.node_url,
        "auth": "required" if settings.auth_required else "none",
        "federation": "enabled" if settings.federation_enabled else "disabled",
        "namespaces": _NAMESPACES,
        "spec": "https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.5-draft.md",
    }

    if settings.federation_enabled:
        from ..peer_token import get_local_pubkey
        result["federation_pubkey"] = get_local_pubkey()
        result["federation_version"] = "0.5"
        result["federation_endpoints"] = {
            "peers": "/v1/federation/peers",
            "facts": "/v1/federation/facts",
            "push": "/v1/federation/facts/push" if settings.federation_push_enabled else None,
        }

    return result
