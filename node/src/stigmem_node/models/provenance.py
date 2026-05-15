"""Fact provenance models."""

from __future__ import annotations

from pydantic import BaseModel


class ProvenanceEntry(BaseModel):
    """One entry in a fact's derived_from chain.

    exists=False means the referenced entity is tombstoned or the fact is otherwise
    inaccessible. Shape is identical in both cases so
    callers cannot distinguish tombstone from unauthorized.
    """

    hash: str
    fact_id: str | None = None
    entity: str | None = None
    exists: bool


class ProvenanceResponse(BaseModel):
    """Response for GET /v1/facts/:id/provenance."""

    fact_id: str
    cid: str | None = None
    derived_from: list[ProvenanceEntry]

