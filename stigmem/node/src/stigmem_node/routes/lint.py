"""Lint route — spec §14 (v0.7).

POST /v1/lint
{ scope, checks?, entity?, relation?, stale_lookahead_s? }

Read-only health-check sweep: contradiction detection, stale-fact flagging,
orphan-entity detection (all-retracted entities), broken cross-reference detection.
Never writes or modifies any facts.
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

LintCheck = Literal["contradiction", "stale", "orphan", "broken_ref", "namespacing"]
ALL_CHECKS: list[LintCheck] = ["contradiction", "stale", "orphan", "broken_ref", "namespacing"]

# Relations where a broken ref is severity=error (spec §14.3)
INTENT_ROUTING_RELATIONS = frozenset({"intent:handoff_to", "intent:context_ref"})


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
    """Health-check sweep for a scope (spec §14). Read-only."""
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
        #    Only flag live facts (confidence > 0.0); retracted facts are not stale.
        if "stale" in checks_to_run:
            stale_sql = f"""
                SELECT f.id, f.entity, f.relation, f.valid_until
                FROM facts f
                WHERE f.valid_until IS NOT NULL
                AND f.confidence > 0.0
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

        # 3. Orphan entities (spec §14.1): entities where ALL facts in scope are either
        #    retracted (confidence=0.0) or expired (valid_until < now). No live facts remain.
        if "orphan" in checks_to_run:
            orphan_clauses = "AND scope = ?"
            orphan_params: list[Any] = [req.scope]
            if req.entity:
                orphan_clauses += " AND entity = ?"
                orphan_params.append(req.entity)

            orphan_sql = f"""
                SELECT entity
                FROM facts
                WHERE 1=1 {orphan_clauses}
                GROUP BY entity
                HAVING COUNT(*) > 0
                   AND SUM(
                       CASE
                         WHEN confidence > 0.0
                          AND (valid_until IS NULL OR valid_until > ?)
                         THEN 1 ELSE 0
                       END
                   ) = 0
            """
            for row in conn.execute(orphan_sql, orphan_params + [now]).fetchall():
                findings.append(LintFinding(
                    check="orphan",
                    severity="info",
                    entity=row["entity"],
                    relation=None,
                    fact_ids=[],
                    detail=f"entity {row['entity']!r} has no live facts in scope={req.scope}",
                ))

        # 4. Broken cross-references (spec §14.1): ref facts whose target entity URI
        #    has no live (non-retracted, non-expired) facts in this node's store.
        #    Severity: error if relation is intent:handoff_to or intent:context_ref (spec §14.3);
        #              warning otherwise.
        if "broken_ref" in checks_to_run:
            ref_sql = f"""
                SELECT f.id, f.entity, f.relation, f.value_v
                FROM facts f
                WHERE f.value_type = 'ref'
                  AND f.confidence > 0.0
                  AND (f.valid_until IS NULL OR f.valid_until > ?)
                  {f_filter}
            """
            for row in conn.execute(ref_sql, [now] + f_params).fetchall():
                target_entity = row["value_v"]
                live_count = conn.execute(
                    """SELECT COUNT(*) FROM facts
                       WHERE entity = ?
                         AND confidence > 0.0
                         AND (valid_until IS NULL OR valid_until > ?)""",
                    [target_entity, now],
                ).fetchone()[0]
                if live_count == 0:
                    is_intent_routing = row["relation"] in INTENT_ROUTING_RELATIONS
                    findings.append(LintFinding(
                        check="broken_ref",
                        severity="error" if is_intent_routing else "warning",
                        entity=row["entity"],
                        relation=row["relation"],
                        fact_ids=[row["id"]],
                        detail=f"ref target entity {target_entity!r} has no live facts",
                    ))

        # 5. Namespacing violations (relation-convention.md): live facts whose relation
        #    contains no colon separator — bare words like "status" silently collide when
        #    multiple sources write semantically distinct facts.
        if "namespacing" in checks_to_run:
            ns_sql = f"""
                SELECT f.entity, f.relation, GROUP_CONCAT(f.id) AS ids
                FROM facts f
                WHERE f.confidence > 0.0
                  AND (f.valid_until IS NULL OR f.valid_until > ?)
                  AND instr(f.relation, ':') = 0
                  {f_filter}
                GROUP BY f.entity, f.relation
            """
            for row in conn.execute(ns_sql, [now] + f_params).fetchall():
                findings.append(LintFinding(
                    check="namespacing",
                    severity="warning",
                    entity=row["entity"],
                    relation=row["relation"],
                    fact_ids=row["ids"].split(",") if row["ids"] else [],
                    detail=(
                        f"bare relation {row['relation']!r} has no namespace prefix — "
                        f"rename to 'your-prefix:{row['relation']}' to avoid silent collisions"
                    ),
                ))

    return LintResult(
        findings=findings,
        checked_at=now,
        scope=req.scope,
        checks_run=checks_to_run,
        fact_count=fact_count,
    )
