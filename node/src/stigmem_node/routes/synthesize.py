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


def _build_synthesize_sql(
    scope: str, include_expired: bool, limit: int, now: str
) -> tuple[str, list[Any]]:
    """Compose the SELECT for synthesize_scope and its bound params."""
    conditions: list[str] = ["scope = ?"]
    params: list[Any] = [scope]
    if not include_expired:
        conditions.append("(valid_until IS NULL OR valid_until > ?)")
        params.append(now)
    params.append(limit)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM facts WHERE {where} ORDER BY confidence DESC, timestamp DESC LIMIT ?"  # nosec B608 — where built from literal SQL fragments; all user values in params
    return sql, params


def _count_pair_occurrences(rows: list[Any]) -> dict[tuple[str, str], int]:
    """Count (entity, relation) occurrences among non-system facts."""
    seen: dict[tuple[str, str], int] = {}
    for r in rows:
        if not _is_system(r["entity"], r["relation"]):
            key = (r["entity"], r["relation"])
            seen[key] = seen.get(key, 0) + 1
    return seen


def _row_age_seconds(timestamp: str) -> float:
    """Compute age in seconds from an ISO timestamp; 0.0 on parse failure."""
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return (datetime.now(UTC) - ts).total_seconds()
    except (ValueError, TypeError):
        return 0.0


def _build_synthesized_fact(
    r: Any, seen: dict[tuple[str, str], int], now: str
) -> tuple[dict[str, Any], bool, bool]:
    """Return (fact_dict, is_expired, contradicted) for one row."""
    is_expired = r["valid_until"] is not None and r["valid_until"] <= now

    contradicted = False
    if not _is_system(r["entity"], r["relation"]):
        contradicted = seen.get((r["entity"], r["relation"]), 0) > 1

    fact = {
        "id": r["id"],
        "entity": r["entity"],
        "relation": r["relation"],
        "value": {"type": r["value_type"], "v": r["value_v"]},
        "confidence": r["confidence"],
        "timestamp": r["timestamp"],
        "valid_until": r["valid_until"],
        "is_expired": is_expired,
        "age_seconds": _row_age_seconds(r["timestamp"]),
        "contradicted": contradicted,
        "source": r["source"],
    }
    return fact, is_expired, contradicted


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

    sql, params = _build_synthesize_sql(scope, include_expired, limit, now)

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    seen = _count_pair_occurrences(rows)

    facts_out: list[dict[str, Any]] = []
    contradiction_count = 0
    expired_count = 0

    for r in rows:
        fact, is_expired, contradicted = _build_synthesized_fact(r, seen, now)
        if is_expired:
            expired_count += 1
        if contradicted:
            contradiction_count += 1
        facts_out.append(fact)

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
