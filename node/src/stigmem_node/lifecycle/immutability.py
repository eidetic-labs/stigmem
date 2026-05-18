"""ADR-016 L1 append-only journal and projection helpers."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def write_fact_journal(
    conn: Any,
    *,
    fact_id: str,
    event_type: str,
    tenant_id: str,
    actor_uri: str | None,
    source: str | None,
    scope: str | None,
    cid: str | None,
    body: dict[str, Any],
) -> None:
    """Append one fact event to the immutable L1 journal."""
    conn.execute(
        "INSERT INTO fact_journal "
        "(id, fact_id, event_type, event_ts, tenant_id, actor_uri, source, scope, cid, body_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            fact_id,
            event_type,
            utc_now_iso(),
            tenant_id,
            actor_uri,
            source,
            scope,
            cid,
            json.dumps(body, sort_keys=True, separators=(",", ":")),
        ),
    )


def set_embedding_status(
    conn: Any,
    *,
    fact_id: str,
    embedding_missing: bool,
    updated_by: str | None = None,
    last_error: str | None = None,
) -> None:
    """Upsert embedding status in the projection table, not on ``facts``."""
    conn.execute(
        "INSERT INTO fact_embedding_status "
        "(fact_id, embedding_missing, updated_at, last_error, updated_by) "
        "VALUES (?,?,?,?,?) "
        "ON CONFLICT(fact_id) DO UPDATE SET "
        "embedding_missing = excluded.embedding_missing, "
        "updated_at = excluded.updated_at, "
        "last_error = excluded.last_error, "
        "updated_by = excluded.updated_by",
        (
            fact_id,
            1 if embedding_missing else 0,
            utc_now_iso(),
            last_error,
            updated_by,
        ),
    )


def set_fact_validity_override(
    conn: Any,
    *,
    fact_id: str,
    valid_until: str | None = None,
    confidence: float | None = None,
    reason: str | None = None,
    updated_by: str | None = None,
) -> None:
    """Upsert derived validity/confidence state outside the base fact row."""
    conn.execute(
        "INSERT INTO fact_validity_overrides "
        "(fact_id, valid_until, confidence, reason, updated_at, updated_by) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(fact_id) DO UPDATE SET "
        "valid_until = excluded.valid_until, "
        "confidence = excluded.confidence, "
        "reason = excluded.reason, "
        "updated_at = excluded.updated_at, "
        "updated_by = excluded.updated_by",
        (fact_id, valid_until, confidence, reason, utc_now_iso(), updated_by),
    )


def set_fact_quarantine_status(
    conn: Any,
    *,
    fact_id: str,
    quarantine_garden_id: str | None,
    quarantine_status: str | None,
    quarantine_reason: str | None = None,
    quarantine_acted_by: str | None = None,
    quarantine_acted_at: str | None = None,
) -> None:
    """Upsert quarantine workflow state outside the base fact row."""
    conn.execute(
        "INSERT INTO fact_quarantine_status "
        "(fact_id, quarantine_garden_id, quarantine_status, quarantine_reason, "
        " quarantine_acted_by, quarantine_acted_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(fact_id) DO UPDATE SET "
        "quarantine_garden_id = excluded.quarantine_garden_id, "
        "quarantine_status = excluded.quarantine_status, "
        "quarantine_reason = excluded.quarantine_reason, "
        "quarantine_acted_by = excluded.quarantine_acted_by, "
        "quarantine_acted_at = excluded.quarantine_acted_at, "
        "updated_at = excluded.updated_at",
        (
            fact_id,
            quarantine_garden_id,
            quarantine_status,
            quarantine_reason,
            quarantine_acted_by,
            quarantine_acted_at,
            utc_now_iso(),
        ),
    )


def set_fact_garden_membership(
    conn: Any,
    *,
    fact_id: str,
    garden_id: str | None,
    updated_by: str | None = None,
) -> None:
    """Upsert derived garden membership outside the base fact row."""
    conn.execute(
        "INSERT INTO fact_garden_membership "
        "(fact_id, garden_id, updated_at, updated_by) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(fact_id) DO UPDATE SET "
        "garden_id = excluded.garden_id, "
        "updated_at = excluded.updated_at, "
        "updated_by = excluded.updated_by",
        (fact_id, garden_id, utc_now_iso(), updated_by),
    )


def set_fact_cid_backfill_status(
    conn: Any,
    *,
    fact_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Record CID backfill progress without mutating ``facts.cid``."""
    conn.execute(
        "INSERT INTO fact_cid_backfill "
        "(fact_id, status, attempted_at, error, updated_at) "
        "VALUES (?,?,?,?,?) "
        "ON CONFLICT(fact_id) DO UPDATE SET "
        "status = excluded.status, "
        "attempted_at = excluded.attempted_at, "
        "error = excluded.error, "
        "updated_at = excluded.updated_at",
        (fact_id, status, utc_now_iso(), error, utc_now_iso()),
    )
