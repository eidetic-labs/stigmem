"""Lazy instruction discovery route wire-format models."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class LoadTriggers(BaseModel):
    intents: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    task_types: list[str] = Field(default_factory=list)


class ManifestEntry(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., max_length=120)
    required_by_task_types: list[str] = Field(default_factory=list)
    guarantee_load: bool = False
    force_position: str | None = None
    load_triggers: LoadTriggers = Field(default_factory=LoadTriggers)
    fact_uri: str | None = None
    path: str | None = None
    token_estimate: int | None = None

    @field_validator("name")
    @classmethod
    def no_spaces_in_name(cls, v: str) -> str:
        if re.search(r"\s", v):
            raise ValueError("name must not contain whitespace")
        return v


class PublishManifestRequest(BaseModel):
    version: str = Field(..., min_length=1)
    entries: list[ManifestEntry]
    skip_coverage_gate: bool = False


class RecallInstructionRequest(BaseModel):
    intent: str = Field(..., min_length=1)
    max_chunks: int = Field(3, ge=1, le=20)
    token_budget: int = Field(2000, ge=1, le=100_000)
    manifest_hint: list[str] = Field(default_factory=list)


class AuditSubmitRequest(BaseModel):
    audit_token: str = Field(..., min_length=1)
    used_chunks: list[str] = Field(default_factory=list)
    missed_chunks: list[str] = Field(default_factory=list)
