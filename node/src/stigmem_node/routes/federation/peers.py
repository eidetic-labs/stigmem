"""Federation peer registration and listing routes."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, HTTPException, status

from ...auth import Identity, resolve_identity
from ...db import db
from ...models.federation import PeerRegisterRequest, PeerRegisterResponse
from .._federation_impl import register_peer_impl
from .common import router


@router.post(
    "/v1/federation/peers",
    response_model=PeerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_peer(
    req: PeerRegisterRequest,
    background_tasks: BackgroundTasks,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> PeerRegisterResponse:
    """Register a peer.

    Fetches its well-known doc and verifies declaration_sig
    (Spec-05-Federation-Trust).
    """
    # Implementation lives in _federation_impl.register_peer_impl.
    return await register_peer_impl(req, background_tasks, identity)


# ---------------------------------------------------------------------------
# GET /v1/federation/peers — list peers (§5.7)
# ---------------------------------------------------------------------------


@router.get("/v1/federation/peers")
def list_peers(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    if not identity.can_federate():
        raise HTTPException(status_code=403, detail="federate permission required")
    with db() as conn:
        rows = conn.execute(
            "SELECT id, node_id, node_url, status, allowed_scopes, established_at FROM peers"
        ).fetchall()
    return {
        "peers": [
            {
                "peer_id": r["id"],
                "node_id": r["node_id"],
                "node_url": r["node_url"],
                "status": r["status"],
                "allowed_scopes": json.loads(r["allowed_scopes"]),
                "established_at": r["established_at"],
            }
            for r in rows
        ]
    }
