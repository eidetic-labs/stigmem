"""Entity alias route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel


class AliasRequest(BaseModel):
    raw_uri: str
    canonical_uri: str


class AliasRecord(BaseModel):
    raw_uri: str
    canonical_uri: str
    kind: str
    created_at: str
