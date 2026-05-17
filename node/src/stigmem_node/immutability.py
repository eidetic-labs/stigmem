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
