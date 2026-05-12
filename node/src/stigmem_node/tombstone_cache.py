"""Tombstone in-process cache — spec §23.3.3 r.4.

Active tombstone entity URIs are cached in-process and refreshed at most every
60 seconds to avoid per-event DB reads during subscription delivery and recall.
Worst-case 60-second leak window after tombstone creation is acceptable per spec.
"""

from __future__ import annotations

import threading
import time

# §23.3.3 r.4: refresh interval ceiling
_CACHE_TTL_SECONDS: float = 60.0

_lock = threading.Lock()
_tombstoned: frozenset[tuple[str, str]] = frozenset()  # (entity_uri, tenant_id)
_last_refresh: float = 0.0


def _load_from_db() -> frozenset[tuple[str, str]]:
    from .db import db

    with db() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT t.entity_uri, t.tenant_id
            FROM tombstones t
            WHERE NOT EXISTS (
                SELECT 1 FROM tombstone_revocations r
                WHERE r.tombstone_id = t.id
            )
            """
        ).fetchall()
    return frozenset((row["entity_uri"], row["tenant_id"]) for row in rows)


def _ensure_fresh() -> None:
    global _tombstoned, _last_refresh
    if time.monotonic() - _last_refresh < _CACHE_TTL_SECONDS:
        return
    with _lock:
        # Double-check under lock — another thread may have refreshed already.
        if time.monotonic() - _last_refresh < _CACHE_TTL_SECONDS:
            return
        _tombstoned = _load_from_db()
        _last_refresh = time.monotonic()


def invalidate() -> None:
    """Force cache expiry so the next call to is_tombstoned triggers a DB read.

    Call after writing a new tombstone or revocation row.
    """
    global _last_refresh
    with _lock:
        _last_refresh = 0.0


def is_tombstoned(entity_uri: str, tenant_id: str = "default") -> bool:
    """Return True if *entity_uri* has an active tombstone in *tenant_id*.

    Uses a thread-safe in-process cache refreshed at most every 60 s (§23.3.3 r.4).
    """
    _ensure_fresh()
    return (entity_uri, tenant_id) in _tombstoned
