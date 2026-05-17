"""Time-travel recall implementation."""

from __future__ import annotations

from typing import Any

from ...auth import Identity
from ...models.facts import row_to_record
from ...models.recall import RecallWeights, ScoreBreakdown, ScoredFact
from ...models.tombstones import TombstoneNotice
from ...recall_pipeline import apply_recall_pipeline
from ...source_trust import compute_source_trust
from .common import _estimate_tokens, _public_module
from .ranking import _greedy_pack


def _recall_as_of_impl(
    conn: Any,
    *,
    query: str,
    scope: str,
    as_of: str,
    is_admin_caller: bool,
    tenant_id: str,
    max_chunks: int,
    include_graph: bool,
    identity: Identity,
    weights: RecallWeights,
    depth: int,
) -> tuple[list[ScoredFact], list[TombstoneNotice], bool]:
    """Return (scored_facts, tombstone_notices, tombstone_filtered) for a time-travel
    recall at as_of (§24.4).

    Fetches facts visible at as_of (existing, not expired, not retracted at T),
    scores them, applies tombstone filter, and returns packed chunks.
    """
    from ..facts import _get_tombstone_filter

    # Candidate fetch: facts visible at as_of
    rows = conn.execute(
        """
        SELECT f.*,
               COALESCE(fvo.valid_until, f.valid_until) AS projected_valid_until,
               COALESCE(fvo.confidence, f.confidence) AS projected_confidence,
               COALESCE(fgm.garden_id, f.garden_id) AS projected_garden_id,
               COALESCE(fqs.quarantine_status, f.quarantine_status)
                 AS projected_quarantine_status,
               COALESCE(fqs.quarantine_garden_id, f.quarantine_garden_id)
                 AS projected_quarantine_garden_id,
               (
                 SELECT fca.cid
                 FROM fact_cid_aliases fca
                 WHERE fca.fact_id = f.id
                 ORDER BY fca.cid
                 LIMIT 1
               ) AS projected_cid
        FROM facts f
        LEFT JOIN fact_validity_overrides fvo ON fvo.fact_id = f.id
        LEFT JOIN fact_garden_membership fgm ON fgm.fact_id = f.id
        LEFT JOIN fact_quarantine_status fqs ON fqs.fact_id = f.id
        WHERE f.scope = ?
          AND f.tenant_id = ?
          AND f.timestamp <= ?
          AND (
            COALESCE(fvo.valid_until, f.valid_until) IS NULL
            OR COALESCE(fvo.valid_until, f.valid_until) > ?
          )
          AND NOT EXISTS (
            SELECT 1 FROM fact_retractions fr
            WHERE fr.fact_id = f.id AND fr.retracted_at <= ?
          )
        ORDER BY f.timestamp DESC
        LIMIT ?
        """,
        (scope, tenant_id, as_of, as_of, as_of, max_chunks * 5),
    ).fetchall()

    if not rows:
        return [], [], False

    all_facts_raw = {row["id"]: row_to_record(row) for row in rows}

    # Apply recall pipeline (trust, sanitizer)
    pipeline_out = apply_recall_pipeline(list(all_facts_raw.values()), identity)
    all_facts = {r.id: r for r in pipeline_out}

    # Score using lexical signal against query (recency computed relative to as_of)
    def _recency_as_of(ts_str: str, as_of_ts: str) -> float:
        try:
            from datetime import UTC, datetime

            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            aof = datetime.fromisoformat(as_of_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if aof.tzinfo is None:
                aof = aof.replace(tzinfo=UTC)
            days_old = (aof - ts).days
            return max(0.0, 1.0 - days_old / 365.0)
        except Exception:
            return 0.5

    scored: list[ScoredFact] = []
    q_lower = query.lower()
    total_weight = weights.lexical + weights.recency + weights.source_trust
    if total_weight <= 0:
        total_weight = 1.0

    for record in all_facts.values():
        if record.quarantine_status == "pending":
            continue
        text = f"{record.entity} {record.relation} {record.value.v or ''}".lower()
        lex = sum(1.0 for w in q_lower.split() if w and w in text) / max(1, len(q_lower.split()))
        rec_s = _recency_as_of(record.timestamp, as_of)
        trust_s = 0.5
        if _public_module().settings.trust_mode != "off":
            trust_s = compute_source_trust(record.source, record.scope, identity)
        raw = (
            weights.lexical * lex + weights.recency * rec_s + weights.source_trust * trust_s
        ) / total_weight
        final_score = raw * max(0.0, record.confidence)
        scored.append(
            ScoredFact(
                fact=record,
                score=round(final_score, 6),
                score_breakdown=ScoreBreakdown(
                    lexical=round(lex, 4),
                    recency=round(rec_s, 4),
                    source_trust=round(trust_s, 4),
                    weighted_total=round(final_score, 6),
                ),
                hop_distance=0,
                token_estimate=_estimate_tokens(record),
            )
        )

    scored.sort(key=lambda c: c.score, reverse=True)

    # Tombstone filter (§24.3)
    entity_uris = list({sf.fact.entity for sf in scored})
    excluded, notices = _get_tombstone_filter(conn, entity_uris, scope, is_admin_caller)
    tombstone_filtered = False
    if excluded:
        scored = [sf for sf in scored if sf.fact.entity not in excluded]
        tombstone_filtered = True

    packed, _, _ = _greedy_pack(scored[:max_chunks], max_chunks * 20)
    return packed[:max_chunks], notices, tombstone_filtered
