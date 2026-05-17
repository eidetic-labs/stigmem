"""HTTP read-path enforcement for content-addressed fact integrity."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status

from ..cid import CidMismatchError, verify_cid_from_row

logger = logging.getLogger("stigmem.cid")


def enforce_read_path_cid(row: Any) -> None:
    """Raise ``409 cid_mismatch`` when a stored CID no longer matches a fact row."""
    try:
        verify_cid_from_row(row)
    except CidMismatchError as exc:
        logger.warning(
            "CID mismatch on read path for fact %s: computed=%s stored=%s",
            exc.fact_id,
            exc.computed_cid,
            exc.stored_cid,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "cid_mismatch",
                "message": "stored CID does not match the fact canonical body",
                "fact_id": exc.fact_id,
                "computed_cid": exc.computed_cid,
                "stored_cid": exc.stored_cid,
            },
        ) from exc
