"""Fact assertion and query routes — spec §5.1, §5.2, §5.4, §5.5, §2.6."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import Identity, resolve_identity
from ..billing import BillingEvent, get_hook_bus
from ..db import db
from ..entity_normalizer import NormalizationError, is_informal, normalize_entity_uri
from ..fuzzy_resolver import resolve_entity
from ..garden_acl import (
    caller_can_see_garden,
    get_garden_by_garden_uri,
    require_garden_read,
    require_garden_write,
)
from ..hlc import node_hlc
from ..models import (
    VALID_SCOPES,
    AssertRequest,
    FactRecord,
    QueryResponse,
    row_to_record,
)
from .. import settings as _settings_pkg  # access via module so test patches propagate
from ..settings import settings as _settings  # direct ref for source_attestation_mode reads

router = APIRouter(prefix="/v1/facts", tags=["facts"])

_SYSTEM_RELATION_PREFIX = "stigmem:"


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
    mode = _settings.source_attestation_mode
    if mode == "off" or not _settings.auth_required:
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
    if not identity.can_write():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="write permission required")

    # C1: attestation enforcement — verify or require attestation token
    attested_key_id: str | None = None
    if req.attestation is not None:
        from .agent_keys import verify_attestation
        value_v_for_sig = _encode_v(req.value.type, req.value.v)
        canonical = (
            f"{req.entity}\n{req.relation}\n{req.value.type}\n{value_v_for_sig}\n{req.source}"
        ).encode("utf-8")
        attested_key_id = verify_attestation(
            key_id=req.attestation.key_id,
            signature_b64=req.attestation.signature,
            canonical_message=canonical,
            caller_entity_uri=identity.entity_uri,
        )
    elif _settings_pkg.settings.attestation_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="attestation required; register an agent key at POST /v1/auth/agent-keys",
        )

    try:
        entity = normalize_entity_uri(req.entity)
        source = normalize_entity_uri(req.source)
    except NormalizationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid_entity_uri: {exc}") from exc

    # Deprecation warning for informal URIs (spec §2.5)
    if is_informal(req.entity):
        print(
            f"[stigmem] DEPRECATED: informal entity URI {req.entity!r} — "
            f"use stigmem://authority/type/id format (spec §2.5)",
            file=sys.stderr,
        )
    if is_informal(req.source):
        print(
            f"[stigmem] DEPRECATED: informal source URI {req.source!r} — "
            f"use stigmem://authority/type/id format (spec §2.5)",
            file=sys.stderr,
        )

    # Layer 2: resolve user-defined semantic aliases (spec §2.6.6).
    # Runs after strict normalization (Layer 1) so the alias table is keyed on canonical forms.
    with db() as _alias_conn:
        entity = resolve_entity(_alias_conn, entity)
        source = resolve_entity(_alias_conn, source)

    # --- Source attestation (spec §18) ---
    attested = _check_source_attestation(source, identity)

    # --- Garden ACL (spec §17.3) ---
    garden = None
    if req.garden_id is not None:
        garden = get_garden_by_garden_uri(req.garden_id, tenant_id=identity.tenant_id)
        if garden is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="garden not found")
        if garden["scope"] != req.scope:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"scope mismatch: garden scope is '{garden['scope']}' but fact scope is '{req.scope}'",
            )
        require_garden_write(garden, identity)

    garden_uuid = garden["id"] if garden is not None else None
    attested_int = None if attested is None else (1 if attested else 0)

    # Relation namespacing convention check (see relation-convention.md)
    relation_warnings = _validate_relation(req.relation)
    for w in relation_warnings:
        print(f"[stigmem] WARN: relation naming: {w}", file=sys.stderr)

    fact_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    hlc = node_hlc.tick()
    value_v = _encode_v(req.value.type, req.value.v)
    audit_id = str(uuid.uuid4())

    with db() as conn:
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from, attested_key_id,
                garden_id, attested, tenant_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact_id,
                entity,    # normalized (spec §2.6)
                req.relation,
                req.value.type,
                value_v,
                source,    # normalized (spec §2.6)
                now,
                req.valid_until,
                req.confidence,
                req.scope,
                hlc,
                None,  # local write; not received from a peer
                attested_key_id,
                garden_uuid,
                attested_int,
                identity.tenant_id,
            ),
        )

        # C3: write audit entry joining principal → attested-source → fact-id
        conn.execute(
            """INSERT INTO fact_audit_log
               (id, fact_id, event_type, entity_uri, oidc_sub, source, attested_key_id, ts, tenant_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                audit_id,
                fact_id,
                "assert",
                identity.entity_uri,
                identity.oidc_sub,
                source,
                attested_key_id,
                now,
                identity.tenant_id,
            ),
        )

        row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()

        # Contradiction detection: skip bare stigmem: system facts — they are state
        # transitions, not semantic content, and are never in conflict (§9.1).
        # stigmem:// URI entities are user content and ARE subject to detection.
        _is_system = (
            entity.startswith(_SYSTEM_RELATION_PREFIX) and not entity.startswith("stigmem://")
        ) or (
            req.relation.startswith(_SYSTEM_RELATION_PREFIX) and not req.relation.startswith("stigmem://")
        )
        siblings: list[Any] = []
        if not _is_system:
            siblings = conn.execute(
                """SELECT id FROM facts
                   WHERE entity=? AND relation=? AND scope=? AND id!=? AND confidence>0.0
                     AND tenant_id=?""",
                (entity, req.relation, req.scope, fact_id, identity.tenant_id),
            ).fetchall()
        contradicted = len(siblings) > 0

        if contradicted:
            _record_contradictions(conn, fact_id, entity, req.relation, req.scope, siblings, identity.tenant_id)
            print(
                f"[stigmem] WARN: collision — entity={entity!r} relation={req.relation!r} "
                f"scope={req.scope!r}: fact {fact_id!r} contradicts {len(siblings)} existing "
                f"fact(s); verify relation namespacing (see relation-convention.md)",
                file=sys.stderr,
            )

    get_hook_bus().emit(BillingEvent(
        event_type="fact_written",
        tenant_id=identity.tenant_id,
        entity_uri=identity.entity_uri,
        fact_id=fact_id,
    ))

    return row_to_record(row, contradicted=contradicted, warnings=relation_warnings)


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


@router.get("", response_model=QueryResponse)
def query_facts(
    identity: Annotated[Identity, Depends(resolve_identity)],
    entity: str | None = Query(None),
    relation: str | None = Query(None),
    source: str | None = Query(None),
    scope: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_contradicted: bool = Query(False),
    include_expired: bool = Query(False),
    after: str | None = Query(None, description="Return facts with timestamp > this ISO 8601 value"),
    cursor: str | None = Query(None, description="Opaque pagination cursor (fact id)"),
    limit: int = Query(50, ge=1, le=500),
    garden_id: str | None = Query(None, description="v0.9: filter to facts in this garden (spec §5.20)"),
    attested: bool | None = Query(None, description="v0.9: filter by attestation status (spec §18.6)"),
) -> QueryResponse:
    """Query facts by pattern (spec §5.2, §5.20). Omitted fields are wildcards. Entity/source are normalized (§2.6)."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")

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
        try:
            entity = normalize_entity_uri(entity)
        except NormalizationError:
            pass  # malformed query — fall through to exact-match with raw value
        conditions.append(
            "(entity = ? OR entity IN"
            " (SELECT raw_uri FROM entity_aliases WHERE canonical_uri = ?))"
        )
        params.extend([entity, entity])
    if relation:
        conditions.append("relation = ?")
        params.append(relation)
    if source:
        try:
            source = normalize_entity_uri(source)
        except NormalizationError:
            pass
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

    next_cursor = rows[-1]["id"] if has_more and rows else None
    return QueryResponse(facts=records, total=len(records), cursor=next_cursor)


@router.get("/{fact_id}", response_model=FactRecord)
def get_fact(
    fact_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> FactRecord:
    """Retrieve a single fact by ID (spec v0.4 §5.5, §17.3)."""
    if not identity.can_read():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read permission required")
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, identity.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")

    # Garden ACL: fact in a garden is only readable by members (spec §17.3)
    if "garden_id" in row.keys() and row["garden_id"] is not None:
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
    return row_to_record(row, contradicted=sibling_count > 1)


def _encode_v(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)
