"""Shared recall route helpers and compatibility utilities."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from ...auth import Identity
from ...models.facts import FactRecord, row_to_record

logger = logging.getLogger("stigmem.recall")

router = APIRouter(prefix="/v1/recall", tags=["recall"])

_MAX_SEED_ENTITIES = 5
_MAX_GRAPH_ENTITIES = 50
_MAX_CANDIDATES = 500


def _public_module() -> Any:
    """Return the public recall module so test monkey-patches stay visible."""
    return sys.modules["stigmem_node.routes.recall"]

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _estimate_tokens(record: FactRecord) -> int:
    """Rough token estimate: 4 chars ≈ 1 token (GPT tokeniser heuristic)."""
    text = f"{record.entity} {record.relation} {record.value.v or ''} {record.source}"
    return max(1, len(text) // 4)


def _recency_score(timestamp_str: str) -> float:
    """Normalised recency: 1.0 = now, 0.0 = ≥1 year old."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        days_old = (datetime.now(UTC) - ts).days
        return max(0.0, 1.0 - days_old / 365.0)
    except Exception:
        return 0.5


def _fetch_facts_by_ids(
    conn: Any,
    fact_ids: list[str],
) -> dict[str, FactRecord]:
    """Bulk-fetch facts by ID; returns {id: FactRecord}."""
    if not fact_ids:
        return {}
    placeholders = ",".join("?" * len(fact_ids))
    rows = conn.execute(
        f"SELECT * FROM facts WHERE id IN ({placeholders})",  # noqa: S608  # nosec B608
        fact_ids,
    ).fetchall()
    return {row["id"]: row_to_record(row) for row in rows}


def _write_recall_audit(
    conn: Any,
    recall_id: str,
    identity: Identity,
    query_hash: str,
    scope: str,
    token_budget: int,
    facts_returned: int,
    tokens_used: int,
    truncated: bool,
) -> None:
    now = _now_iso()
    try:
        conn.execute(
            """
            INSERT INTO recall_audit_log
              (id, entity_uri, query_hash, scope, token_budget,
               facts_returned, tokens_used, truncated, tenant_id, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recall_id,
                identity.entity_uri,
                query_hash,
                scope,
                token_budget,
                facts_returned,
                tokens_used,
                1 if truncated else 0,
                identity.tenant_id,
                now,
            ),
        )
    except Exception as exc:
        logger.error("Failed to write recall_audit_log: %s", exc)
