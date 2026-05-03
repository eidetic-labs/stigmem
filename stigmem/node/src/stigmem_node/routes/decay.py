"""Decay sweeper HTTP route — Phase 6 (spec §decay)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import Identity, resolve_identity
from ..decay import run_decay_sweep
from ..models import VALID_SCOPES

router = APIRouter(prefix="/v1/decay", tags=["decay"])


@router.post("/sweep")
def decay_sweep(
    identity: Annotated[Identity, Depends(resolve_identity)],
    dry_run: bool = Query(False, description="Report what would be decayed without writing"),
    scope: str | None = Query(None, description="Restrict sweep to one scope"),
    ttl_seconds: int | None = Query(
        None, ge=0, description="Expire non-expiring facts older than N seconds (0 = all)"
    ),
    min_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Expire active facts below this confidence"
    ),
) -> dict[str, Any]:
    """Mark stale facts as expired. Cron-friendly one-shot sweeper (Phase 6).

    At least one of ttl_seconds or min_confidence should be provided, or defaults
    from STIGMEM_DECAY_TTL_SECONDS / STIGMEM_DECAY_MIN_CONFIDENCE are used.
    System facts (stigmem: entity/relation prefix) are never decayed.
    """
    if not identity.can_write():
        raise HTTPException(status_code=403, detail="write permission required")
    if scope is not None and scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")

    return run_decay_sweep(
        ttl_seconds=ttl_seconds,
        min_confidence=min_confidence,
        scope=scope,
        dry_run=dry_run,
    )
