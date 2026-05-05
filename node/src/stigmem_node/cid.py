"""Content-addressed fact IDs — spec §25.

CID = "sha256:" + hex_lowercase(SHA-256(RFC8785(canonical_fact_body)))

The canonical body is a JSON object with exactly 7 fields in lexicographic key order:
  confidence, entity, relation, scope, source, value_type, value_v

Security-relevant excluded fields (§25.2.1 rev 14):
  valid_until, derived_from, attestation_chain, source_trust, signature, reason
  (these require independent validation; CID coverage alone is not sufficient)

fact_id and cid are also excluded (circular).
timestamp/created_at is excluded so the same assertion at different times shares one CID.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_CID_PREFIX = "sha256:"
_CID_HEX_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def compute_cid(
    entity: str,
    relation: str,
    value_type: str,
    value_v: str,
    source: str,
    scope: str,
    confidence: float = 1.0,
) -> str:
    """Return the CID for a fact's canonical body (spec §25.2.1, §25.2.2)."""
    body: dict[str, Any] = {
        "confidence": confidence,
        "entity": entity,
        "relation": relation,
        "scope": scope,
        "source": source,
        "value_type": value_type,
        "value_v": value_v,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"{_CID_PREFIX}{digest}"


def compute_cid_from_row(row: Any) -> str:
    """Convenience wrapper: compute CID from a facts-table row."""
    return compute_cid(
        entity=row["entity"],
        relation=row["relation"],
        value_type=row["value_type"],
        value_v=row["value_v"] or "",
        source=row["source"],
        scope=row["scope"],
        confidence=float(row["confidence"]),
    )


def is_valid_cid(s: str) -> bool:
    """Return True if *s* looks like a well-formed sha256 CID (spec §25.2)."""
    return bool(_CID_HEX_RE.match(s))


def is_cid(s: str) -> bool:
    """Return True if *s* starts with the sha256: prefix (quick pre-filter)."""
    return s.startswith(_CID_PREFIX)
