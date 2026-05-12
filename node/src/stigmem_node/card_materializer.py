"""Memory card materializer — spec §20 (Phase 9).

A memory card is a per-entity, per-scope pre-aggregated summary that is
refreshed on write.  When recall finds a fresh card with high confidence it
short-circuits raw-fact re-ranking for that entity, reducing per-query work.

Public surface
--------------
mark_entity_stale(entity_uri, scope, tenant_id)
    Called on every assert; marks the entity's card stale so the next recall
    (or explicit GET /v1/cards) triggers a refresh.

refresh_card(entity_uri, scope, tenant_id, conn) -> MemoryCardData | None
    Regenerates the card from current facts using the configured summary model.
    Returns None when the entity has no live facts.

get_fresh_card(entity_uri, scope, tenant_id, conn) -> MemoryCardData | None
    Returns a cached fresh card when available; refreshes if stale.
    Returns None when the entity has no facts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

logger = logging.getLogger("stigmem.cards")

# Cards below this avg_confidence threshold do not short-circuit recall.
CARD_MIN_CONFIDENCE: float = 0.5

# Maximum facts folded into a single card summary.
_SUMMARY_MAX_FACTS = 20


class MemoryCardData(NamedTuple):
    entity_uri: str
    scope: str
    tenant_id: str
    summary: str
    fact_hashes: list[str]
    avg_confidence: float
    refreshed_at: str
    is_stale: bool
    has_contradictions: bool


def mark_entity_stale(entity_uri: str, scope: str, tenant_id: str) -> None:
    """Open a short-lived DB connection and mark the entity's card stale.

    No-op when no card row exists yet.  Errors are logged and suppressed so
    the caller's write path is never blocked by card bookkeeping.
    """
    try:
        from .db import db

        with db() as conn:
            conn.execute(
                "UPDATE memory_cards SET is_stale = 1"
                " WHERE entity_uri = ? AND tenant_id = ? AND scope = ?",
                (entity_uri, tenant_id, scope),
            )
    except Exception as exc:
        logger.warning("mark_entity_stale failed for %r: %s", entity_uri, exc)


def refresh_card(
    entity_uri: str,
    scope: str,
    tenant_id: str,
    conn: Any,
) -> MemoryCardData | None:
    """Recompute and persist the card for *entity_uri* from current live facts.

    Returns the new MemoryCardData, or None when the entity has no live facts.
    The card row is upserted atomically in *conn*.
    """
    now = datetime.now(UTC).isoformat()

    rows = conn.execute(
        """
        SELECT id, relation, value_type, value_v, confidence, source_trust, timestamp
        FROM facts
        WHERE entity = ? AND scope = ? AND tenant_id = ?
          AND confidence > 0
          AND (valid_until IS NULL OR valid_until > ?)
          AND (quarantine_status IS NULL OR quarantine_status != 'pending')
        ORDER BY confidence DESC, timestamp DESC
        LIMIT ?
        """,
        (entity_uri, scope, tenant_id, now, _SUMMARY_MAX_FACTS),
    ).fetchall()

    if not rows:
        return None

    # Contradiction: multiple facts with the same relation on this entity
    relations_seen: set[str] = set()
    has_contradictions = False
    for row in rows:
        rel = row["relation"]
        if rel in relations_seen:
            has_contradictions = True
            break
        relations_seen.add(rel)

    # Source-trust-weighted average confidence
    total_weight = 0.0
    weighted_conf = 0.0
    for row in rows:
        st = row["source_trust"] if row["source_trust"] is not None else 1.0
        weight = max(0.01, float(st))
        weighted_conf += float(row["confidence"]) * weight
        total_weight += weight
    avg_confidence = round(weighted_conf / total_weight if total_weight > 0 else 0.0, 6)

    # Contributing fact hashes: sha256 of fact id
    fact_hashes = [hashlib.sha256(row["id"].encode()).hexdigest() for row in rows]

    # Local summary: structured text representation
    lines = [f"Entity: {entity_uri}", "Facts:"]
    for row in rows:
        vv = row["value_v"] or ""
        lines.append(f"  {row['relation']}: {vv} (conf={row['confidence']:.2f})")
    summary = "\n".join(lines)

    conn.execute(
        """
        INSERT INTO memory_cards
            (entity_uri, tenant_id, scope, summary, fact_hashes, avg_confidence,
             refreshed_at, is_stale, has_contradictions)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT (entity_uri, tenant_id, scope) DO UPDATE SET
            summary            = excluded.summary,
            fact_hashes        = excluded.fact_hashes,
            avg_confidence     = excluded.avg_confidence,
            refreshed_at       = excluded.refreshed_at,
            is_stale           = 0,
            has_contradictions = excluded.has_contradictions
        """,
        (
            entity_uri,
            tenant_id,
            scope,
            summary,
            json.dumps(fact_hashes),
            avg_confidence,
            now,
            1 if has_contradictions else 0,
        ),
    )

    return MemoryCardData(
        entity_uri=entity_uri,
        scope=scope,
        tenant_id=tenant_id,
        summary=summary,
        fact_hashes=fact_hashes,
        avg_confidence=avg_confidence,
        refreshed_at=now,
        is_stale=False,
        has_contradictions=has_contradictions,
    )


def get_fresh_card(
    entity_uri: str,
    scope: str,
    tenant_id: str,
    conn: Any,
) -> MemoryCardData | None:
    """Return a fresh card for *entity_uri*, refreshing it when stale.

    Returns None when the entity has no live facts.
    """
    row = conn.execute(
        """
        SELECT entity_uri, tenant_id, scope, summary, fact_hashes,
               avg_confidence, refreshed_at, is_stale, has_contradictions
        FROM memory_cards
        WHERE entity_uri = ? AND tenant_id = ? AND scope = ?
        """,
        (entity_uri, tenant_id, scope),
    ).fetchone()

    if row is None or row["is_stale"]:
        return refresh_card(entity_uri, scope, tenant_id, conn)

    return MemoryCardData(
        entity_uri=row["entity_uri"],
        scope=row["scope"],
        tenant_id=row["tenant_id"],
        summary=row["summary"],
        fact_hashes=json.loads(row["fact_hashes"] or "[]"),
        avg_confidence=float(row["avg_confidence"]),
        refreshed_at=row["refreshed_at"],
        is_stale=False,
        has_contradictions=bool(row["has_contradictions"]),
    )
