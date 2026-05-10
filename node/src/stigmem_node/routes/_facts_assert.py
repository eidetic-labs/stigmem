"""Implementation of POST /v1/facts (assert_fact) extracted from routes/facts.py.

Imported back into ``routes.facts``; the route stub there delegates to this
function inside its tracing span.  Helper symbols are imported lazily inside
the function to keep the module-level import graph acyclic.
No behavioural changes — code was moved verbatim from facts.py.
"""

from __future__ import annotations

import logging
import sys
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from ..auth import Identity
from ..billing import BillingEvent, get_hook_bus
from ..cid import compute_cid
from ..db import db
from ..entity_normalizer import NormalizationError, is_informal, normalize_entity_uri
from ..fuzzy_resolver import resolve_entity
from ..garden_acl import (
    get_garden_by_garden_uri,
    require_garden_write,
)
from ..hlc import node_hlc
from ..metrics import CONTRADICTION, FACT_WRITE
from ..models import AssertRequest, FactRecord, row_to_record
from ..settings import settings as _settings  # noqa: F401  — kept for parity

logger = logging.getLogger("stigmem.facts")


def assert_fact_impl(
    req: AssertRequest,
    identity: Identity,
    _span: object,
) -> FactRecord:
    # Lazy imports of sibling helpers to avoid circular import with .facts
    from .facts import (
        _SYSTEM_RELATION_PREFIX,
        _check_source_attestation,
        _embed_fact_background,
        _encode_v,
        _is_valid_entity_uri,
        _record_contradictions,
        _validate_relation,
    )
    from .. import settings as _settings_pkg

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

    # §25.7.3: compute CID before write; persisted in the same transaction
    fact_cid = compute_cid(
        entity=entity,
        relation=req.relation,
        value_type=req.value.type,
        value_v=value_v or "",
        source=source,
        scope=req.scope,
        confidence=req.confidence,
    )

    _embed_enabled = _settings_pkg.settings.embed_enabled
    embedding_missing_val = 1 if _embed_enabled else None

    # F-10 §25.7.3: idempotent CID pre-check — if CID already exists, return existing record
    with db() as _precheck_conn:
        existing_alias = _precheck_conn.execute(
            "SELECT fact_id FROM fact_cid_aliases WHERE cid = ?", (fact_cid,)
        ).fetchone()
        if existing_alias is not None:
            existing_row = _precheck_conn.execute(
                "SELECT * FROM facts WHERE id = ? AND tenant_id = ?",
                (existing_alias["fact_id"], identity.tenant_id),
            ).fetchone()
            if existing_row is not None:
                return row_to_record(existing_row, contradicted=False)

    with db() as conn:
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from, attested_key_id,
                garden_id, attested, tenant_id, embedding_missing, cid)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                embedding_missing_val,
                fact_cid,
            ),
        )

        # F-10 §25.7.3: alias table row — idempotent upsert on CID collision
        alias_result = conn.execute(
            "INSERT OR IGNORE INTO fact_cid_aliases (fact_id, cid) VALUES (?, ?)",
            (fact_id, fact_cid),
        )
        if alias_result.rowcount == 0:
            # Concurrent same-CID write race: return existing record
            existing = conn.execute(
                "SELECT f.* FROM facts f JOIN fact_cid_aliases a ON a.fact_id = f.id"
                " WHERE a.cid = ? AND f.tenant_id = ?",
                (fact_cid, identity.tenant_id),
            ).fetchone()
            if existing is not None:
                return row_to_record(existing, contradicted=False)

        # C3 / §22.3: write-ahead audit entry for fact_write event (same transaction)
        from ..audit_event import emit as _emit_audit
        _emit_audit(
            "fact_write",
            entity_uri=identity.entity_uri,
            tenant_id=identity.tenant_id,
            oidc_sub=identity.oidc_sub,
            fact_id=fact_id,
            source=source,
            attested_key_id=attested_key_id,
            scope=req.scope,
            conn=conn,
        )

        # Graph adjacency index (§20.1.1): materialize edge for ref-typed facts
        if req.value.type == "ref" and value_v and _is_valid_entity_uri(value_v):
            from ..graph_index import upsert_edge as _upsert_edge
            _upsert_edge(
                conn,
                fact_id=fact_id,
                subject=entity,
                relation=req.relation,
                object_uri=value_v,
                scope=req.scope,
                confidence=req.confidence,
                garden_id=garden_uuid,
                tenant_id=identity.tenant_id,
                received_from=None,
                source_trust=None,
                valid_until=req.valid_until,
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

    # Phase 9: mark entity's memory card stale on every write (ACM-214)
    try:
        from ..card_materializer import mark_entity_stale as _mark_stale
        _mark_stale(entity, req.scope, identity.tenant_id)
    except Exception as _card_exc:
        logger.warning("card mark_stale failed for %r: %s", entity, _card_exc)

    # Phase 9 §2: write-time embedding (background thread, graceful fallback)
    if _embed_enabled:
        threading.Thread(
            target=_embed_fact_background,
            args=(fact_id, entity, req.relation, req.value.type, value_v or ""),
            daemon=True,
        ).start()

    get_hook_bus().emit(BillingEvent(
        event_type="fact_written",
        tenant_id=identity.tenant_id,
        entity_uri=identity.entity_uri,
        fact_id=fact_id,
    ))

    # §20: fan out to subscribers (fast DB insert only; delivery happens in sweep loop)
    try:
        import json as _json
        from ..subscription_delivery import fan_out as _subscription_fan_out
        _subscription_fan_out(
            fact_id=fact_id,
            entity=entity,
            scope=req.scope,
            garden_id=garden_uuid,
            tenant_id=identity.tenant_id,
            fact_payload_json=_json.dumps({
                "id": fact_id,
                "entity": entity,
                "relation": req.relation,
                "value_type": req.value.type,
                "value_v": value_v,
                "source": source,
                "timestamp": now,
                "scope": req.scope,
                "confidence": req.confidence,
                "garden_id": garden_uuid,
            }),
        )
    except Exception as _sub_exc:
        print(f"[stigmem] WARN: subscription fan_out failed: {_sub_exc}", file=sys.stderr)

    FACT_WRITE.labels(principal=identity.entity_uri, tenant=identity.tenant_id).inc()
    if contradicted:
        CONTRADICTION.labels(tenant=identity.tenant_id).inc()
    try:
        _span.set_attribute("stigmem.fact_id", fact_id)  # type: ignore[attr-defined]
        _span.set_attribute("stigmem.contradicted", contradicted)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001  # nosec B110
        pass

    return row_to_record(row, contradicted=contradicted, warnings=relation_warnings)
