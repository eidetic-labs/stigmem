"""Graph traversal route — spec §20 (Phase 9).

GET /v1/graph/neighbors
  ?entity=   required  seed entity URI
  &depth=    1–3; default 1; 400 graph_depth_exceeded if > 3
  &scope=    required; facts MUST NOT cross scopes
  &relation_filter=  optional; prefix-glob (e.g. "memory:*")
  &min_confidence=   optional; default 0.1
  &min_trust=        optional; default 0.0
  &page_size=        default 20; max 200
  &cursor=           opaque pagination cursor; 400 cursor_expired after 300 s
"""

from __future__ import annotations

import base64
import json
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import Identity, resolve_identity
from ..db import db
from ..entity_normalizer import NormalizationError, normalize_entity_uri
from ..models.graph import NeighborItem, NeighborsResponse
from ..recall.graph import MAX_DEPTH, bfs_neighbors

router = APIRouter(prefix="/v1/graph", tags=["graph"])

_CURSOR_TTL_S: float = 300.0


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------


def _encode_cursor(offset: int) -> str:
    payload = json.dumps({"offset": offset, "ts": time.time()}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> int:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        age = time.time() - float(payload["ts"])
        if age > _CURSOR_TTL_S:
            raise HTTPException(
                status_code=400,
                detail={"code": "cursor_expired", "message": "pagination cursor has expired"},
            )
        return int(payload["offset"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_cursor", "message": "unreadable pagination cursor"},
        ) from exc


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/neighbors", response_model=NeighborsResponse)
def graph_neighbors(
    identity: Annotated[Identity, Depends(resolve_identity)],
    entity: str = Query(..., description="Seed entity URI"),
    depth: int = Query(1, ge=1, description="Traversal depth (1–3)"),
    scope: str = Query(..., description="Scope filter; required"),
    relation_filter: str | None = Query(
        None, description="Prefix-glob relation filter (e.g. 'memory:*')"
    ),
    min_confidence: float = Query(0.1, ge=0.0, le=1.0),
    min_trust: float = Query(0.0, ge=0.0, le=1.0),
    page_size: int = Query(20, ge=1, le=200),
    cursor: str | None = Query(None),
) -> Any:
    """Return graph neighbors of entity within depth hops (Spec-X11-Recall-Graph)."""
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    if depth > MAX_DEPTH:
        raise HTTPException(
            status_code=400,
            detail={"code": "graph_depth_exceeded", "message": f"depth must be ≤ {MAX_DEPTH}"},
        )

    try:
        seed = normalize_entity_uri(entity)
    except NormalizationError as exc:
        raise HTTPException(status_code=400, detail=f"invalid_entity_uri: {exc}") from exc

    offset = _decode_cursor(cursor) if cursor else 0

    with db() as conn:
        all_neighbors = bfs_neighbors(
            conn,
            seed_entity=seed,
            max_depth=depth,
            scope=scope,
            tenant_id=identity.tenant_id,
            relation_filter=relation_filter,
            min_confidence=min_confidence,
            min_trust=min_trust,
            identity=identity,
        )

    page = all_neighbors[offset : offset + page_size]
    next_offset = offset + page_size
    next_cursor = _encode_cursor(next_offset) if next_offset < len(all_neighbors) else None

    items = [
        NeighborItem(
            entity=n.entity,
            relation=n.relation,
            hops=n.hops,
            confidence=n.confidence,
            source_trust=n.source_trust,
            path=n.path,
        )
        for n in page
    ]

    return NeighborsResponse(
        entity=seed,
        depth=depth,
        neighbors=items,
        next_cursor=next_cursor,
        total_hint=len(all_neighbors),
    )
