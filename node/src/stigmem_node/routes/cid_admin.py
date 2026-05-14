"""CID backfill admin routes — spec §25.6.3, §25.7.2."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import Identity, resolve_identity
from ..db import db

logger = logging.getLogger("stigmem.cid_admin")

router = APIRouter(prefix="/v1/admin", tags=["admin", "cid"])


class CidBackfillStatus(BaseModel):
    total_facts: int
    backfilled_facts: int
    pending_facts: int
    backfill_complete: bool


@router.get("/cid-backfill/status", response_model=CidBackfillStatus)
def cid_backfill_status(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> CidBackfillStatus:
    """Return CID backfill progress for this node (Spec-21-Content-Addressed-IDs)."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="read permission required"
        )
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        backfilled = conn.execute("SELECT COUNT(*) FROM facts WHERE cid IS NOT NULL").fetchone()[0]
    pending = total - backfilled
    return CidBackfillStatus(
        total_facts=total,
        backfilled_facts=backfilled,
        pending_facts=pending,
        backfill_complete=(pending == 0),
    )
