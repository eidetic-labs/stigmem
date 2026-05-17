"""Stigmem data models — spec v0.4/v0.5 fact model."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# FactValue
# ---------------------------------------------------------------------------

class StringValue(BaseModel):
    type: Literal["string"]
    v: str


class TextValue(BaseModel):
    type: Literal["text"]
    v: str


class NumberValue(BaseModel):
    type: Literal["number"]
    v: float


class BooleanValue(BaseModel):
    type: Literal["boolean"]
    v: bool


class DatetimeValue(BaseModel):
    type: Literal["datetime"]
    v: str  # ISO 8601


class RefValue(BaseModel):
    type: Literal["ref"]
    v: str  # URI


class NullValue(BaseModel):
    type: Literal["null"]

FactValue = (
    StringValue
    | TextValue
    | NumberValue
    | BooleanValue
    | DatetimeValue
    | RefValue
    | NullValue
)

FactScope = Literal["local", "team", "company", "public"]


def string_value(v: str) -> StringValue:
    return StringValue(type="string", v=v)


def text_value(v: str) -> TextValue:
    return TextValue(type="text", v=v)


def number_value(v: float) -> NumberValue:
    return NumberValue(type="number", v=v)


def boolean_value(v: bool) -> BooleanValue:
    return BooleanValue(type="boolean", v=v)


def datetime_value(v: str) -> DatetimeValue:
    return DatetimeValue(type="datetime", v=v)


def ref_value(v: str) -> RefValue:
    return RefValue(type="ref", v=v)


def null_value() -> NullValue:
    return NullValue(type="null")


# ---------------------------------------------------------------------------
# Fact
# ---------------------------------------------------------------------------

class Fact(BaseModel):
    id: str
    entity: str
    relation: str
    value: FactValue
    source: str
    timestamp: str
    hlc: str | None = None
    valid_until: str | None = None
    confidence: float
    scope: FactScope
    contradicted: bool = False
    received_from: str | None = None

    model_config = {"extra": "allow"}


class FactPage(BaseModel):
    facts: list[Fact]
    total: int
    cursor: str | None = None


# ---------------------------------------------------------------------------
# Peer / Federation
# ---------------------------------------------------------------------------

PeerStatus = Literal["pending_verification", "active", "rejected", "revoked"]


class Peer(BaseModel):
    peer_id: str
    node_id: str
    node_url: str
    status: PeerStatus
    allowed_scopes: list[FactScope]
    established_at: str | None = None

    model_config = {"extra": "allow"}


class PeerPage(BaseModel):
    peers: list[Peer]


# ---------------------------------------------------------------------------
# Node info (/.well-known/stigmem)
# ---------------------------------------------------------------------------

class FederationEndpoints(BaseModel):
    peers: str
    facts: str
    push: str | None = None


class NodeInfo(BaseModel):
    version: str
    node_id: str
    node_url: str
    auth: Literal["none", "required"]
    federation: Literal["disabled", "enabled"]
    federation_pubkey: str | None = None
    federation_version: str | None = None
    federation_endpoints: FederationEndpoints | None = None
    namespaces: list[str] = Field(default_factory=list)
    spec: str | None = None

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

ConflictStatus = Literal["unresolved", "resolved"]


class Conflict(BaseModel):
    conflict_id: str
    fact_a: Fact
    fact_b: Fact
    status: ConflictStatus
    resolved_by: str | None = None
    detected_at: str

    model_config = {"extra": "allow"}


class ConflictPage(BaseModel):
    conflicts: list[Conflict]
    cursor: str | None = None
    has_more: bool = False


class ConflictResolution(BaseModel):
    resolution_fact_id: str
    conflict_status: Literal["resolved"]

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Assert / Query request shapes (convenience)
# ---------------------------------------------------------------------------

class AssertRequest(BaseModel):
    entity: str
    relation: str
    value: FactValue
    source: str
    confidence: float = 1.0
    scope: FactScope = "company"
    valid_until: str | None = None
    write_mode: str = "assert"
    derived_from: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class ResolveRequest(BaseModel):
    winning_fact_id: str | None = None
    resolution_note: str = ""
    new_value: FactValue | None = None

    def model_dump_api(self) -> dict[str, Any]:
        d: dict[str, Any] = {"resolution_note": self.resolution_note}
        if self.winning_fact_id is not None:
            d["winning_fact_id"] = self.winning_fact_id
        if self.new_value is not None:
            d["new_value"] = self.new_value.model_dump()
        return d


# ---------------------------------------------------------------------------
# Recall (Phase 9 — spec §20)
# ---------------------------------------------------------------------------

class RecallWeights(BaseModel):
    """Per-signal weights for the hybrid ranker."""

    lexical: float = 0.35
    semantic: float = 0.35
    graph: float = 0.15
    source_trust: float = 0.10
    recency: float = 0.05

    model_config = {"extra": "allow"}


class RecallRequest(BaseModel):
    query: str
    scope: FactScope = "local"
    token_budget: int = 4000
    depth: int = 2
    weights: RecallWeights = Field(default_factory=RecallWeights)
    min_confidence: float = 0.1
    include_neighbors: bool = True
    limit: int = 100

    model_config = {"extra": "allow"}


class ScoreBreakdown(BaseModel):
    lexical: float = 0.0
    semantic: float = 0.0
    graph: float = 0.0
    source_trust: float = 0.0
    recency: float = 0.0
    weighted_total: float = 0.0

    model_config = {"extra": "allow"}


class ScoredFact(BaseModel):
    fact: Fact
    score: float
    score_breakdown: ScoreBreakdown
    hop_distance: int = 0
    token_estimate: int

    model_config = {"extra": "allow"}


class RecallResponse(BaseModel):
    recall_id: str
    query_hash: str
    facts: list[ScoredFact]
    content: list[ScoredFact] = Field(default_factory=list)
    instructions: list[ScoredFact] = Field(default_factory=list)
    total_scored: int | None
    token_budget: int
    tokens_used: int
    truncated: bool

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Memory cards (Phase 9 — spec §20)
# ---------------------------------------------------------------------------

class MemoryCard(BaseModel):
    """Per-entity synthesized summary card (spec §20)."""

    entity_uri: str
    scope: str
    summary: str
    fact_hashes: list[str]
    avg_confidence: float
    refreshed_at: str | None = None
    is_stale: bool = False
    has_contradictions: bool = False

    model_config = {"extra": "allow"}
