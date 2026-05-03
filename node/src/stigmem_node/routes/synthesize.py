"""Scope synthesis route — Phase 6 (spec §synthesize)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import Identity, resolve_identity
from ..db import db
from ..models import VALID_SCOPES

router = APIRouter(prefix="/v1/scopes", tags=["synthesis"])

_SYS_PREFIX = "stigmem:"
_URI_PREFIX = "stigmem://"


def _is_system(entity: str, relation: str) -> bool:
    return (entity.startswith(_SYS_PREFIX) and not entity.startswith(_URI_PREFIX)) or (
        relation.startswith(_SYS_PREFIX) and not relation.startswith(_URI_PREFIX)
    )


@router.get("/{scope}/synthesize")
def synthesize_scope(
    scope: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
    include_expired: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    """Confidence-weighted summary of all facts in a scope (Phase 6).

    Returns facts sorted by confidence descending, with contradiction flags and
    freshness metadata for each fact, plus aggregate statistics.
    """
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")

    now = datetime.now(UTC).isoformat()

    conditions: list[str] = ["scope = ?"]
    params: list[Any] = [scope]
    if not include_expired:
        conditions.append("(valid_until IS NULL OR valid_until > ?)")
        params.append(now)
    params.append(limit)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM facts WHERE {where} ORDER BY confidence DESC, timestamp DESC LIMIT ?"  # nosec B608 — where built from literal SQL fragments; all user values in params

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    # Count occurrences per (entity, relation) among non-system facts to detect contradictions
    seen: dict[tuple[str, str], int] = {}
    for r in rows:
        if not _is_system(r["entity"], r["relation"]):
            key = (r["entity"], r["relation"])
            seen[key] = seen.get(key, 0) + 1

    facts_out: list[dict[str, Any]] = []
    contradiction_count = 0
    expired_count = 0

    for r in rows:
        is_expired = r["valid_until"] is not None and r["valid_until"] <= now
        if is_expired:
            expired_count += 1

        contradicted = False
        if not _is_system(r["entity"], r["relation"]):
            contradicted = seen.get((r["entity"], r["relation"]), 0) > 1
            if contradicted:
                contradiction_count += 1

        try:
            ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            age_seconds = (datetime.now(UTC) - ts).total_seconds()
        except (ValueError, TypeError):
            age_seconds = 0.0

        facts_out.append(
            {
                "id": r["id"],
                "entity": r["entity"],
                "relation": r["relation"],
                "value": {"type": r["value_type"], "v": r["value_v"]},
                "confidence": r["confidence"],
                "timestamp": r["timestamp"],
                "valid_until": r["valid_until"],
                "is_expired": is_expired,
                "age_seconds": age_seconds,
                "contradicted": contradicted,
                "source": r["source"],
            }
        )

    confidences = [f["confidence"] for f in facts_out]
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    timestamps = [f["timestamp"] for f in facts_out]

    return {
        "scope": scope,
        "fact_count": len(facts_out),
        "facts": facts_out,
        "contradiction_count": contradiction_count,
        "mean_confidence": mean_confidence,
        "freshest_timestamp": max(timestamps) if timestamps else None,
        "oldest_timestamp": min(timestamps) if timestamps else None,
        "expired_fact_count": expired_count,
        "synthesized_at": now,
    }
