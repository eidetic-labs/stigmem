"""Idempotent fact ingestion from federated peers (spec §6.3, §6.5).

ingest_fact() is the single entry-point for all federated facts.
It is safe to call multiple times for the same fact (no-op after first write).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .db import db
from .hlc import node_hlc


def _encode_v(value: dict[str, Any]) -> str:
    vtype = value["type"]
    v = value.get("v")
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)


def ingest_fact(
    fact: dict[str, Any],
    sender_node_id: str,
    origin_node_id: str | None = None,
    origin_allowed_scopes: list[str] | None = None,
) -> bool:
    """Idempotently ingest a federated fact.

    Returns True if the fact was new, False if it already existed (no-op).
    Writes stigmem:received_from meta-fact atomically with the fact.
    Advances the local HLC.
    Detects contradictions and writes conflict entities (spec §6.5, §3.3).

    origin_node_id / origin_allowed_scopes populate the v0.8 scope-propagation
    columns (spec §6.8.1, Migration 004). When None, defaults to sender_node_id
    and the fact's scope as a single-element list (first-hop inference).

    Company-scope facts are re_federation_blocked=1 by default (spec §6.8.2):
    the originating node's grant is non-transitive.
    """
    fact_id = fact["id"]
    scope = fact["scope"]

    # Scope-propagation columns (spec §6.8.1)
    eff_origin_node_id = origin_node_id or sender_node_id
    eff_origin_scopes: str | None
    if origin_allowed_scopes is not None:
        eff_origin_scopes = json.dumps(sorted(origin_allowed_scopes))
    else:
        eff_origin_scopes = json.dumps([scope])
    # company-scope facts: re-federation is blocked by default (§6.8.2)
    re_fed_blocked = 1 if scope == "company" else 0

    with db() as conn:
        existing = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_id,)).fetchone()
        if existing is not None:
            return False  # already ingested; silent no-op per spec §5.8

        # Advance HLC (spec §6.3)
        remote_hlc = fact.get("hlc")
        new_hlc = node_hlc.receive(remote_hlc) if remote_hlc else node_hlc.tick()

        # Insert the fact with received_from + scope-propagation columns (Migration 004)
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from,
                origin_node_id, origin_allowed_scopes, re_federation_blocked)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact_id,
                fact["entity"],
                fact["relation"],
                fact["value"]["type"],
                _encode_v(fact["value"]),
                fact["source"],
                fact["timestamp"],
                fact.get("valid_until"),
                fact["confidence"],
                scope,
                new_hlc,
                sender_node_id,
                eff_origin_node_id,
                eff_origin_scopes,
                re_fed_blocked,
            ),
        )

        # Write stigmem:received_from meta-fact atomically (spec §3.1)
        meta_id = str(uuid.uuid4())
        meta_now = datetime.now(UTC).isoformat()
        meta_hlc = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                meta_id,
                fact_id,           # entity = the ingested fact's ID
                "stigmem:received_from",
                "ref",
                sender_node_id,
                "system:stigmem",
                meta_now,
                None,
                1.0,
                "local",           # meta-facts are local; MUST NOT be re-replicated (spec §3.1)
                meta_hlc,
                None,
            ),
        )

        # Contradiction detection (spec §3.3, §6.5)
        _detect_and_record_contradiction(conn, fact, fact_id)

    return True


_STIGMEM_NS = "stigmem:"
_STIGMEM_URI_NS = "stigmem://"


def _is_reserved_stigmem(s: str) -> bool:
    """True for bare stigmem: system names (e.g. 'stigmem:conflict:x').
    False for stigmem:// URI entities which are user content."""
    return s.startswith(_STIGMEM_NS) and not s.startswith(_STIGMEM_URI_NS)


def _detect_and_record_contradiction(
    conn: Any,
    fact: dict[str, Any],
    fact_id: str,
) -> None:
    """If a contradiction exists, assert conflict entities and write conflicts table."""
    # Reserved stigmem: facts are system state (status transitions, meta-facts), not
    # semantic content. Two stigmem:conflict:status facts with different values represent
    # a state transition, not a contradiction — exempt them from sibling-detection (§9.1).
    # Note: stigmem:// URI entities are user content and ARE subject to detection.
    if _is_reserved_stigmem(fact["entity"]) or _is_reserved_stigmem(fact["relation"]):
        return

    siblings = conn.execute(
        """SELECT id FROM facts
           WHERE entity = ? AND relation = ? AND scope = ?
             AND id != ? AND confidence > 0.0""",
        (fact["entity"], fact["relation"], fact["scope"], fact_id),
    ).fetchall()

    if not siblings:
        return

    now = datetime.now(UTC).isoformat()

    for sibling in siblings:
        sibling_id = sibling["id"]
        conflict_uuid = str(uuid.uuid4())
        conflict_id = f"stigmem:conflict:{conflict_uuid}"

        # Skip if this pair already has a conflict record
        already = conn.execute(
            """SELECT c.id FROM conflicts c
               WHERE (c.fact_a_id = ? AND c.fact_b_id = ?)
                  OR (c.fact_a_id = ? AND c.fact_b_id = ?)""",
            (fact_id, sibling_id, sibling_id, fact_id),
        ).fetchone()
        if already:
            continue

        hlc_between = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                conflict_id,
                "stigmem:conflict:between",
                "text",
                f"{fact_id} {sibling_id}",
                "system:stigmem",
                now,
                None,
                1.0,
                fact["scope"],
                hlc_between,
                None,
            ),
        )

        hlc_status = node_hlc.tick()
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                conflict_id,
                "stigmem:conflict:status",
                "string",
                "unresolved",
                "system:stigmem",
                now,
                None,
                1.0,
                fact["scope"],
                hlc_status,
                None,
            ),
        )

        conn.execute(
            """INSERT OR IGNORE INTO conflicts (id, fact_a_id, fact_b_id, status, detected_at)
               VALUES (?,?,?,?,?)""",
            (conflict_id, fact_id, sibling_id, "unresolved", now),
        )


def write_audit_log(
    peer_id: str,
    event_type: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Write a federation audit log entry (spec §6.4)."""
    entry_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_audit (id, peer_id, event_type, detail, ts) VALUES (?,?,?,?,?)",
            (entry_id, peer_id, event_type, json.dumps(detail) if detail else None, now),
        )
