"""Configurable decay sweeper — marks stale facts as expired (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .db import db
from .settings import settings

# Exclude system-internal facts (stigmem: prefix but not stigmem:// URI content)
_NOT_SYSTEM_SQL = (
    "NOT (entity LIKE 'stigmem:%' AND entity NOT LIKE 'stigmem://%') "
    "AND NOT (relation LIKE 'stigmem:%' AND relation NOT LIKE 'stigmem://%')"
)


def _resolve_effective_ttl(ttl_seconds: int | None) -> int | None:
    """Apply override-or-settings precedence; returns None when disabled."""
    if ttl_seconds is not None:
        return ttl_seconds  # 0 is valid: expire everything
    if settings.decay_ttl_seconds > 0:
        return settings.decay_ttl_seconds
    return None


def _resolve_effective_min_conf(min_confidence: float | None) -> float | None:
    """Apply override-or-settings precedence; returns None when disabled."""
    if min_confidence is not None and min_confidence > 0.0:
        return min_confidence
    if settings.decay_min_confidence > 0.0:
        return settings.decay_min_confidence
    return None


def _select_ttl_candidates(
    conn: Any, effective_ttl: int, now_dt: datetime, scope: str | None
) -> list[str]:
    """Return ids of non-expiring facts whose timestamp is at/before cutoff."""
    cutoff = (now_dt - timedelta(seconds=effective_ttl)).isoformat()
    sql = (
        f"SELECT id FROM facts "  # nosec B608 — _NOT_SYSTEM_SQL is a module-level constant; user values in params
        f"WHERE timestamp <= ? AND valid_until IS NULL AND {_NOT_SYSTEM_SQL}"
    )
    params: list[Any] = [cutoff]
    if scope:
        sql += " AND scope = ?"
        params.append(scope)
    return [r["id"] for r in conn.execute(sql, params).fetchall()]


def _select_confidence_candidates(
    conn: Any, effective_min_conf: float, now: str, scope: str | None
) -> list[str]:
    """Return ids of active facts below the confidence floor."""
    sql = (
        f"SELECT id FROM facts "  # nosec B608 — _NOT_SYSTEM_SQL is a module-level constant; user values in params
        f"WHERE confidence < ? AND confidence > 0.0 "
        f"AND (valid_until IS NULL OR valid_until > ?) "
        f"AND {_NOT_SYSTEM_SQL}"
    )
    params: list[Any] = [effective_min_conf, now]
    if scope:
        sql += " AND scope = ?"
        params.append(scope)
    return [r["id"] for r in conn.execute(sql, params).fetchall()]


def _apply_decay(conn: Any, candidates: list[str], conf_ids: list[str], now: str) -> None:
    """Mark candidates expired, log retractions for confidence drops, sync edges."""
    placeholders = ",".join("?" * len(candidates))
    conn.execute(
        f"UPDATE facts SET valid_until = ? WHERE id IN ({placeholders})",  # nosec B608 — placeholders is "?,?,?" sequence, not user input
        [now, *candidates],
    )
    # Append-only retraction log for confidence-floor drops (§24.2.1 c.3)
    if conf_ids:
        conn.executemany(
            "INSERT INTO fact_retractions (id, fact_id, retracted_at, retracted_by)"
            " VALUES (?,?,?,?)",
            [(str(uuid.uuid4()), fid, now, "stigmem:system:decay") for fid in conf_ids],
        )
    # Graph adjacency index (§20.1.2): propagate expiry to entity_edges
    from .graph_index import sync_edge_expiry
    sync_edge_expiry(conn, candidates, now)


def run_decay_sweep(
    ttl_seconds: int | None = None,
    min_confidence: float | None = None,
    scope: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mark stale facts as expired by setting valid_until to now.

    - TTL decay: non-expiring facts whose timestamp is at or before (now - ttl_seconds).
      Passing ttl_seconds=0 expires all non-expiring facts regardless of age.
    - Confidence decay: active facts whose confidence is below min_confidence.
    - System facts (stigmem: entity/relation, not stigmem://) are never decayed.
    - dry_run=True returns counts without writing.

    Returns {"scanned": N, "decayed": M, "dry_run": bool}.
    """
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()

    # Explicit args override settings defaults; settings=0/0.0 means "disabled"
    effective_ttl = _resolve_effective_ttl(ttl_seconds)
    effective_min_conf = _resolve_effective_min_conf(min_confidence)

    ttl_ids: list[str] = []
    conf_ids: list[str] = []

    with db() as conn:
        if effective_ttl is not None:
            ttl_ids = _select_ttl_candidates(conn, effective_ttl, now_dt, scope)

        if effective_min_conf is not None:
            conf_ids = _select_confidence_candidates(conn, effective_min_conf, now, scope)

        candidates = list({*ttl_ids, *conf_ids})

        if not dry_run and candidates:
            _apply_decay(conn, candidates, conf_ids, now)

    return {
        "scanned": len(candidates),
        "decayed": len(candidates) if not dry_run else 0,
        "dry_run": dry_run,
    }
