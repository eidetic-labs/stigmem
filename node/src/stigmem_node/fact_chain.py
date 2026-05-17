"""ADR-016 L4 local hash chain for fact insert sequence integrity."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

_HASH_PREFIX = "sha256:"
_CHECKPOINT_PAYLOAD_KIND = "stigmem.fact_chain_checkpoint"
_CHECKPOINT_PAYLOAD_VERSION = 1


@dataclass(frozen=True)
class FactChainVerification:
    """Result of verifying a tenant's local fact chain."""

    valid: bool
    checked_entries: int
    mismatch_reason: str | None = None
    fact_id: str | None = None
    chain_seq: int | None = None


class FactChainIntegrityError(ValueError):
    """Raised when a fact chain cannot be verified."""

    def __init__(self, result: FactChainVerification) -> None:
        super().__init__(result.mismatch_reason or "fact_chain_invalid")
        self.result = result


def _sha256_json(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{_HASH_PREFIX}{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def compute_fact_chain_event_hash(row: Any) -> str:
    """Hash the fact fields that define the local insert event."""
    return _sha256_json(
        {
            "cid": row["cid"],
            "confidence": float(row["confidence"]),
            "entity": row["entity"],
            "fact_id": row["id"],
            "relation": row["relation"],
            "scope": row["scope"],
            "source": row["source"],
            "tenant_id": row["tenant_id"],
            "value_type": row["value_type"],
            "value_v": row["value_v"] or "",
        }
    )


def compute_fact_chain_hash(
    *,
    tenant_id: str,
    chain_seq: int,
    fact_id: str,
    event_hash: str,
    previous_hash: str | None,
    created_at: str,
) -> str:
    """Hash one chain link from its event hash and predecessor."""
    return _sha256_json(
        {
            "chain_seq": chain_seq,
            "created_at": created_at,
            "event_hash": event_hash,
            "fact_id": fact_id,
            "previous_hash": previous_hash,
            "tenant_id": tenant_id,
        }
    )


def append_fact_chain_entry(conn: Any, row: Any) -> None:
    """Append a local L4 chain entry for a newly inserted fact row."""
    tenant_id = row["tenant_id"]
    existing = conn.execute(
        "SELECT 1 FROM fact_chain WHERE tenant_id = ? AND fact_id = ?",
        (tenant_id, row["id"]),
    ).fetchone()
    if existing is not None:
        return

    previous = conn.execute(
        "SELECT chain_seq, chain_hash FROM fact_chain "
        "WHERE tenant_id = ? ORDER BY chain_seq DESC LIMIT 1",
        (tenant_id,),
    ).fetchone()
    chain_seq = 1 if previous is None else int(previous["chain_seq"]) + 1
    previous_hash = None if previous is None else previous["chain_hash"]
    event_hash = compute_fact_chain_event_hash(row)
    created_at = datetime.now(UTC).isoformat()
    chain_hash = compute_fact_chain_hash(
        tenant_id=tenant_id,
        chain_seq=chain_seq,
        fact_id=row["id"],
        event_hash=event_hash,
        previous_hash=previous_hash,
        created_at=created_at,
    )
    conn.execute(
        """
        INSERT INTO fact_chain
            (id, tenant_id, chain_seq, fact_id, event_hash, previous_hash, chain_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"chain_{uuid.uuid4().hex}",
            tenant_id,
            chain_seq,
            row["id"],
            event_hash,
            previous_hash,
            chain_hash,
            created_at,
        ),
    )
    submit_due_fact_chain_checkpoints(conn, tenant_id=tenant_id)


def verify_fact_chain(conn: Any, tenant_id: str = "default") -> FactChainVerification:
    """Verify chain sequence, fact event hashes, and link hashes for one tenant."""
    rows = conn.execute(
        """
        SELECT
            fc.*,
            f.id AS stored_fact_id,
            f.entity,
            f.relation,
            f.value_type,
            f.value_v,
            f.source,
            f.confidence,
            f.scope,
            f.tenant_id AS fact_tenant_id,
            f.cid
        FROM fact_chain fc
        LEFT JOIN facts f ON f.id = fc.fact_id AND f.tenant_id = fc.tenant_id
        WHERE fc.tenant_id = ?
        ORDER BY fc.chain_seq ASC
        """,
        (tenant_id,),
    ).fetchall()

    previous_hash: str | None = None
    expected_seq = 1
    for row in rows:
        chain_seq = int(row["chain_seq"])
        if chain_seq != expected_seq:
            return FactChainVerification(
                valid=False,
                checked_entries=expected_seq - 1,
                mismatch_reason="chain_seq_gap",
                fact_id=row["fact_id"],
                chain_seq=chain_seq,
            )
        if row["previous_hash"] != previous_hash:
            return FactChainVerification(
                valid=False,
                checked_entries=expected_seq - 1,
                mismatch_reason="previous_hash_mismatch",
                fact_id=row["fact_id"],
                chain_seq=chain_seq,
            )
        if row["stored_fact_id"] is None:
            return FactChainVerification(
                valid=False,
                checked_entries=expected_seq - 1,
                mismatch_reason="fact_missing",
                fact_id=row["fact_id"],
                chain_seq=chain_seq,
            )

        fact_row = {
            "cid": row["cid"],
            "confidence": row["confidence"],
            "entity": row["entity"],
            "id": row["fact_id"],
            "relation": row["relation"],
            "scope": row["scope"],
            "source": row["source"],
            "tenant_id": row["fact_tenant_id"],
            "value_type": row["value_type"],
            "value_v": row["value_v"],
        }
        expected_event_hash = compute_fact_chain_event_hash(fact_row)
        if row["event_hash"] != expected_event_hash:
            return FactChainVerification(
                valid=False,
                checked_entries=expected_seq - 1,
                mismatch_reason="event_hash_mismatch",
                fact_id=row["fact_id"],
                chain_seq=chain_seq,
            )

        expected_chain_hash = compute_fact_chain_hash(
            tenant_id=row["tenant_id"],
            chain_seq=chain_seq,
            fact_id=row["fact_id"],
            event_hash=row["event_hash"],
            previous_hash=row["previous_hash"],
            created_at=row["created_at"],
        )
        if row["chain_hash"] != expected_chain_hash:
            return FactChainVerification(
                valid=False,
                checked_entries=expected_seq - 1,
                mismatch_reason="chain_hash_mismatch",
                fact_id=row["fact_id"],
                chain_seq=chain_seq,
            )

        previous_hash = row["chain_hash"]
        expected_seq += 1

    return FactChainVerification(valid=True, checked_entries=len(rows))


def build_fact_chain_proof(conn: Any, tenant_id: str = "default") -> dict[str, Any]:
    """Return a compact proof over the current tenant-local chain head."""
    verification = verify_fact_chain(conn, tenant_id=tenant_id)
    if not verification.valid:
        raise FactChainIntegrityError(verification)
    head = conn.execute(
        "SELECT chain_hash FROM fact_chain WHERE tenant_id = ? ORDER BY chain_seq DESC LIMIT 1",
        (tenant_id,),
    ).fetchone()
    return {
        "tenant_id": tenant_id,
        "checked_entries": verification.checked_entries,
        "head_hash": None if head is None else head["chain_hash"],
        "checkpoint": latest_fact_chain_checkpoint(conn, tenant_id=tenant_id),
    }


def _json_dumps(body: dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _row_to_checkpoint(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "covered_chain_seq": int(row["covered_chain_seq"]),
        "chain_hash": row["chain_hash"],
        "status": row["status"],
        "attempt_count": int(row["attempt_count"]),
        "created_at": row["created_at"],
        "submitted_at": row["submitted_at"],
        "last_error": row["last_error"],
        "tl_backend": row["tl_backend"],
        "tl_log_id": row["tl_log_id"],
        "tl_leaf_hash": row["tl_leaf_hash"],
        "tl_log_index": row["tl_log_index"],
        "tl_integrated_time": row["tl_integrated_time"],
        "tl_inclusion_proof": json.loads(row["tl_inclusion_proof"] or "{}"),
        "tl_raw": json.loads(row["tl_raw"] or "{}"),
    }


def _checkpoint_payload(row: Any, created_at: str) -> dict[str, Any]:
    return {
        "kind": _CHECKPOINT_PAYLOAD_KIND,
        "version": _CHECKPOINT_PAYLOAD_VERSION,
        "tenant_id": row["tenant_id"],
        "covered_chain_seq": int(row["chain_seq"]),
        "chain_hash": row["chain_hash"],
        "created_at": created_at,
    }


def _latest_checkpoint_row(conn: Any, tenant_id: str) -> Any | None:
    return conn.execute(
        """
        SELECT *
        FROM fact_chain_checkpoints
        WHERE tenant_id = ?
        ORDER BY covered_chain_seq DESC
        LIMIT 1
        """,
        (tenant_id,),
    ).fetchone()


def latest_fact_chain_checkpoint(conn: Any, tenant_id: str = "default") -> dict[str, Any] | None:
    """Return the latest local L5 checkpoint metadata for a tenant."""
    row = _latest_checkpoint_row(conn, tenant_id)
    return None if row is None else _row_to_checkpoint(row)


def _next_pending_checkpoint(conn: Any, tenant_id: str, now: datetime) -> Any | None:
    return conn.execute(
        """
        SELECT *
        FROM fact_chain_checkpoints
        WHERE tenant_id = ?
          AND status = 'pending'
          AND (next_retry_at IS NULL OR next_retry_at <= ?)
        ORDER BY covered_chain_seq ASC
        LIMIT 1
        """,
        (tenant_id, now.isoformat()),
    ).fetchone()


def _submit_checkpoint_row(conn: Any, row: Any, now: datetime) -> None:
    from .identity.transparency_log import make_transparency_log
    from .settings import settings

    attempt_count = int(row["attempt_count"]) + 1
    try:
        entry = make_transparency_log().submit(json.loads(row["payload"]))
    except Exception as exc:
        retry_s = max(1, settings.fact_chain_checkpoint_retry_s)
        next_retry_at = (now + timedelta(seconds=retry_s)).isoformat()
        conn.execute(
            """
            UPDATE fact_chain_checkpoints
            SET attempt_count = ?,
                next_retry_at = ?,
                last_error = ?,
                status = 'pending'
            WHERE id = ?
            """,
            (attempt_count, next_retry_at, str(exc), row["id"]),
        )
        return

    conn.execute(
        """
        UPDATE fact_chain_checkpoints
        SET status = 'submitted',
            attempt_count = ?,
            submitted_at = ?,
            next_retry_at = NULL,
            last_error = NULL,
            tl_log_id = ?,
            tl_leaf_hash = ?,
            tl_log_index = ?,
            tl_integrated_time = ?,
            tl_inclusion_proof = ?,
            tl_raw = ?
        WHERE id = ?
        """,
        (
            attempt_count,
            now.isoformat(),
            entry.log_id,
            entry.leaf_hash,
            entry.log_index,
            entry.integrated_time,
            _json_dumps(entry.inclusion_proof),
            _json_dumps(entry.raw),
            row["id"],
        ),
    )


def _checkpoint_due(conn: Any, tenant_id: str, head: Any, now: datetime) -> bool:
    from .settings import settings

    latest = _latest_checkpoint_row(conn, tenant_id)
    covered_seq = 0 if latest is None else int(latest["covered_chain_seq"])
    head_seq = int(head["chain_seq"])
    if head_seq <= covered_seq:
        return False
    checkpoint_interval = max(1, settings.fact_chain_checkpoint_interval)
    checkpoint_max_age_s = max(1, settings.fact_chain_checkpoint_max_age_s)
    if head_seq - covered_seq >= checkpoint_interval:
        return True

    reference_time = (
        _parse_iso(head["created_at"]) if latest is None else _parse_iso(latest["created_at"])
    )
    if reference_time is None:
        return False
    return now - reference_time >= timedelta(seconds=checkpoint_max_age_s)


def _create_checkpoint_for_head(conn: Any, tenant_id: str, head: Any, now: datetime) -> Any:
    from .settings import settings

    created_at = now.isoformat()
    payload = _checkpoint_payload(head, created_at)
    checkpoint_id = f"chaincp_{uuid.uuid4().hex}"
    conn.execute(
        """
        INSERT INTO fact_chain_checkpoints
            (id, tenant_id, covered_chain_seq, chain_hash, payload, created_at, tl_backend)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            checkpoint_id,
            tenant_id,
            int(head["chain_seq"]),
            head["chain_hash"],
            _json_dumps(payload),
            created_at,
            settings.tl_backend,
        ),
    )
    return conn.execute(
        "SELECT * FROM fact_chain_checkpoints WHERE id = ?",
        (checkpoint_id,),
    ).fetchone()


def submit_due_fact_chain_checkpoints(conn: Any, tenant_id: str = "default") -> None:
    """Create and submit due L5 checkpoints without blocking fact writes."""
    now = datetime.now(UTC)
    pending = _next_pending_checkpoint(conn, tenant_id, now)
    if pending is not None:
        _submit_checkpoint_row(conn, pending, now)

    head = conn.execute(
        """
        SELECT tenant_id, chain_seq, chain_hash, created_at
        FROM fact_chain
        WHERE tenant_id = ?
        ORDER BY chain_seq DESC
        LIMIT 1
        """,
        (tenant_id,),
    ).fetchone()
    if head is None or not _checkpoint_due(conn, tenant_id, head, now):
        return
    checkpoint = _create_checkpoint_for_head(conn, tenant_id, head, now)
    _submit_checkpoint_row(conn, checkpoint, now)
