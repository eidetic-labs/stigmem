"""Fact assertion and query routes — spec §5.1, §5.2, §5.4, §5.5, §2.6."""

from __future__ import annotations

import contextlib
import logging
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from .. import settings as _settings_pkg  # access via module so test patches propagate
from ..auth import Identity, resolve_identity
from ..cid import compute_cid_from_row, is_cid, is_valid_cid
from ..db import db
from ..entity_normalizer import NormalizationError, normalize_entity_uri
from ..garden_acl import (
    caller_can_see_garden,
    get_garden_by_garden_uri,
    require_garden_read,
)
from ..hlc import node_hlc
from ..metrics import FACT_READ
from ..models import (
    VALID_SCOPES,
    AssertRequest,
    FactRecord,
    ProvenanceEntry,
    ProvenanceResponse,
    QueryResponse,
    TombstoneNotice,
    row_to_record,
)
from ..recall_pipeline import apply_recall_pipeline

# Re-exported binding used by tests that monkey-patch ``routes.facts._settings``.
from ..settings import settings as _settings  # noqa: F401
from ..tracing import start_span

logger = logging.getLogger("stigmem.facts")


def _get_tombstone_filter(
    conn: Any,
    entity_uris: list[str],
    scope: str,
    is_admin_caller: bool,
) -> tuple[set[str], list[TombstoneNotice]]:
    """Return (excluded_entity_uris, tombstone_notices) for entity_uris in scope (§23.3, §24.3).

    excluded_entity_uris: entities under active (non-legal-hold) tombstones.
    tombstone_notices: annotations for legal_hold tombstones visible to admin callers.
    """

    if not entity_uris:
        return set(), []

    placeholders = ",".join("?" * len(entity_uris))
    # BEGIN IMMEDIATE for SQLite consistency (§23.3.3 rule 5).
    # On postgres this is a syntax error; rollback clears the failed txn state.
    # Catch Exception (not sqlite3.Error) because conn may be a psycopg2/libsql
    # connection and each raises its own backend-specific error type.
    try:
        conn.execute("BEGIN IMMEDIATE")
    except Exception as _begin_exc:  # noqa: BLE001
        logger.debug("BEGIN IMMEDIATE failed (likely non-sqlite backend): %s", _begin_exc)
        with contextlib.suppress(Exception):  # noqa: BLE001
            conn.rollback()
    rows = conn.execute(
        f"""SELECT t.id, t.entity_uri, t.scope, t.created_at, t.legal_hold
            FROM tombstones t
            WHERE t.entity_uri IN ({placeholders})
            AND NOT EXISTS (
                SELECT 1 FROM tombstone_revocations r WHERE r.tombstone_id = t.id
            )""",  # noqa: S608  # nosec B608
        entity_uris,
    ).fetchall()
    with contextlib.suppress(Exception):  # noqa: BLE001
        conn.execute("COMMIT")

    excluded: set[str] = set()
    notices: list[TombstoneNotice] = []

    for row in rows:
        uri = row["entity_uri"]
        row_scope = row["scope"]
        if row_scope != "*" and row_scope != scope:
            continue

        if row["legal_hold"]:
            if is_admin_caller:
                notices.append(TombstoneNotice(
                    entity_uri=uri,
                    tombstone_id=row["id"],
                    legal_hold=True,
                    tombstone_created_at=row["created_at"],
                ))
            else:
                excluded.add(uri)
        else:
            excluded.add(uri)

    return excluded, notices

router = APIRouter(prefix="/v1/facts", tags=["facts"])

_SYSTEM_RELATION_PREFIX = "stigmem:"


def _validate_as_of(as_of: str) -> datetime:
    """Parse and validate an as_of timestamp per §24.2.2."""
    import re
    # URL query strings decode + as space; restore the + in timezone offsets like "+00:00".
    normalized = re.sub(r" (\d{2}:\d{2})$", r"+\1", as_of).replace("Z", "+00:00")
    try:
        ts = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "as_of_invalid_timestamp", "message": str(exc)},
        ) from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    if ts > datetime.now(UTC) + timedelta(seconds=5):
        raise HTTPException(
            status_code=400,
            detail={"code": "as_of_future", "message": "as_of must not be in the future (§24.2.2)"},
        )
    floor = _settings_pkg.settings.as_of_retention_floor
    if floor:
        try:
            floor_ts = datetime.fromisoformat(floor.replace("Z", "+00:00"))
            if floor_ts.tzinfo is None:
                floor_ts = floor_ts.replace(tzinfo=UTC)
            if ts < floor_ts:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "as_of_before_retention_floor",
                        "message": (
                            "as_of predates the retention horizon "
                            "for this deployment (§24.2.2)"
                        ),
                    },
                )
        except HTTPException:
            raise
        except (ValueError, TypeError) as _floor_exc:
            logger.debug("as_of retention floor parse failed: %s", _floor_exc)
    return ts


def _query_facts_as_of_impl(
    conn: Any,
    *,
    entity: str | None,
    scope: str | None,
    relation: str | None,
    as_of: str,
    is_admin_caller: bool,
    tenant_id: str,
    limit: int,
    cursor: str | None,
) -> QueryResponse:
    """Return facts visible at as_of per §24.4.

    Retraction gating uses fact_retractions.retracted_at (append-only log), NOT facts.confidence.
    Expiry gating uses facts.valid_until.
    Tombstone filter per §24.3: retroactive RTBF unless legal_hold=true AND is_admin_caller.
    """
    # F-14 §24.3.2: pre-check — agent-key callers get empty results if a legal-hold
    # tombstone covers the queried entity (short-circuit before executing the query)
    if entity and not is_admin_caller:
        legal_hold_row = conn.execute(
            """SELECT 1 FROM tombstones t
               WHERE t.entity_uri = ?
               AND t.legal_hold = 1
               AND NOT EXISTS (
                   SELECT 1 FROM tombstone_revocations r WHERE r.tombstone_id = t.id
               )
               LIMIT 1""",
            (entity,),
        ).fetchone()
        if legal_hold_row is not None:
            return QueryResponse(facts=[], total=0, cursor=None)

    conditions = [
        "f.tenant_id = ?",
        "f.timestamp <= ?",
        "(f.valid_until IS NULL OR f.valid_until > ?)",
        (
            "NOT EXISTS (SELECT 1 FROM fact_retractions fr"
            " WHERE fr.fact_id = f.id AND fr.retracted_at <= ?)"
        ),
    ]
    params: list[Any] = [tenant_id, as_of, as_of, as_of]

    if entity:
        conditions.append(
            "(f.entity = ? OR f.entity IN"
            " (SELECT raw_uri FROM entity_aliases WHERE canonical_uri = ?))"
        )
        params.extend([entity, entity])
    if relation:
        conditions.append("f.relation = ?")
        params.append(relation)
    if scope:
        if scope not in VALID_SCOPES:
            raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")
        conditions.append("f.scope = ?")
        params.append(scope)
    if cursor:
        conditions.append("f.id > ?")
        params.append(cursor)

    where = " AND ".join(conditions)
    sql = f"SELECT f.* FROM facts f WHERE {where} ORDER BY f.timestamp DESC, f.id DESC LIMIT ?"  # nosec B608
    params.append(limit + 1)

    rows = conn.execute(sql, params).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]

    seen: dict[tuple[str, str, str], int] = {}
    for r in rows:
        key = (r["entity"], r["relation"], r["scope"])
        seen[key] = seen.get(key, 0) + 1

    records = [
        row_to_record(r, contradicted=seen[(r["entity"], r["relation"], r["scope"])] > 1)
        for r in rows
    ]

    # §24.3: tombstone filter for as_of queries
    tombstone_notices: list[TombstoneNotice] = []
    tombstone_filtered = False
    if records:
        entity_uris = list({r.entity for r in records})
        excluded, tombstone_notices = _get_tombstone_filter(
            conn, entity_uris, scope or "local", is_admin_caller
        )
        if excluded:
            records = [r for r in records if r.entity not in excluded]
            tombstone_filtered = True

    next_cursor = rows[-1]["id"] if has_more and rows else None
    # §23.3.3 r.3: suppress total when tombstone filtering was applied to prevent oracle leakage
    total = None if tombstone_filtered else len(records)
    return QueryResponse(
        facts=records,
        total=total,
        cursor=next_cursor,
        tombstone_notices=tombstone_notices,
    )


def _validate_relation(relation: str) -> list[str]:
    """Return convention warnings for a relation name (see relation-convention.md)."""
    if ":" not in relation:
        return [
            f"bare relation {relation!r} has no namespace prefix; "
            f"rename to 'your-prefix:{relation}' to prevent silent collisions "
            "(see relation-convention.md)"
        ]
    if relation.startswith(_SYSTEM_RELATION_PREFIX):
        return [
            f"relation {relation!r} uses reserved system prefix 'stigmem:'; "
            "non-system callers should use a custom namespace prefix (see spec §9.1)"
        ]
    return []


def _check_source_attestation(source: str, identity: Identity) -> bool | None:
    """Enforce source attestation per spec §18. Returns attested value or raises 403."""
    mode = _settings_pkg.settings.source_attestation_mode
    if mode == "off" or not _settings_pkg.settings.auth_required:
        return None

    attested = (source == identity.entity_uri)
    if not attested:
        if mode == "enforce":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"source_attestation_failed: declared source {source!r} does not match "
                    f"authenticated principal {identity.entity_uri!r} (spec §18)"
                ),
            )
        # warn mode
        print(
            f"[stigmem] WARN: source attestation mismatch — "
            f"declared source={source!r}, identity={identity.entity_uri!r}",
            file=sys.stderr,
        )
    return attested


@router.post("", response_model=FactRecord, status_code=status.HTTP_201_CREATED)
def assert_fact(
    req: AssertRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Assert a fact into the fabric (spec §5.1, §2.6). Normalizes entity/source URIs on ingest."""
    from ._facts_assert import assert_fact_impl

    with start_span(
        "stigmem.assert_fact",
        **{"stigmem.tenant": identity.tenant_id, "stigmem.principal": identity.entity_uri},
    ) as _span:
        return assert_fact_impl(req, identity, _span)


def _is_valid_entity_uri(uri: str) -> bool:
    """Minimal check: URI must contain '://' or start with 'urn:'."""
    return "://" in uri or uri.startswith("urn:")


def _embed_fact_background(
    fact_id: str,
    entity: str,
    relation: str,
    value_type: str,
    value_v: str,
) -> None:
    """Background thread: embed one fact and persist to vec_facts."""
    try:
        from .. import settings as settings_pkg
        from ..db import db
        from ..embedding import get_embedding_model
        from ..vector_search import check_or_register_model, embed_and_store_fact

        model = get_embedding_model(settings_pkg.settings)
        with db() as conn:
            check_or_register_model(conn, model.model_id, model.dimension)
            embed_and_store_fact(fact_id, entity, relation, value_type, value_v, conn, model)
    except Exception as exc:
        logger.warning("Write-time embedding failed for fact %s: %s", fact_id, exc)


def _record_contradictions(
    conn: Any,
    new_fact_id: str,
    entity: str,
    relation: str,
    scope: str,
    siblings: list[Any],
    tenant_id: str = "default",
) -> None:
    """Write conflict entities and conflicts table rows for new contradictions."""
    now = datetime.now(UTC).isoformat()
    for sibling in siblings:
        sibling_id = sibling["id"]

        already = conn.execute(
            """SELECT id FROM conflicts
               WHERE (fact_a_id=? AND fact_b_id=?) OR (fact_a_id=? AND fact_b_id=?)""",
            (new_fact_id, sibling_id, sibling_id, new_fact_id),
        ).fetchone()
        if already:
            continue

        conflict_id = f"stigmem:conflict:{uuid.uuid4()}"
        h_between = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from, tenant_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()), conflict_id, "stigmem:conflict:between",
                "text", f"{new_fact_id} {sibling_id}",
                "system:stigmem", now, None, 1.0, scope, h_between, None, tenant_id,
            ),
        )
        h_status = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from, tenant_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()), conflict_id, "stigmem:conflict:status",
                "string", "unresolved",
                "system:stigmem", now, None, 1.0, scope, h_status, None, tenant_id,
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO conflicts (id, fact_a_id, fact_b_id, status, detected_at)
               VALUES (?,?,?,?,?)""",
            (conflict_id, new_fact_id, sibling_id, "unresolved", now),
        )


@router.get(
    "",
    response_model=QueryResponse,
    description=(
        "Query facts by pattern (spec §5.2, §5.20). "
        "Omitted fields are wildcards. Entity/source are normalized (§2.6)."
    ),
)
def query_facts(
    identity: Annotated[Identity, Depends(resolve_identity)],
    response: Response,
    entity: str | None = Query(None),
    relation: str | None = Query(None),
    source: str | None = Query(None),
    scope: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_contradicted: bool = Query(False),
    include_expired: bool = Query(False),
    after: str | None = Query(
        None, description="Return facts with timestamp > this ISO 8601 value"
    ),
    cursor: str | None = Query(None, description="Opaque pagination cursor (fact id)"),
    limit: int = Query(50, ge=1, le=500),
    garden_id: str | None = Query(
        None, description="v0.9: filter to facts in this garden (spec §5.20)"
    ),
    attested: bool | None = Query(
        None, description="v0.9: filter by attestation status (spec §18.6)"
    ),
    include_low_trust: bool = Query(
        False,
        description="v1.1: include facts with effective_confidence < 0.3 (§19.4.4)",
    ),
    as_of: str | None = Query(
        None,
        description="§24: time-travel — return facts visible at this ISO 8601 timestamp",
    ),
) -> QueryResponse:
    """Query facts by pattern (spec §5.2, §5.20)."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="read permission required",
        )

    # §24.4: time-travel query — delegate to as_of implementation
    if as_of is not None:
        _validate_as_of(as_of)
        with db() as conn:
            result = _query_facts_as_of_impl(
                conn,
                entity=entity,
                scope=scope,
                relation=relation,
                as_of=as_of,
                is_admin_caller="admin" in identity.permissions,
                tenant_id=identity.tenant_id,
                limit=limit,
                cursor=cursor,
            )
        if result.total is not None:
            response.headers["X-Total-Count"] = str(result.total)
        return result

    FACT_READ.labels(principal=identity.entity_uri, tenant=identity.tenant_id).inc()

    # Garden ACL: resolve and enforce membership before querying (spec §5.20, §17.3)
    garden = None
    if garden_id is not None:
        garden = get_garden_by_garden_uri(garden_id, tenant_id=identity.tenant_id)
        if garden is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")
        require_garden_read(garden, identity)

    conditions: list[str] = ["confidence >= ?", "tenant_id = ?"]
    params: list[Any] = [min_confidence, identity.tenant_id]

    # Garden filter: explicit garden_id, or hide garden facts from callers who can't see them
    if garden is not None:
        conditions.append("garden_id = ?")
        params.append(garden["id"])
    else:
        # Hide garden-tagged facts from callers who aren't members (spec §17.3)
        with db() as _g_conn:
            visible_garden_ids = [
                row["id"] for row in _g_conn.execute(
                    "SELECT id FROM gardens WHERE tenant_id = ?", (identity.tenant_id,)
                ).fetchall()
                if caller_can_see_garden(row["id"], identity)
            ]
        if visible_garden_ids:
            placeholders = ",".join("?" * len(visible_garden_ids))
            conditions.append(f"(garden_id IS NULL OR garden_id IN ({placeholders}))")
            params.extend(visible_garden_ids)
        else:
            conditions.append("garden_id IS NULL")

    if attested is not None:
        conditions.append("attested = ?")
        params.append(1 if attested else 0)

    if entity:
        # malformed query — fall through to exact-match with raw value
        with contextlib.suppress(NormalizationError):
            entity = normalize_entity_uri(entity)
        conditions.append(
            "(entity = ? OR entity IN"
            " (SELECT raw_uri FROM entity_aliases WHERE canonical_uri = ?))"
        )
        params.extend([entity, entity])
    if relation:
        conditions.append("relation = ?")
        params.append(relation)
    if source:
        with contextlib.suppress(NormalizationError):
            source = normalize_entity_uri(source)
        conditions.append(
            "(source = ? OR source IN"
            " (SELECT raw_uri FROM entity_aliases WHERE canonical_uri = ?))"
        )
        params.extend([source, source])
    if scope:
        if scope not in VALID_SCOPES:
            raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")
        conditions.append("scope = ?")
        params.append(scope)
    if after:
        conditions.append("timestamp > ?")
        params.append(after)
    if cursor:
        conditions.append("id > ?")
        params.append(cursor)

    if not include_expired:
        now = datetime.now(UTC).isoformat()
        conditions.append("(valid_until IS NULL OR valid_until > ?)")
        params.append(now)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM facts WHERE {where} ORDER BY timestamp DESC, id DESC LIMIT ?"  # nosec B608 — where is built from literal SQL fragments; all user values in params
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    seen: dict[tuple[str, str, str], int] = {}
    for r in rows:
        key = (r["entity"], r["relation"], r["scope"])
        seen[key] = seen.get(key, 0) + 1

    records = [
        row_to_record(r, contradicted=seen[(r["entity"], r["relation"], r["scope"])] > 1)
        for r in rows
    ]

    if not include_contradicted:
        records = [r for r in records if not r.contradicted]

    # v1.1: apply recall-time trust multiplier + content sanitizer (§19.4.4, §19.7)
    records = apply_recall_pipeline(records, identity=identity, include_low_trust=include_low_trust)

    # §23.3: tombstone filter — must be applied after scope filtering, before packing
    tombstone_filtered = False
    if records:
        entity_uris_in_result = list({r.entity for r in records})
        with db() as _tc_conn:
            excluded, _notices = _get_tombstone_filter(
                _tc_conn, entity_uris_in_result, scope or "local", "admin" in identity.permissions
            )
        if excluded:
            records = [r for r in records if r.entity not in excluded]
            tombstone_filtered = True

    next_cursor = rows[-1]["id"] if has_more and rows else None
    # §23.3.3 r.3: suppress total when tombstone filtering was applied to prevent oracle leakage
    total = None if tombstone_filtered else len(records)
    result = QueryResponse(facts=records, total=total, cursor=next_cursor)
    if result.total is not None:
        response.headers["X-Total-Count"] = str(result.total)
    return result


@router.get("/{fact_id}", response_model=FactRecord)
def get_fact(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Retrieve a single fact by UUID or sha256: CID (spec v0.4 §5.5, §17.3, §25.5)."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="read permission required",
        )

    # §25.5: dual addressing — resolve CID to UUID via alias table
    resolved_fact_id = fact_id
    if is_cid(fact_id):
        if not is_valid_cid(fact_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cid_malformed",
                    "message": "CID must be 'sha256:' followed by 64 hex chars",
                },
            )
        with db() as conn:
            alias = conn.execute(
                "SELECT fact_id FROM fact_cid_aliases WHERE cid = ?", (fact_id,)
            ).fetchone()
        if alias is None:
            raise HTTPException(status_code=404, detail="fact not found")
        resolved_fact_id = alias["fact_id"]

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
            (resolved_fact_id, identity.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")

    # F-11 §25.6.1/§23.3.3: tombstone indistinguishability — tombstoned facts return 404
    from ..tombstone_cache import is_tombstoned as _is_tombstoned_check
    if _is_tombstoned_check(row["entity"], identity.tenant_id):
        raise HTTPException(status_code=404, detail="fact not found")

    # Garden ACL: fact in a garden is only readable by members (spec §17.3)
    if "garden_id" in row.keys() and row["garden_id"] is not None:  # noqa: SIM118  # sqlite3.Row __contains__ checks values not keys
        with db() as conn:
            garden_row = conn.execute(
                "SELECT * FROM gardens WHERE id = ? AND tenant_id = ?",
                (row["garden_id"], identity.tenant_id),
            ).fetchone()
        if garden_row is not None:
            require_garden_read(dict(garden_row), identity)

    with db() as conn:
        sibling_count: int = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE entity=? AND relation=? AND scope=? AND tenant_id=?",
            (row["entity"], row["relation"], row["scope"], identity.tenant_id),
        ).fetchone()[0]
    record = row_to_record(row, contradicted=sibling_count > 1)
    # v1.1: recall pipeline (trust multiplier + sanitizer)
    pipeline_results = apply_recall_pipeline([record], identity=identity, include_low_trust=True)
    if pipeline_results:
        return pipeline_results[0]
    # Pending-quarantine facts return 404 to normal callers
    raise HTTPException(status_code=404, detail="fact not found")


class _CidVerifyResponse(BaseModel):
    cid_valid: bool
    computed_cid: str
    stored_cid: str | None
    mismatch_reason: str | None = None


@router.post("/{fact_id}/verify-cid", response_model=_CidVerifyResponse, tags=["facts"])
def verify_cid(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> _CidVerifyResponse:
    """Verify a fact's stored CID against a freshly computed one (spec §25.6.2)."""
    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="read permission required",
        )
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, identity.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")
    computed = compute_cid_from_row(row)
    stored = row["cid"] if "cid" in row.keys() else None  # noqa: SIM118  # sqlite3.Row __contains__ checks values not keys
    if stored is None:
        return _CidVerifyResponse(
            cid_valid=False,
            computed_cid=computed,
            stored_cid=None,
            mismatch_reason="stored_cid is null (pre-Phase-13 record pending backfill)",
        )
    if computed == stored:
        return _CidVerifyResponse(cid_valid=True, computed_cid=computed, stored_cid=stored)
    logger.warning("CID mismatch for fact %s: computed=%s stored=%s", fact_id, computed, stored)
    return _CidVerifyResponse(
        cid_valid=False,
        computed_cid=computed,
        stored_cid=stored,
        mismatch_reason="stored_cid does not match computed_cid",
    )


def _encode_v(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)


@router.get("/{fact_id}/provenance", response_model=ProvenanceResponse)
def get_provenance(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> ProvenanceResponse:
    """Provenance walk with tombstone suppression (spec §23.3.2 r.4 + §20.6.2).

    Returns the derived_from chain for a fact.  Any entry whose referenced entity is
    tombstoned — or whose fact is otherwise inaccessible — is redacted to
    {"hash": "...", "exists": false}, indistinguishable from the §20.6.2
    unauthorized cross-scope pattern to prevent existence leakage.
    """
    import json as _prov_json

    if not identity.can_read():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="read permission required",
        )

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, identity.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")

    derived_from_raw = row["derived_from"] if "derived_from" in row.keys() else None  # noqa: SIM118  # sqlite3.Row __contains__ checks values not keys
    cid_val = row["cid"] if "cid" in row.keys() else None  # noqa: SIM118  # sqlite3.Row __contains__ checks values not keys
    root_scope: str = row["scope"] or "local"

    if not derived_from_raw:
        return ProvenanceResponse(fact_id=fact_id, cid=cid_val, derived_from=[])

    try:
        entries_raw: list[Any] = _prov_json.loads(derived_from_raw)
    except Exception:
        entries_raw = []

    # Resolve each derived_from entry to its referenced fact row
    resolved: list[tuple[str, Any]] = []  # (hash_val, ref_row | None)
    for entry in entries_raw:
        if not isinstance(entry, dict):
            continue
        hash_val: str = entry.get("hash", "")
        entry_fact_id: str | None = entry.get("fact_id")

        ref_row = None
        with db() as conn:
            if entry_fact_id:
                ref_row = conn.execute(
                    "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
                    (entry_fact_id, identity.tenant_id),
                ).fetchone()
            elif hash_val.startswith("sha256:"):
                alias = conn.execute(
                    "SELECT fact_id FROM fact_cid_aliases WHERE cid = ?",
                    (hash_val,),
                ).fetchone()
                if alias:
                    ref_row = conn.execute(
                        "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
                        (alias["fact_id"], identity.tenant_id),
                    ).fetchone()
        resolved.append((hash_val, ref_row))

    # Single tombstone filter call across all resolved entity URIs (§23.3.2 r.4)
    accessible_entities = [ref_row["entity"] for _, ref_row in resolved if ref_row is not None]
    excluded: set[str] = set()
    if accessible_entities:
        with db() as _tc_conn:
            is_admin = identity.can_write() and identity.can_federate()
            excluded, _ = _get_tombstone_filter(
                _tc_conn, accessible_entities, root_scope, is_admin
            )

    # Build response — §23.3.2 r.4 tombstone and §20.6.2 unauthorized share identical shape
    result: list[ProvenanceEntry] = []
    for hash_val, ref_row in resolved:
        if ref_row is None:
            result.append(ProvenanceEntry(hash=hash_val, exists=False))
            continue
        if ref_row["entity"] in excluded:
            result.append(ProvenanceEntry(hash=hash_val, exists=False))
            continue
        result.append(ProvenanceEntry(
            hash=hash_val,
            fact_id=ref_row["id"],
            entity=ref_row["entity"],
            exists=True,
        ))

    return ProvenanceResponse(fact_id=fact_id, cid=cid_val, derived_from=result)
