"""Centralized audit event emission — spec §22.3.

All code paths that emit audit events call ``emit()`` here.  Write-ahead
semantics are guaranteed by the caller: callers must call ``emit()`` *before*
returning the HTTP response (or inside the same DB transaction where
possible).

Supported event_type values (spec §22.3.1):
  fact_write, fact_read, capability_token_issue, capability_token_revoke,
  manifest_publish, key_rotation, federation_connect, quarantine_admit,
  quarantine_release, quota_breach, admin_action, replay_rejected,
  instruction_audit, instruction_quarantined, instruction_promoted,
  peer_hlc_anomaly, api_key_rehashed
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .db import db
from .metrics import AUDIT_EVENT
from .plugins import AuditEvent, Success, get_registry

INSTRUCTION_QUARANTINED = "instruction_quarantined"
INSTRUCTION_PROMOTED = "instruction_promoted"


def is_instruction_fact(entity: str | None, relation: str | None = None) -> bool:
    """Return true for the instruction namespace used before interpret_as lands."""
    return bool(
        (entity and entity.startswith("instruction:"))
        or (relation and relation.startswith("instruction:"))
    )


def _emit_with_conn(
    event_type: str,
    entity_uri: str,
    tenant_id: str,
    oidc_sub: str | None,
    fact_id: str | None,
    source: str,
    attested_key_id: str | None,
    detail_json: str | None,
    now: str,
    entry_id: str,
    conn: Any,
) -> None:
    cur = conn.execute(
        """INSERT INTO fact_audit_log
           (id, fact_id, event_type, entity_uri, oidc_sub, source,
            attested_key_id, ts, tenant_id, detail)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            entry_id,
            fact_id,
            event_type,
            entity_uri,
            oidc_sub,
            source,
            attested_key_id,
            now,
            tenant_id,
            detail_json,
        ),
    )
    # seq = rowid on SQLite (implicit monotonic integer); on PostgreSQL the column
    # carries a sequence DEFAULT so no manual update is needed — lastrowid is None.
    row_seq = getattr(cur, "lastrowid", None)
    if row_seq is not None:
        conn.execute("UPDATE fact_audit_log SET seq=? WHERE id=?", (row_seq, entry_id))


def emit(
    event_type: str,
    *,
    entity_uri: str,
    tenant_id: str = "default",
    oidc_sub: str | None = None,
    fact_id: str | None = None,
    source: str = "",
    attested_key_id: str | None = None,
    scope: str | None = None,
    detail: dict[str, Any] | None = None,
    conn: Any = None,
) -> None:
    """Append one audit event to fact_audit_log (write-ahead).

    Pass ``conn`` to reuse an existing open connection and participate in its
    transaction (required when called from inside a ``with db() as conn:`` block
    to avoid nested-lock errors on SQLite).  If ``conn`` is None a fresh
    connection context is opened.

    The ``seq`` column is populated from the inserted row's implicit rowid on
    SQLite, or from a named sequence DEFAULT on PostgreSQL (migration 022).
    """
    now = datetime.now(UTC).isoformat()
    entry_id = str(uuid.uuid4())
    detail_json = json.dumps(detail) if detail else None

    if conn is not None:
        _emit_with_conn(
            event_type,
            entity_uri,
            tenant_id,
            oidc_sub,
            fact_id,
            source,
            attested_key_id,
            detail_json,
            now,
            entry_id,
            conn,
        )
    else:
        with db() as _conn:
            _emit_with_conn(
                event_type,
                entity_uri,
                tenant_id,
                oidc_sub,
                fact_id,
                source,
                attested_key_id,
                detail_json,
                now,
                entry_id,
                _conn,
            )

    # §22.3: increment Prometheus counter for every successfully written audit event.
    AUDIT_EVENT.labels(event_type=event_type, tenant=tenant_id).inc()
    get_registry().fire_fire_and_forget(
        "audit_emit",
        event=AuditEvent(
            event_type=event_type,
            actor_uri=entity_uri,
            target_uri=fact_id,
            tenant_id=tenant_id,
            timestamp=datetime.fromisoformat(now),
            outcome=Success(),
            metadata={
                "oidc_sub": oidc_sub,
                "source": source,
                "attested_key_id": attested_key_id,
                "scope": scope,
                "detail": detail or {},
                "audit_entry_id": entry_id,
            },
        ),
    )


def emit_nofail(
    event_type: str,
    *,
    entity_uri: str,
    tenant_id: str = "default",
    oidc_sub: str | None = None,
    fact_id: str | None = None,
    source: str = "",
    attested_key_id: str | None = None,
    scope: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Like ``emit()`` but swallows exceptions — use in middleware/best-effort paths."""
    import logging

    try:
        emit(
            event_type,
            entity_uri=entity_uri,
            tenant_id=tenant_id,
            oidc_sub=oidc_sub,
            fact_id=fact_id,
            source=source,
            attested_key_id=attested_key_id,
            scope=scope,
            detail=detail,
        )
    except Exception:
        logging.getLogger("stigmem.audit").exception(
            "Failed to emit audit event type=%s principal=%s tenant=%s",
            event_type,
            entity_uri,
            tenant_id,
        )


def emit_instruction_event_if_applicable(
    event_type: str,
    *,
    fact_id: str,
    fact_entity: str | None,
    fact_relation: str | None,
    actor_uri: str,
    tenant_id: str = "default",
    oidc_sub: str | None = None,
    source: str = "",
    detail: dict[str, Any] | None = None,
    conn: Any,
) -> None:
    """Emit ADR-003 instruction audit events for instruction-namespace facts."""
    if not is_instruction_fact(fact_entity, fact_relation):
        return

    emit(
        event_type,
        entity_uri=actor_uri,
        tenant_id=tenant_id,
        oidc_sub=oidc_sub,
        fact_id=fact_id,
        source=source or actor_uri,
        detail={
            "fact_entity": fact_entity,
            "fact_relation": fact_relation,
            **(detail or {}),
        },
        conn=conn,
    )
