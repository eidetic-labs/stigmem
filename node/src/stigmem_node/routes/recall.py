"""Hybrid recall endpoint — spec §20 (Phase 9).

POST /v1/recall  Hybrid ranker combining:
    - lexical (FTS5 / BM25)
    - dense vector (sqlite-vec, when embed_enabled=True)
    - graph traversal (bfs_neighbors k-hop from top-result entities)
  Returns ranked, token-budget-packed response with per-fact score breakdown.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from ..auth import Identity, resolve_identity
from ..card_materializer import CARD_MIN_CONFIDENCE, get_fresh_card
from ..db import db
from ..garden_acl import caller_can_see_garden
from ..graph import MAX_DEPTH, bfs_neighbors
from ..metrics import FACT_READ, RECALL_RANKER_DURATION, observe_duration
from ..models import VALID_SCOPES, FactRecord, FactValue, TombstoneNotice, row_to_record
from ..recall_pipeline import apply_recall_pipeline
from ..settings import settings
from ..source_trust import compute_source_trust
from ..tombstone_cache import is_tombstoned as _is_tombstoned
from ..tracing import start_span

logger = logging.getLogger("stigmem.recall")

router = APIRouter(prefix="/v1/recall", tags=["recall"])

# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS = {
    "lexical": 0.35,
    "semantic": 0.35,
    "graph": 0.15,
    "source_trust": 0.10,
    "recency": 0.05,
}

_MAX_SEED_ENTITIES = 5
_MAX_GRAPH_ENTITIES = 50
_MAX_CANDIDATES = 500


class RecallWeights(BaseModel):
    lexical: float = Field(0.35, ge=0.0, le=1.0)
    semantic: float = Field(0.35, ge=0.0, le=1.0)
    graph: float = Field(0.15, ge=0.0, le=1.0)
    source_trust: float = Field(0.10, ge=0.0, le=1.0)
    recency: float = Field(0.05, ge=0.0, le=1.0)


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1)
    scope: str = Field("local")
    token_budget: int = Field(4000, ge=1, le=200_000)
    depth: int = Field(2, ge=1, le=3)
    weights: RecallWeights = Field(default_factory=RecallWeights)
    min_confidence: float = Field(0.1, ge=0.0, le=1.0)
    include_neighbors: bool = Field(True)
    limit: int = Field(100, ge=1, le=500, description="Max candidates before token-budget packing")
    as_of: str | None = Field(
        None,
        description="§24: time-travel — return facts visible at this ISO 8601 timestamp",
    )


class ScoreBreakdown(BaseModel):
    lexical: float = 0.0
    semantic: float = 0.0
    graph: float = 0.0
    source_trust: float = 0.0
    recency: float = 0.0
    weighted_total: float = 0.0


class ScoredFact(BaseModel):
    fact: FactRecord
    score: float
    score_breakdown: ScoreBreakdown
    hop_distance: int = 0
    token_estimate: int
    from_card: bool = False


class RecallResponse(BaseModel):
    recall_id: str
    query_hash: str
    facts: list[ScoredFact]
    total_scored: int | None = None
    token_budget: int
    tokens_used: int
    truncated: bool
    tombstone_notices: list[TombstoneNotice] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FTS5_SPECIAL = re.compile(r'["()\^*\-:,]+')


def _fts_query(q: str) -> str:
    """Sanitise a user query string for SQLite FTS5 MATCH."""
    cleaned = _FTS5_SPECIAL.sub(" ", q).strip()
    return cleaned or '""'


def _like_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, float]:
    """LIKE-based text scan — fallback when FTS5 is unavailable (libsql, postgres)."""
    words = [w for w in re.sub(r"[^\w]", " ", query).split() if len(w) >= 2][:5]
    if not words:
        return {}
    clauses = " OR ".join("(value_v LIKE ? OR entity LIKE ?)" for _ in words)
    params: list[Any] = []
    for w in words:
        pat = f"%{w}%"
        params.extend([pat, pat])
    params.extend([scope, tenant_id, min_confidence, now, k])
    try:
        rows = conn.execute(
            (  # nosec B608
                "SELECT id AS fact_id, confidence AS rank FROM facts"
                f" WHERE ({clauses})"
                " AND scope = ? AND tenant_id = ? AND confidence >= ?"
                " AND (valid_until IS NULL OR valid_until > ?)"
                " ORDER BY confidence DESC LIMIT ?"
            ),
            params,
        ).fetchall()
    except Exception as exc:
        logger.warning("LIKE fallback search failed: %s", exc)
        return {}
    if not rows:
        return {}
    max_conf = max(float(row["rank"]) for row in rows)
    if max_conf <= 0:
        return {}
    return {row["fact_id"]: float(row["rank"]) / max_conf for row in rows}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _estimate_tokens(record: FactRecord) -> int:
    """Rough token estimate: 4 chars ≈ 1 token (GPT tokeniser heuristic)."""
    text = f"{record.entity} {record.relation} {record.value.v or ''} {record.source}"
    return max(1, len(text) // 4)


def _recency_score(timestamp_str: str) -> float:
    """Normalised recency: 1.0 = now, 0.0 = ≥1 year old."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        days_old = (datetime.now(UTC) - ts).days
        return max(0.0, 1.0 - days_old / 365.0)
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Lexical search (FTS5 / BM25)
# ---------------------------------------------------------------------------

def _lexical_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, float]:
    """Return {fact_id: normalised_bm25_score}. Returns {} on FTS unavailability."""
    fts_q = _fts_query(query)
    try:
        # SAVEPOINT protects the surrounding transaction on Postgres: a failed
        # FTS5 MATCH query aborts the psycopg2 transaction, making all subsequent
        # SQL on the same connection fail.  Rolling back to the savepoint restores
        # the connection to a usable state.  SAVEPOINT is a no-op cost on
        # SQLite/libsql, which also support the syntax.
        conn.execute("SAVEPOINT _fts_search")
        rows = conn.execute(
            """
            SELECT ff.fact_id, bm25(facts_fts) AS rank
            FROM facts_fts ff
            JOIN facts f ON f.id = ff.fact_id
            WHERE facts_fts MATCH ?
              AND f.scope = ?
              AND f.tenant_id = ?
              AND f.confidence >= ?
              AND (f.valid_until IS NULL OR f.valid_until > ?)
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, scope, tenant_id, min_confidence, now, k),
        ).fetchall()
        conn.execute("RELEASE SAVEPOINT _fts_search")
    except Exception as exc:
        logger.warning("FTS5 lexical search failed: %s", exc)
        with contextlib.suppress(Exception):  # nosec B110 — best-effort rollback
            conn.execute("ROLLBACK TO SAVEPOINT _fts_search")
        return _like_search(conn, query, scope, tenant_id, k, min_confidence, now)

    if not rows:
        return {}

    # bm25() returns negative values; less negative = more relevant.
    abs_scores = [(-row["rank"], row["fact_id"]) for row in rows]
    max_score = max(s for s, _ in abs_scores)
    if max_score <= 0:
        return {}
    return {fid: score / max_score for score, fid in abs_scores}


# ---------------------------------------------------------------------------
# Semantic (dense vector) search
# ---------------------------------------------------------------------------

def _semantic_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
) -> dict[str, float]:
    """Return {fact_id: cosine_similarity}. Returns {} when embed_enabled=False."""
    if not settings.embed_enabled:
        return {}
    try:
        from ..embedding import get_embedding_model
        from ..vector_search import vector_search

        model = get_embedding_model()
        vecs = model.embed([query])
        if not vecs:
            return {}
        results = vector_search(
            vecs[0], k=k, scope_filter=scope, tenant_id=tenant_id, conn=conn
        )
        return {record.id: float(sim) for record, sim in results}
    except Exception as exc:
        logger.warning("Semantic search failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Graph expansion
# ---------------------------------------------------------------------------

def _graph_expand(
    conn: Any,
    seed_fact_ids: list[str],
    depth: int,
    scope: str,
    tenant_id: str,
    identity: Identity,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, int]:
    """BFS-expand from top-seed entities; return {fact_id: min_hops}."""
    if not seed_fact_ids:
        return {}

    placeholders = ",".join("?" * len(seed_fact_ids))
    seed_rows = conn.execute(
        f"SELECT DISTINCT entity FROM facts WHERE id IN ({placeholders})",  # nosec B608
        seed_fact_ids,
    ).fetchall()

    seed_entities = [row["entity"] for row in seed_rows][: _MAX_SEED_ENTITIES]
    if not seed_entities:
        return {}

    entity_min_hops: dict[str, int] = {}
    for seed in seed_entities:
        neighbors = bfs_neighbors(
            conn,
            seed_entity=seed,
            max_depth=depth,
            scope=scope,
            tenant_id=tenant_id,
            identity=identity,
        )
        for n in neighbors:
            prev = entity_min_hops.get(n.entity)
            if prev is None or n.hops < prev:
                entity_min_hops[n.entity] = n.hops

    if not entity_min_hops:
        return {}

    entities = list(entity_min_hops.keys())[: _MAX_GRAPH_ENTITIES]
    placeholders = ",".join("?" * len(entities))
    fact_rows = conn.execute(
        f"""
        SELECT id, entity
        FROM facts
        WHERE entity IN ({placeholders})  -- nosec B608
          AND scope = ?
          AND tenant_id = ?
          AND confidence >= ?
          AND (valid_until IS NULL OR valid_until > ?)
        LIMIT ?
        """,  # nosec B608
        [*entities, scope, tenant_id, min_confidence, now, k],
    ).fetchall()

    return {
        row["id"]: entity_min_hops.get(row["entity"], depth)
        for row in fact_rows
    }


# ---------------------------------------------------------------------------
# Fact fetch helpers
# ---------------------------------------------------------------------------

def _fetch_facts_by_ids(
    conn: Any,
    fact_ids: list[str],
) -> dict[str, FactRecord]:
    """Bulk-fetch facts by ID; returns {id: FactRecord}."""
    if not fact_ids:
        return {}
    placeholders = ",".join("?" * len(fact_ids))
    rows = conn.execute(
        f"SELECT * FROM facts WHERE id IN ({placeholders})",  # nosec B608
        fact_ids,
    ).fetchall()
    return {row["id"]: row_to_record(row) for row in rows}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

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
        if settings.trust_mode != "off":
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


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def _write_recall_audit(
    conn: Any,
    recall_id: str,
    identity: Identity,
    query_hash: str,
    scope: str,
    token_budget: int,
    facts_returned: int,
    tokens_used: int,
    truncated: bool,
) -> None:
    now = _now_iso()
    try:
        conn.execute(
            """
            INSERT INTO recall_audit_log
              (id, entity_uri, query_hash, scope, token_budget,
               facts_returned, tokens_used, truncated, tenant_id, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recall_id,
                identity.entity_uri,
                query_hash,
                scope,
                token_budget,
                facts_returned,
                tokens_used,
                1 if truncated else 0,
                identity.tenant_id,
                now,
            ),
        )
    except Exception as exc:
        logger.error("Failed to write recall_audit_log: %s", exc)


# ---------------------------------------------------------------------------
# §24 Time-travel recall implementation
# ---------------------------------------------------------------------------

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
    from .facts import _get_tombstone_filter

    # Candidate fetch: facts visible at as_of
    rows = conn.execute(
        """
        SELECT f.*
        FROM facts f
        WHERE f.scope = ?
          AND f.tenant_id = ?
          AND f.timestamp <= ?
          AND (f.valid_until IS NULL OR f.valid_until > ?)
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
        if settings.trust_mode != "off":
            trust_s = compute_source_trust(record.source, record.scope, identity)
        raw = (
            weights.lexical * lex
            + weights.recency * rec_s
            + weights.source_trust * trust_s
        ) / total_weight
        final_score = raw * max(0.0, record.confidence)
        scored.append(ScoredFact(
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
        ))

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


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=RecallResponse)
def recall(
    req: RecallRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
    response: Response,
) -> RecallResponse:
    """Hybrid recall — return the most salient facts for a query, within budget.

    Combines lexical (FTS5/BM25), dense-vector, and graph-traversal signals.
    Honors §17 garden ACL and §19 source-trust at every step.
    """
    with start_span(
        "stigmem.recall",
        **{
            "stigmem.tenant": identity.tenant_id,
            "stigmem.principal": identity.entity_uri,
            "stigmem.scope": req.scope,
        },
    ) as _span:
        result = _recall_impl(req, identity, _span)
    if result.total_scored is not None:
        response.headers["X-Total-Count"] = str(result.total_scored)
    return result


def _recall_impl(
    req: RecallRequest,
    identity: Identity,
    _span: object,
) -> RecallResponse:
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="read permission required"
        )

    FACT_READ.labels(principal=identity.entity_uri, tenant=identity.tenant_id).inc()

    if req.scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid_scope: must be one of {sorted(VALID_SCOPES)}",
        )

    if req.depth > MAX_DEPTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "graph_depth_exceeded", "message": f"depth must be ≤ {MAX_DEPTH}"},
        )

    # §24 time-travel path
    if req.as_of is not None:
        from .facts import _validate_as_of
        _validate_as_of(req.as_of)
        is_admin = identity.is_admin()
        recall_id = str(uuid.uuid4())
        query_hash = hashlib.sha256(req.query.encode()).hexdigest()
        with db() as conn:
            packed, notices, tombstone_filtered = _recall_as_of_impl(
                conn,
                query=req.query,
                scope=req.scope,
                as_of=req.as_of,
                is_admin_caller=is_admin,
                tenant_id=identity.tenant_id,
                max_chunks=req.limit,
                include_graph=req.include_neighbors,
                identity=identity,
                weights=req.weights,
                depth=req.depth,
            )
        tokens_used = sum(sf.token_estimate for sf in packed)
        # §23.3.3 r.3: suppress total_scored when tombstone filtering was applied
        return RecallResponse(
            recall_id=recall_id,
            query_hash=query_hash,
            facts=packed,
            total_scored=None if tombstone_filtered else len(packed),
            token_budget=req.token_budget,
            tokens_used=tokens_used,
            truncated=False,
            tombstone_notices=notices,
        )

    recall_id = str(uuid.uuid4())
    query_hash = hashlib.sha256(req.query.encode()).hexdigest()
    now = _now_iso()

    logger.info(
        "recall id=%s entity=%s query_hash=%s scope=%s budget=%d",
        recall_id, identity.entity_uri, query_hash[:12], req.scope, req.token_budget,
    )

    with db() as conn:
        # --- Lexical ---
        lex_scores = (
            _lexical_search(
                conn, req.query, req.scope, identity.tenant_id,
                req.limit, req.min_confidence, now,
            )
            if req.weights.lexical > 0
            else {}
        )

        # --- Semantic ---
        sem_scores = (
            _semantic_search(
                conn, req.query, req.scope, identity.tenant_id, req.limit
            )
            if req.weights.semantic > 0
            else {}
        )

        # --- Merge direct-match candidates ---
        direct_ids = set(lex_scores) | set(sem_scores)

        # --- Graph expansion from top direct-match seeds ---
        graph_hops: dict[str, int] = {}
        if req.include_neighbors and req.weights.graph > 0 and direct_ids:
            top_seeds = sorted(
                direct_ids,
                key=lambda fid: lex_scores.get(fid, 0) + sem_scores.get(fid, 0),
                reverse=True,
            )
            top_seeds = top_seeds[: _MAX_SEED_ENTITIES]
            graph_hops = _graph_expand(
                conn, top_seeds, req.depth, req.scope, identity.tenant_id,
                identity, req.limit, req.min_confidence, now,
            )

        # Direct matches have hop_distance=0 (mark in graph_hops)
        for fid in direct_ids:
            if fid not in graph_hops:
                graph_hops[fid] = 0

        # --- Fetch all candidate facts ---
        all_candidate_ids = list(direct_ids | set(graph_hops.keys()))[:_MAX_CANDIDATES]
        all_facts_raw = _fetch_facts_by_ids(conn, all_candidate_ids)

        # §23.3.2 r.3: exclude facts whose entity has an active tombstone (about_entity).
        # Uses in-process cache (§23.3.3 r.4) — no per-fact DB read required.
        pre_tombstone_count = len(all_facts_raw)
        all_facts_raw = {
            k: v for k, v in all_facts_raw.items()
            if not _is_tombstoned(v.entity, identity.tenant_id)
        }
        tombstone_filtered = len(all_facts_raw) < pre_tombstone_count

        # --- Card fast-path (§20): for each candidate entity, check for a fresh card ---
        # Entities with a fresh, high-confidence, contradiction-free card skip raw-fact
        # re-ranking; their card becomes a single synthetic ScoredFact in the output.
        card_facts: list[ScoredFact] = []
        card_entity_ids: set[str] = set()  # fact IDs belonging to card-served entities
        try:
            candidate_entities: dict[str, list[str]] = {}  # entity -> [fact_ids]
            for fid, record in all_facts_raw.items():
                candidate_entities.setdefault(record.entity, []).append(fid)

            for entity_uri, entity_fact_ids in candidate_entities.items():
                # §23.3.2 r.3: cards whose about_entity is tombstoned are fully excluded.
                if _is_tombstoned(entity_uri, identity.tenant_id):
                    continue
                card = get_fresh_card(entity_uri, req.scope, identity.tenant_id, conn)
                if (
                    card is not None
                    and not card.is_stale
                    and not card.has_contradictions
                    and card.avg_confidence >= CARD_MIN_CONFIDENCE
                ):
                    # Build a synthetic FactRecord from the card summary
                    card_record = FactRecord(
                        id=f"card:{entity_uri}",
                        entity=entity_uri,
                        relation="stigmem:card:summary",
                        value=FactValue(type="text", v=card.summary),
                        source="system:stigmem:materializer",
                        timestamp=card.refreshed_at or now,
                        confidence=card.avg_confidence,
                        scope=req.scope,
                    )
                    card_facts.append(ScoredFact(
                        fact=card_record,
                        score=round(card.avg_confidence, 6),
                        score_breakdown=ScoreBreakdown(
                            source_trust=round(card.avg_confidence, 4),
                            weighted_total=round(card.avg_confidence, 6),
                        ),
                        hop_distance=0,
                        token_estimate=_estimate_tokens(card_record),
                        from_card=True,
                    ))
                    card_entity_ids.update(entity_fact_ids)
        except Exception as _card_exc:
            logger.warning("card fast-path error (falling through to raw facts): %s", _card_exc)
            card_facts = []
            card_entity_ids = set()

        # Exclude card-served facts from raw-fact scoring
        if card_entity_ids:
            all_facts_raw = {k: v for k, v in all_facts_raw.items() if k not in card_entity_ids}
            lex_scores = {k: v for k, v in lex_scores.items() if k not in card_entity_ids}
            sem_scores = {k: v for k, v in sem_scores.items() if k not in card_entity_ids}
            graph_hops = {k: v for k, v in graph_hops.items() if k not in card_entity_ids}

        # Apply §19 recall pipeline (source-trust multiplier + content sanitiser)
        pipeline_out = apply_recall_pipeline(list(all_facts_raw.values()), identity)
        all_facts = {r.id: r for r in pipeline_out}

        # --- Score (timed for ranker histogram) ---
        with observe_duration(RECALL_RANKER_DURATION, {"tenant": identity.tenant_id}):
            candidates = _score_candidates(
                all_facts, lex_scores, sem_scores, graph_hops,
                req.weights, identity, req.depth,
            )

        # Merge card-derived facts with raw-fact candidates
        candidates.extend(card_facts)

        total_scored = len(candidates)

        # --- Token-budget packing ---
        packed, tokens_used, truncated = _greedy_pack(candidates, req.token_budget)

        # --- Audit ---
        _write_recall_audit(
            conn, recall_id, identity, query_hash, req.scope,
            req.token_budget, len(packed), tokens_used, truncated,
        )

    logger.info(
        "recall id=%s scored=%d packed=%d tokens=%d truncated=%s",
        recall_id, total_scored, len(packed), tokens_used, truncated,
    )

    try:
        _span.set_attribute("stigmem.recall_id", recall_id)  # type: ignore[attr-defined]
        _span.set_attribute("stigmem.total_scored", total_scored)  # type: ignore[attr-defined]
        _span.set_attribute("stigmem.tokens_used", tokens_used)  # type: ignore[attr-defined]
        _span.set_attribute("stigmem.truncated", truncated)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001  # nosec B110 — span attrs best-effort
        logger.debug("recall span attribute set failed: %s", exc)

    # §23.3.3 r.3: suppress total_scored when tombstone filtering was applied
    return RecallResponse(
        recall_id=recall_id,
        query_hash=query_hash,
        facts=packed,
        total_scored=None if tombstone_filtered else total_scored,
        token_budget=req.token_budget,
        tokens_used=tokens_used,
        truncated=truncated,
    )
