"""Recall scoring and packing stages."""

from __future__ import annotations

from ...auth import Identity
from ...garden_acl import caller_can_see_garden
from ...models.facts import FactRecord
from ...models.recall import RecallWeights, ScoreBreakdown, ScoredFact
from ...source_trust import compute_source_trust
from .common import _estimate_tokens, _public_module, _recency_score


def _score_candidates(
    all_facts: dict[str, FactRecord],
    lex_scores: dict[str, float],
    sem_scores: dict[str, float],
    graph_hops: dict[str, int],
    weights: RecallWeights,
    identity: Identity,
    depth: int,
) -> list[ScoredFact]:
    """Compute composite score for each candidate fact."""
    w = weights
    total_weight = w.lexical + w.semantic + w.graph + w.source_trust + w.recency
    if total_weight <= 0:
        total_weight = 1.0

    results: list[ScoredFact] = []

    for fact_id, record in all_facts.items():
        # Skip quarantined / fully-redacted
        if record.quarantine_status == "pending":
            continue

        # Salience signal: contradiction-resolution status
        contradiction_factor = 0.1 if record.contradicted else 1.0

        # Salience signal: garden tier (quarantine garden = 0, normal = 1)
        garden_factor = 1.0
        if record.garden_id is not None:
            if not caller_can_see_garden(record.garden_id, identity):
                continue  # hidden by ACL
            # Penalise quarantine-tagged gardens (§17)
            garden_factor = 0.5

        # Salience signal: source trust
        st_score = 0.5  # default when trust_mode=off
        if _public_module().settings.trust_mode != "off":
            st_score = compute_source_trust(record.source, record.scope, identity)

        # Lexical signal
        lex = lex_scores.get(fact_id, 0.0)

        # Semantic signal
        sem = sem_scores.get(fact_id, 0.0)

        # Graph signal: inverse of hop distance (direct=0 → no graph bonus, 1 hop → 0.5, etc.)
        hops = graph_hops.get(fact_id)
        if hops is not None and hops > 0:
            graph_s = 1.0 / (1.0 + hops)
        else:
            graph_s = 0.0 if hops is None else 1.0

        # Salience signal: recency
        recency_s = _recency_score(record.timestamp)

        # Salience signal: decay proxy (confidence itself encodes decay)
        decay_factor = max(0.0, record.confidence)

        # Weighted sum (normalised by sum of non-zero weights)
        raw_total = (
            w.lexical * lex
            + w.semantic * sem
            + w.graph * graph_s
            + w.source_trust * st_score
            + w.recency * recency_s
        ) / total_weight

        # Apply multiplicative adjustments
        final_score = raw_total * decay_factor * contradiction_factor * garden_factor

        breakdown = ScoreBreakdown(
            lexical=round(lex, 4),
            semantic=round(sem, 4),
            graph=round(graph_s, 4),
            source_trust=round(st_score, 4),
            recency=round(recency_s, 4),
            weighted_total=round(final_score, 6),
        )

        results.append(
            ScoredFact(
                fact=record,
                score=round(final_score, 6),
                score_breakdown=breakdown,
                hop_distance=hops if hops is not None else 0,
                token_estimate=_estimate_tokens(record),
            )
        )

    return results


# ---------------------------------------------------------------------------
# Token-budget greedy packing
# ---------------------------------------------------------------------------


def _greedy_pack(
    candidates: list[ScoredFact],
    token_budget: int,
) -> tuple[list[ScoredFact], int, bool]:
    """Sort by score desc; include facts until budget exhausted.

    Returns (packed_facts, tokens_used, truncated).
    """
    candidates.sort(key=lambda c: c.score, reverse=True)
    packed: list[ScoredFact] = []
    tokens_used = 0
    truncated = False

    for candidate in candidates:
        if tokens_used + candidate.token_estimate > token_budget:
            truncated = True
            continue  # skip this fact (too large), keep trying smaller ones
        packed.append(candidate)
        tokens_used += candidate.token_estimate

    # Secondary sort within packed: preserve score order
    packed.sort(key=lambda c: c.score, reverse=True)
    return packed, tokens_used, truncated
