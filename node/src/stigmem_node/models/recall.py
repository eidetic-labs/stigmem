"""Recall route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .facts import FactRecord
from .tombstones import TombstoneNotice

_DEFAULT_WEIGHTS = {
    "lexical": 0.35,
    "semantic": 0.35,
    "graph": 0.15,
    "source_trust": 0.10,
    "recency": 0.05,
}


class RecallWeights(BaseModel):
    lexical: float = Field(_DEFAULT_WEIGHTS["lexical"], ge=0.0, le=1.0)
    semantic: float = Field(_DEFAULT_WEIGHTS["semantic"], ge=0.0, le=1.0)
    graph: float = Field(_DEFAULT_WEIGHTS["graph"], ge=0.0, le=1.0)
    source_trust: float = Field(_DEFAULT_WEIGHTS["source_trust"], ge=0.0, le=1.0)
    recency: float = Field(_DEFAULT_WEIGHTS["recency"], ge=0.0, le=1.0)


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
        description="Time-travel query: return facts visible at this ISO 8601 timestamp (Spec-X3-Time-Travel-Queries)",  # noqa: E501
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
    content: list[ScoredFact] = Field(default_factory=list)
    instructions: list[ScoredFact] = Field(default_factory=list)
    total_scored: int | None = None
    token_budget: int
    tokens_used: int
    truncated: bool
    tombstone_notices: list[TombstoneNotice] = Field(default_factory=list)
