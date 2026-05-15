"""Graph route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NeighborItem(BaseModel):
    entity: str
    relation: str
    hops: int
    confidence: float
    source_trust: float | None = None
    path: list[str] = Field(default_factory=list)


class NeighborsResponse(BaseModel):
    entity: str
    depth: int
    neighbors: list[NeighborItem]
    next_cursor: str | None = None
    total_hint: int
