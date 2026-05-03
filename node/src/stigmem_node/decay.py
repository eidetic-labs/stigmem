"""Configurable decay sweeper — marks stale facts as expired (Phase 6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .db import db
from .settings import settings

# Exclude system-internal facts (stigmem: prefix but not stigmem:// URI content)
_NOT_SYSTEM_SQL = (
    "NOT (entity LIKE 'stigmem:%' AND entity NOT LIKE 'stigmem://%') "
    "AND NOT (relation LIKE 'stigmem:%' AND relation NOT LIKE 'stigmem://%')"
)


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
    effective_ttl: int | None
    if ttl_seconds is not None:
        effective_ttl = ttl_seconds  # 0 is valid: expire everything
    elif settings.decay_ttl_seconds > 0:
        effective_ttl = settings.decay_ttl_seconds
    else:
        effective_ttl = None

    effective_min_conf: float | None
    if min_confidence is not None and min_confidence > 0.0:
        effective_min_conf = min_confidence
    elif settings.decay_min_confidence > 0.0:
        effective_min_conf = settings.decay_min_confidence
    else:
        effective_min_conf = None

    ttl_ids: list[str] = []
    conf_ids: list[str] = []

    with db() as conn:
        if effective_ttl is not None:
            cutoff = (now_dt - timedelta(seconds=effective_ttl)).isoformat()
            sql = (
                f"SELECT id FROM facts "
                f"WHERE timestamp <= ? AND valid_until IS NULL AND {_NOT_SYSTEM_SQL}"
            )
            params: list[Any] = [cutoff]
            if scope:
                sql += " AND scope = ?"
                params.append(scope)
            ttl_ids = [r["id"] for r in conn.execute(sql, params).fetchall()]

        if effective_min_conf is not None:
            sql = (
                f"SELECT id FROM facts "
                f"WHERE confidence < ? AND confidence > 0.0 "
                f"AND (valid_until IS NULL OR valid_until > ?) "
                f"AND {_NOT_SYSTEM_SQL}"
            )
            params = [effective_min_conf, now]
            if scope:
                sql += " AND scope = ?"
                params.append(scope)
            conf_ids = [r["id"] for r in conn.execute(sql, params).fetchall()]

        candidates = list({*ttl_ids, *conf_ids})

        if not dry_run and candidates:
            placeholders = ",".join("?" * len(candidates))
            conn.execute(
                f"UPDATE facts SET valid_until = ? WHERE id IN ({placeholders})",
                [now, *candidates],
            )

    return {
        "scanned": len(candidates),
        "decayed": len(candidates) if not dry_run else 0,
        "dry_run": dry_run,
    }
