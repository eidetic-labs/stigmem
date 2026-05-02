"""Pydantic models for the Muninn v0.3 fact model."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel, Field, field_validator

VALID_VALUE_TYPES = {"string", "text", "number", "boolean", "datetime", "ref", "null"}
VALID_SCOPES = {"local", "team", "company", "public"}


class FactValue(BaseModel):
    type: str
    v: Any = None

    @field_validator("type")
    @classmethod
    def check_type(cls, t: str) -> str:
        if t not in VALID_VALUE_TYPES:
            raise ValueError(f"type must be one of {VALID_VALUE_TYPES}")
        return t


class AssertRequest(BaseModel):
    entity: str = Field(..., min_length=1)
    relation: str = Field(..., min_length=1)
    value: FactValue
    source: str = Field(..., min_length=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    scope: str = Field("local")
    valid_until: str | None = Field(None, description="ISO 8601 UTC expiry; null = non-expiring")

    @field_validator("scope")
    @classmethod
    def check_scope(cls, s: str) -> str:
        if s not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return s


class FactRecord(BaseModel):
    id: str
    entity: str
    relation: str
    value: FactValue
    source: str
    timestamp: str
    valid_until: str | None = None
    confidence: float
    scope: str
    contradicted: bool = False


class QueryResponse(BaseModel):
    facts: list[FactRecord]
    total: int
    cursor: str | None


def row_to_record(row: sqlite3.Row, contradicted: bool = False) -> FactRecord:
    return FactRecord(
        id=row["id"],
        entity=row["entity"],
        relation=row["relation"],
        value=FactValue(type=row["value_type"], v=_parse_v(row["value_type"], row["value_v"])),
        source=row["source"],
        timestamp=row["timestamp"],
        valid_until=row["valid_until"],
        confidence=row["confidence"],
        scope=row["scope"],
        contradicted=contradicted,
    )


def _parse_v(vtype: str, raw: str) -> Any:
    if vtype == "number":
        return float(raw)
    if vtype == "boolean":
        return raw == "true"
    if vtype == "null":
        return None
    return raw  # string, text, datetime, ref
