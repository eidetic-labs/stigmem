"""Memory card route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel


class MemoryCardResponse(BaseModel):
    entity_uri: str
    scope: str
    summary: str
    fact_hashes: list[str]
    avg_confidence: float
    refreshed_at: str | None
    is_stale: bool
    has_contradictions: bool
