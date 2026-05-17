"""ADR-016 L4 local hash chain for fact insert sequence integrity."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_HASH_PREFIX = "sha256:"


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
    }
