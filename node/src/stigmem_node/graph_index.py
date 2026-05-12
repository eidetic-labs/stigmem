"""Graph adjacency index maintenance — spec §20.1.

Called from:
  - routes/facts.py on every ref-typed fact insert
  - decay.py when facts expire (valid_until propagation)
  - routes/facts.py contradiction path (confidence = 0.0 soft-delete)
"""

from __future__ import annotations

import time
from typing import Any


def upsert_edge(
    conn: Any,
    fact_id: str,
    subject: str,
    relation: str,
    object_uri: str,
    scope: str,
    confidence: float,
    garden_id: str | None,
    tenant_id: str,
    received_from: str | None,
    source_trust: float | None = None,
    valid_until: str | None = None,
) -> None:
    """Insert or replace the entity_edges row for a ref-typed fact.

    On conflict (same fact_id), updates mutable fields so re-assertions stay
    in sync.  Called inside the same transaction as the facts INSERT.
    """
    now_ms = int(time.time() * 1000)
    conn.execute(
        """INSERT INTO entity_edges
               (id, subject, relation, object, scope, garden_id, tenant_id,
                received_from, valid_until, confidence, source_trust,
                decay_epoch, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,?)
           ON CONFLICT(id) DO UPDATE SET
               confidence   = excluded.confidence,
               source_trust = excluded.source_trust,
               valid_until  = excluded.valid_until,
               decay_epoch  = excluded.decay_epoch""",
        (
            fact_id,
            subject,
            relation,
            object_uri,
            scope,
            garden_id,
            tenant_id,
            received_from,
            valid_until,
            confidence,
            source_trust,
            now_ms,
        ),
    )


def sync_edge_confidence(
    conn: Any,
    fact_id: str,
    confidence: float,
    decay_epoch_ms: int,
) -> None:
    """Propagate a retraction (confidence=0.0) to entity_edges (§20.1.3)."""
    conn.execute(
        "UPDATE entity_edges SET confidence = ?, decay_epoch = ? WHERE id = ?",
        (confidence, decay_epoch_ms, fact_id),
    )


def sync_edge_expiry(
    conn: Any,
    fact_ids: list[str],
    valid_until: str,
) -> None:
    """Propagate TTL/confidence-decay expiry to entity_edges (§20.1.2)."""
    if not fact_ids:
        return
    placeholders = ",".join("?" * len(fact_ids))
    now_ms = int(time.time() * 1000)
    conn.execute(
        f"UPDATE entity_edges SET valid_until = ?, decay_epoch = ? WHERE id IN ({placeholders})",  # nosec B608
        [valid_until, now_ms, *fact_ids],
    )
