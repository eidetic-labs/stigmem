"""Stigmem — Letta adapter.

Bridge between Stigmem (federated fact store, shared across agents) and Letta
(per-agent persistent memory: archival memory + core memory blocks).

Federation model
----------------
Stigmem is shared coordination memory across agent networks.
Letta is per-agent in-context memory within a single agent runtime.

The adapter writes Stigmem facts into a Letta agent's archival memory as
``[stigmem]``-tagged passages and reads them back as Stigmem-compatible
records. Non-Stigmem passages (native Letta memories) are optionally included
in reads and returned with a ``letta:archival_memory`` relation.

Typical usage::

    from adapter import StigmemLettaAdapter

    adapter = StigmemLettaAdapter.from_env()

    # Push a fact into a Letta agent's archival memory
    adapter.push_to_letta(fact_dict, agent_id="agent-<uuid>")

    # Seed from a list of facts
    adapter.batch_push_to_letta(facts, agent_id="agent-<uuid>")

    # Read facts back from the agent
    records = adapter.pull_from_letta("agent-<uuid>", scope="company")

Requires the ``letta`` Python package (``pip install letta``).  The import is
lazy so the module can be imported without installing letta — the error is
raised only when a push or pull is attempted.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

#: Prefix used to tag archival passages that originated from Stigmem.
#: Passages that do NOT start with this prefix are either returned as
#: fallback records or filtered out (when stigmem_only=True).
_STIGMEM_PREFIX = "[stigmem]"


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def _fact_to_text(fact: dict[str, Any]) -> str:
    """Serialise a Stigmem fact dict into a Letta archival memory passage.

    The passage is a ``_STIGMEM_PREFIX``-tagged block of newline-separated
    ``key:value`` pairs.  The value scalar (``v``) is stored as a plain
    string on the ``value`` line; the type discriminant is stored separately
    on ``value_type``.  This lets callers do quick substring checks like
    ``"value:engineer" in text`` while still enabling full round-trips.

    Null facts encode as ``value:null`` (no ``value_type`` line needed, but
    ``value_type:null`` is always written for consistency).
    """
    value = fact.get("value") or {"type": "null"}
    vtype: str = value.get("type", "null")
    v = value.get("v")

    if vtype == "null" or v is None:
        vstr = "null"
    else:
        vstr = str(v)

    lines = [
        _STIGMEM_PREFIX,
        f"entity:{fact.get('entity', '')}",
        f"relation:{fact.get('relation', '')}",
        f"value:{vstr}",
        f"value_type:{vtype}",
        f"source:{fact.get('source', '')}",
        f"scope:{fact.get('scope', 'company')}",
        f"confidence:{fact.get('confidence', 1.0)}",
        f"stigmem_id:{fact.get('id', '')}",
    ]
    if fact.get("valid_until"):
        lines.append(f"valid_until:{fact['valid_until']}")

    return "\n".join(lines)


def _parse_fact_text(text: str, scope: str) -> dict[str, Any]:
    """Parse a Letta archival passage into a Stigmem-compatible fact dict.

    If the passage does not start with ``_STIGMEM_PREFIX``, a fallback record
    is returned with ``relation="letta:archival_memory"`` and the raw text as
    a ``text``-typed value — so non-Stigmem native memories are still surfaced
    as queryable records.
    """
    stripped = text.strip()

    if not stripped.startswith(_STIGMEM_PREFIX):
        return {
            "id": "",
            "entity": "",
            "relation": "letta:archival_memory",
            "value": {"type": "text", "v": text},
            "source": "",
            "scope": scope,
            "confidence": 1.0,
            "contradicted": False,
        }

    fields: dict[str, str] = {}
    for line in stripped.splitlines()[1:]:  # skip the prefix line
        if ":" in line:
            key, val = line.split(":", 1)
            fields[key.strip()] = val.strip()

    vtype = fields.get("value_type", "string")
    vstr = fields.get("value", "")

    if vtype == "null":
        value: dict[str, Any] = {"type": "null"}
    elif vtype == "number":
        value = {"type": "number", "v": float(vstr)}
    elif vtype == "boolean":
        value = {"type": "boolean", "v": vstr.lower() == "true"}
    else:
        value = {"type": vtype, "v": vstr}

    result: dict[str, Any] = {
        "id": fields.get("stigmem_id", ""),
        "entity": fields.get("entity", ""),
        "relation": fields.get("relation", ""),
        "value": value,
        "source": fields.get("source", ""),
        "scope": fields.get("scope", scope),
        "confidence": float(fields.get("confidence", "1.0")),
        "contradicted": False,
    }
    if "valid_until" in fields:
        result["valid_until"] = fields["valid_until"]
    return result


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class StigmemLettaAdapter:
    """Bridge between Stigmem facts and Letta agent archival memory.

    Parameters
    ----------
    letta_url:
        Base URL of the Letta server, e.g. ``http://localhost:8283``.
    letta_token:
        Optional bearer token for the Letta server.
    """

    def __init__(
        self,
        letta_url: str = "http://localhost:8283",
        letta_token: str | None = None,
    ) -> None:
        self._letta_url = letta_url
        self._letta_token = letta_token

    @classmethod
    def from_env(cls) -> "StigmemLettaAdapter":
        """Construct from environment variables.

        ``LETTA_URL``   — Letta server base URL (default: ``http://localhost:8283``)
        ``LETTA_TOKEN`` — optional bearer token
        """
        return cls(
            letta_url=os.environ.get("LETTA_URL", "http://localhost:8283"),
            letta_token=os.environ.get("LETTA_TOKEN"),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _client(self) -> Any:
        """Return a Letta client instance (lazy import)."""
        try:
            import letta  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "letta is required for StigmemLettaAdapter; install with: pip install letta"
            ) from exc
        return letta.Letta(base_url=self._letta_url, token=self._letta_token)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def push_to_letta(self, fact: dict[str, Any], *, agent_id: str) -> None:
        """Insert a Stigmem fact into a Letta agent's archival memory.

        The fact is serialised as a ``[stigmem]``-tagged passage via
        :func:`_fact_to_text` and inserted via
        ``client.agents.archival_memory.insert``.
        """
        client = self._client()
        text = _fact_to_text(fact)
        client.agents.archival_memory.insert(agent_id=agent_id, text=text)

    def batch_push_to_letta(
        self, facts: list[dict[str, Any]], *, agent_id: str
    ) -> None:
        """Insert multiple Stigmem facts into a Letta agent's archival memory."""
        for fact in facts:
            self.push_to_letta(fact, agent_id=agent_id)

    def pull_from_letta(
        self,
        agent_id: str,
        scope: str,
        *,
        stigmem_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Read a Letta agent's archival memory as Stigmem-compatible records.

        Parameters
        ----------
        agent_id:
            The Letta agent to read from.
        scope:
            Scope string to attach to fallback records (non-Stigmem passages).
        stigmem_only:
            If ``True``, skip passages that are not tagged with
            ``_STIGMEM_PREFIX``.  Default ``False`` — native Letta memories
            are returned with ``relation="letta:archival_memory"``.
        limit:
            Maximum number of passages to retrieve from Letta.
        """
        client = self._client()
        passages = client.agents.archival_memory.list(agent_id=agent_id, limit=limit)

        records: list[dict[str, Any]] = []
        for passage in passages:
            text: str = passage.text if hasattr(passage, "text") else str(passage)
            if stigmem_only and not text.strip().startswith(_STIGMEM_PREFIX):
                continue
            records.append(_parse_fact_text(text, scope=scope))
        return records
