"""Lint route — spec §5.12 (Phase 5).

POST /v1/lint
{ scope, checks?, entity?, relation?, stale_lookahead_s? }

Read-only health-check sweep: contradiction detection, stale-fact flagging,
orphan-entity detection, broken cross-reference detection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Identity, resolve_identity
from ..db import db
from ..models import VALID_SCOPES

router = APIRouter(tags=["lint"])

LintCheck = Literal["contradiction", "stale", "orphan", "broken_ref"]
ALL_CHECKS: list[LintCheck] = ["contradiction", "stale", "orphan", "broken_ref"]


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


@router.post("/v1/lint", response_model=LintResult)
def lint_scope(
    req: LintRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> LintResult:
    """Health-check sweep for a scope (spec §5.12). Read-only."""
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")

    if req.scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")

    checks_to_run: list[LintCheck] = req.checks if req.checks else ALL_CHECKS
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    lookahead_dt = now_dt + timedelta(seconds=req.stale_lookahead_s)
    lookahead = lookahead_dt.isoformat()

    # Clauses using alias "f" (for simple facts queries)
    f_scope = "AND f.scope = ?"
    f_entity = ("AND f.entity = ?" if req.entity else "")
    f_relation = ("AND f.relation = ?" if req.relation else "")
    f_filter = f_scope + f_entity + f_relation
    f_params: list[Any] = [req.scope] + ([req.entity] if req.entity else []) + ([req.relation] if req.relation else [])

    # Clauses using alias "fa" (for conflict join queries)
    fa_scope = "AND fa.scope = ?"
    fa_entity = ("AND fa.entity = ?" if req.entity else "")
    fa_relation = ("AND fa.relation = ?" if req.relation else "")
    fa_filter = fa_scope + fa_entity + fa_relation
    fa_params: list[Any] = [req.scope] + ([req.entity] if req.entity else []) + ([req.relation] if req.relation else [])

    findings: list[LintFinding] = []
    fact_count = 0

    with db() as conn:
        # Total facts checked
        count_sql = f"SELECT COUNT(*) FROM facts f WHERE 1=1 {f_filter}"
        fact_count = conn.execute(count_sql, f_params).fetchone()[0]

        # 1. Unresolved contradictions
        if "contradiction" in checks_to_run:
            conflict_sql = f"""
                SELECT c.id AS conflict_id, c.fact_a_id, c.fact_b_id,
                       fa.entity, fa.relation
                FROM conflicts c
                JOIN facts fa ON fa.id = c.fact_a_id
                JOIN facts fb ON fb.id = c.fact_b_id
                WHERE c.status = 'unresolved'
                {fa_filter}
            """
            for row in conn.execute(conflict_sql, fa_params).fetchall():
                findings.append(LintFinding(
                    check="contradiction",
                    severity="error",
                    entity=row["entity"],
                    relation=row["relation"],
                    fact_ids=[row["fact_a_id"], row["fact_b_id"]],
                    detail=f"unresolved conflict {row['conflict_id']}",
                ))

        # 2. Stale facts (past valid_until, or expiring within lookahead_s)
        if "stale" in checks_to_run:
            stale_sql = f"""
                SELECT f.id, f.entity, f.relation, f.valid_until
                FROM facts f
                WHERE f.valid_until IS NOT NULL
                AND f.valid_until <= ?
                {f_filter}
            """
            stale_params: list[Any] = [lookahead] + f_params
            for row in conn.execute(stale_sql, stale_params).fetchall():
                expired = row["valid_until"] <= now
                severity = "warning" if expired else "info"
                detail = (
                    f"expired at {row['valid_until']}"
                    if expired
                    else f"expires at {row['valid_until']} (within {req.stale_lookahead_s}s)"
                )
                findings.append(LintFinding(
                    check="stale",
                    severity=severity,
                    entity=row["entity"],
                    relation=row["relation"],
                    fact_ids=[row["id"]],
                    detail=detail,
                ))

        # 3. Orphan entities: source URIs that never appear as entity in scope
        if "orphan" in checks_to_run and not req.entity and not req.relation:
            orphan_sql = """
                SELECT DISTINCT f.source
                FROM facts f
                WHERE f.scope = ?
                AND f.source NOT IN (
                    SELECT DISTINCT entity FROM facts WHERE scope = ?
                )
            """
            for row in conn.execute(orphan_sql, [req.scope, req.scope]).fetchall():
                findings.append(LintFinding(
                    check="orphan",
                    severity="info",
                    entity=row["source"],
                    relation=None,
                    fact_ids=[],
                    detail=f"source URI {row['source']!r} has no facts as entity in scope={req.scope}",
                ))

        # 4. Broken cross-references: ref values pointing to non-existent fact IDs
        if "broken_ref" in checks_to_run:
            ref_sql = f"""
                SELECT f.id, f.entity, f.relation, f.value_v
                FROM facts f
                WHERE f.value_type = 'ref'
                AND f.value_v NOT IN (SELECT id FROM facts)
                {f_filter}
            """
            for row in conn.execute(ref_sql, f_params).fetchall():
                findings.append(LintFinding(
                    check="broken_ref",
                    severity="warning",
                    entity=row["entity"],
                    relation=row["relation"],
                    fact_ids=[row["id"]],
                    detail=f"ref value {row['value_v']!r} not found in facts table",
                ))

    return LintResult(
        findings=findings,
        checked_at=now,
        scope=req.scope,
        checks_run=checks_to_run,
        fact_count=fact_count,
    )
