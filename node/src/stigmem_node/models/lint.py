"""Lint route wire-format models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LintCheck = Literal["contradiction", "stale", "orphan", "broken_ref", "namespacing"]
ALL_CHECKS: list[LintCheck] = ["contradiction", "stale", "orphan", "broken_ref", "namespacing"]


class LintRequest(BaseModel):
    scope: str = Field(..., description="Fact scope to sweep")
    checks: list[LintCheck] | None = Field(None, description="Checks to run; omit for all")
    entity: str | None = Field(None, description="Restrict to a specific entity URI")
    relation: str | None = Field(None, description="Restrict to a specific relation")
    stale_lookahead_s: int = Field(0, ge=0, description="Also flag facts expiring within N seconds")


class LintFinding(BaseModel):
    check: LintCheck
    severity: Literal["error", "warning", "info"]
    entity: str
    relation: str | None
    fact_ids: list[str]
    detail: str


class LintResult(BaseModel):
    findings: list[LintFinding]
    checked_at: str
    scope: str
    checks_run: list[LintCheck]
    fact_count: int
