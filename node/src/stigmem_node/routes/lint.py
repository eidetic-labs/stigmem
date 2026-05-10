"""Lint route — spec §14 (v0.7) + async job path (spec §14.5).

POST /v1/lint
{ scope, checks?, entity?, relation?, stale_lookahead_s? }
  → 200 sync result, or 202 { job_id, status, estimated_s } when scope > threshold.

GET /v1/lint/jobs/:job_id
  → 200 job status/result, or 404 if not found.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..auth import Identity, resolve_identity
from ..db import db
from ..jobs import create_job, get_job, mark_done, mark_failed, mark_running
from ..models import VALID_SCOPES
from ..settings import settings

router = APIRouter(tags=["lint"])

LintCheck = Literal["contradiction", "stale", "orphan", "broken_ref", "namespacing"]
ALL_CHECKS: list[LintCheck] = ["contradiction", "stale", "orphan", "broken_ref", "namespacing"]

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


def _build_lint_filters(
    scope: str, entity: str | None, relation: str | None
) -> tuple[str, list[Any], str, list[Any]]:
    """Build the (f.*) and (fa.*) WHERE-fragment + params for the lint queries."""
    f_scope = "AND f.scope = ?"
    f_entity = ("AND f.entity = ?" if entity else "")
    f_relation = ("AND f.relation = ?" if relation else "")
    f_filter = f_scope + f_entity + f_relation
    f_params: list[Any] = (
        [scope] + ([entity] if entity else []) + ([relation] if relation else [])
    )

    fa_scope = "AND fa.scope = ?"
    fa_entity = ("AND fa.entity = ?" if entity else "")
    fa_relation = ("AND fa.relation = ?" if relation else "")
    fa_filter = fa_scope + fa_entity + fa_relation
    fa_params: list[Any] = (
        [scope] + ([entity] if entity else []) + ([relation] if relation else [])
    )

    return f_filter, f_params, fa_filter, fa_params


def _check_contradictions(
    conn: Any, fa_filter: str, fa_params: list[Any]
) -> list[dict[str, Any]]:
    """Return contradiction findings for unresolved conflicts in the filtered scope."""
    findings: list[dict[str, Any]] = []
    conflict_sql = (
        "SELECT c.id AS conflict_id, c.fact_a_id, c.fact_b_id, fa.entity, fa.relation"
        " FROM conflicts c"
        " JOIN facts fa ON fa.id = c.fact_a_id"
        " JOIN facts fb ON fb.id = c.fact_b_id"
        f" WHERE c.status = 'unresolved' {fa_filter}"  # nosec B608 — fa_filter built from literal SQL fragments; values in params
    )
    for row in conn.execute(conflict_sql, fa_params).fetchall():
        findings.append({
            "check": "contradiction",
            "severity": "error",
            "entity": row["entity"],
            "relation": row["relation"],
            "fact_ids": [row["fact_a_id"], row["fact_b_id"]],
            "detail": f"unresolved conflict {row['conflict_id']}",
        })
    return findings


def _check_stale(
    conn: Any,
    f_filter: str,
    f_params: list[Any],
    now: str,
    lookahead: str,
    stale_lookahead_s: int,
) -> list[dict[str, Any]]:
    """Return stale (already-expired or expiring-soon) findings."""
    findings: list[dict[str, Any]] = []
    stale_sql = (
        "SELECT f.id, f.entity, f.relation, f.valid_until"
        " FROM facts f"
        " WHERE f.valid_until IS NOT NULL"
        " AND f.confidence > 0.0"
        " AND f.valid_until <= ?"
        f" {f_filter}"  # nosec B608 — f_filter built from literal SQL fragments; values in params
    )
    for row in conn.execute(stale_sql, [lookahead] + f_params).fetchall():
        expired = row["valid_until"] <= now
        findings.append({
            "check": "stale",
            "severity": "warning" if expired else "info",
            "entity": row["entity"],
            "relation": row["relation"],
            "fact_ids": [row["id"]],
            "detail": (
                f"expired at {row['valid_until']}"
                if expired
                else f"expires at {row['valid_until']} (within {stale_lookahead_s}s)"
            ),
        })
    return findings


def _check_orphans(
    conn: Any, scope: str, entity: str | None, now: str
) -> list[dict[str, Any]]:
    """Return orphan-entity findings (entities with no live facts in scope)."""
    findings: list[dict[str, Any]] = []
    orphan_clauses = "AND scope = ?"
    orphan_params: list[Any] = [scope]
    if entity:
        orphan_clauses += " AND entity = ?"
        orphan_params.append(entity)

    orphan_sql = (
        "SELECT entity FROM facts"
        f" WHERE 1=1 {orphan_clauses}"  # nosec B608 — orphan_clauses built from literal SQL fragments; values in params
        " GROUP BY entity"
        " HAVING COUNT(*) > 0"
        " AND SUM(CASE WHEN confidence > 0.0"
        " AND (valid_until IS NULL OR valid_until > ?) THEN 1 ELSE 0 END) = 0"
    )
    for row in conn.execute(orphan_sql, orphan_params + [now]).fetchall():
        findings.append({
            "check": "orphan",
            "severity": "info",
            "entity": row["entity"],
            "relation": None,
            "fact_ids": [],
            "detail": f"entity {row['entity']!r} has no live facts in scope={scope}",
        })
    return findings


def _check_broken_refs(
    conn: Any, f_filter: str, f_params: list[Any], now: str
) -> list[dict[str, Any]]:
    """Return broken-ref findings for value-type=ref facts whose target has no live facts."""
    findings: list[dict[str, Any]] = []
    ref_sql = (
        "SELECT f.id, f.entity, f.relation, f.value_v"
        " FROM facts f"
        " WHERE f.value_type = 'ref'"
        " AND f.confidence > 0.0"
        " AND (f.valid_until IS NULL OR f.valid_until > ?)"
        f" {f_filter}"  # nosec B608 — f_filter built from literal SQL fragments; values in params
    )
    for row in conn.execute(ref_sql, [now] + f_params).fetchall():
        target_entity = row["value_v"]
        live_count = conn.execute(
            "SELECT COUNT(*) FROM facts"
            " WHERE entity = ? AND confidence > 0.0"
            " AND (valid_until IS NULL OR valid_until > ?)",
            [target_entity, now],
        ).fetchone()[0]
        if live_count == 0:
            is_intent = row["relation"] in INTENT_ROUTING_RELATIONS
            findings.append({
                "check": "broken_ref",
                "severity": "error" if is_intent else "warning",
                "entity": row["entity"],
                "relation": row["relation"],
                "fact_ids": [row["id"]],
                "detail": f"ref target entity {target_entity!r} has no live facts",
            })
    return findings


def _check_namespacing(
    conn: Any, f_filter: str, f_params: list[Any], now: str
) -> list[dict[str, Any]]:
    """Return namespacing findings for live facts whose relation lacks a 'prefix:' namespace."""
    findings: list[dict[str, Any]] = []
    ns_sql = (
        "SELECT f.entity, f.relation, GROUP_CONCAT(f.id) AS ids"
        " FROM facts f"
        " WHERE f.confidence > 0.0"
        " AND (f.valid_until IS NULL OR f.valid_until > ?)"
        " AND instr(f.relation, ':') = 0"
        f" {f_filter}"  # nosec B608 — f_filter built from literal SQL fragments; values in params
        " GROUP BY f.entity, f.relation"
    )
    for row in conn.execute(ns_sql, [now] + f_params).fetchall():
        findings.append({
            "check": "namespacing",
            "severity": "warning",
            "entity": row["entity"],
            "relation": row["relation"],
            "fact_ids": row["ids"].split(",") if row["ids"] else [],
            "detail": (
                f"bare relation {row['relation']!r} has no namespace prefix — "
                f"rename to 'your-prefix:{row['relation']}' to avoid silent collisions"
            ),
        })
    return findings


def _run_lint_sweep(
    scope: str,
    checks: list[LintCheck],
    entity: str | None,
    relation: str | None,
    stale_lookahead_s: int,
) -> dict[str, Any]:
    """Execute the lint sweep and return a dict matching LintResult fields."""
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    lookahead = (now_dt + timedelta(seconds=stale_lookahead_s)).isoformat()

    f_filter, f_params, fa_filter, fa_params = _build_lint_filters(scope, entity, relation)

    findings: list[dict[str, Any]] = []
    fact_count = 0

    with db() as conn:
        count_sql = f"SELECT COUNT(*) FROM facts f WHERE 1=1 {f_filter}"  # nosec B608 — f_filter is built from literal SQL fragments; values in params
        fact_count = conn.execute(count_sql, f_params).fetchone()[0]

        if "contradiction" in checks:
            findings.extend(_check_contradictions(conn, fa_filter, fa_params))

        if "stale" in checks:
            findings.extend(
                _check_stale(conn, f_filter, f_params, now, lookahead, stale_lookahead_s)
            )

        if "orphan" in checks:
            findings.extend(_check_orphans(conn, scope, entity, now))

        if "broken_ref" in checks:
            findings.extend(_check_broken_refs(conn, f_filter, f_params, now))

        if "namespacing" in checks:
            findings.extend(_check_namespacing(conn, f_filter, f_params, now))

    return {
        "findings": findings,
        "checked_at": now,
        "scope": scope,
        "checks_run": checks,
        "fact_count": fact_count,
    }


def _lint_job_worker(job_id: str, req: LintRequest) -> None:
    """Background task: run lint sweep and update job status."""
    mark_running(job_id)
    try:
        result = _run_lint_sweep(
            scope=req.scope,
            checks=req.checks or ALL_CHECKS,
            entity=req.entity,
            relation=req.relation,
            stale_lookahead_s=req.stale_lookahead_s,
        )
        mark_done(job_id, result)
    except Exception as exc:
        mark_failed(job_id, str(exc))


@router.post("/v1/lint")
def lint_scope(
    req: LintRequest,
    background_tasks: BackgroundTasks,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> Any:
    """Health-check sweep for a scope (spec §14). Read-only.

    Returns 200 with results synchronously for scopes ≤ threshold facts.
    Returns 202 with job_id for larger scopes; poll GET /v1/lint/jobs/:job_id.
    """
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")
    if req.scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")

    checks_to_run: list[LintCheck] = req.checks if req.checks else ALL_CHECKS

    # Count scope facts to choose sync vs. async path (spec §14.5).
    with db() as conn:
        scope_count: int = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE scope = ?", [req.scope]
        ).fetchone()[0]

    if scope_count > settings.async_job_threshold:
        estimated_s = max(10, scope_count // 5_000)
        job_id = create_job("lint", req.scope, estimated_s)
        background_tasks.add_task(_lint_job_worker, job_id, req)
        return JSONResponse(
            status_code=202,
            content={"job_id": job_id, "status": "pending", "estimated_s": estimated_s},
        )

    result = _run_lint_sweep(
        req.scope,
        checks_to_run,
        req.entity,
        req.relation,
        req.stale_lookahead_s,
    )
    return LintResult(
        findings=[LintFinding(**f) for f in result["findings"]],
        checked_at=result["checked_at"],
        scope=result["scope"],
        checks_run=result["checks_run"],
        fact_count=result["fact_count"],
    )


@router.get("/v1/lint/jobs/{job_id}")
def get_lint_job(
    job_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> Any:
    """Poll the status of an async lint job (spec §14.5)."""
    if not identity.can_read():
        raise HTTPException(status_code=403, detail="read permission required")
    job = get_job(job_id, job_type="lint")
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
