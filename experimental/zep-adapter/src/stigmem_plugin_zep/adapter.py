"""Stigmem — Zep adapter.

Federation model
----------------
stigmem is shared, multi-agent coordination memory: typed facts scoped across
an agent network (local / team / company / public).  Zep is per-user/session
episodic memory for a single LLM application.

This adapter bridges them at the seam:

  assert_to_zep(fact, session_id)
      A stigmem FactRecord (plain dict) is formatted as a structured system
      message and written into Zep memory for the given session.  Zep's memory
      extractor will surface it alongside the session's episodic context.

  query_from_zep(scope, session_id)
      Fetches Zep's extracted facts for the session and returns them as a list
      of stigmem-compatible FactRecord dicts that can be re-asserted on any
      stigmem node or used for query hydration.

Typical usage::

    from stigmem_plugin_zep import StigmemZepAdapter

    adapter = StigmemZepAdapter.from_env()

    # Mirror a stigmem fact into Zep
    result = adapter.assert_to_zep(fact_dict, session_id="session-123")

    # Hydrate an agent's context from Zep episodic memory
    records = adapter.query_from_zep("company", session_id="session-123")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Prefix embedded in every Zep message written by this adapter.
_STIGMEM_TAG = "[STIGMEM]"


# ---------------------------------------------------------------------------
# Minimal Message fallback (used when zep-cloud is not installed)
# ---------------------------------------------------------------------------

@dataclass
class _Message:
    """Minimal Zep message shape used when zep-cloud is absent (e.g. tests)."""
    role: str
    role_type: str
    content: str


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def fact_to_message_content(fact: dict[str, Any]) -> str:
    """Format a stigmem fact dict as a structured Zep message body."""
    entity = fact.get("entity", "")
    relation = fact.get("relation", "")
    value = fact.get("value") or {}
    v = value.get("v", "") if value.get("type") != "null" else "null"
    scope = fact.get("scope", "")
    confidence = float(fact.get("confidence", 1.0))
    return (
        f"{_STIGMEM_TAG} {entity} | {relation}: {v}"
        f" (scope={scope}, confidence={confidence:.2f})"
    )


def zep_fact_to_stigmem_record(
    fact_text: str,
    session_id: str,
    scope: str,
    idx: int,
) -> dict[str, Any]:
    """Wrap a Zep extracted fact string as a stigmem-compatible FactRecord dict."""
    return {
        "id": f"zep:{session_id}:{idx}",
        "entity": f"session:{session_id}",
        "relation": "zep:episodic_fact",
        "value": {"type": "text", "v": fact_text},
        "source": f"zep:{session_id}",
        "timestamp": None,
        "hlc": None,
        "received_from": None,
        "valid_until": None,
        "confidence": 1.0,
        "scope": scope,
        "attested_key_id": None,
        "contradicted": False,
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class StigmemZepAdapter:
    """Stigmem ↔ Zep federation bridge.

    Parameters
    ----------
    api_key:
        Zep Cloud API key.  Omit for self-hosted Zep (use ``base_url``).
    base_url:
        Base URL for a self-hosted Zep instance, e.g. ``http://localhost:8000``.
        For Zep Cloud, omit this and use ``api_key``.
    source_entity:
        Entity URI recorded as ``source`` on facts produced by this adapter.
    _zep_client:
        Inject a pre-built client for testing.  Production callers should omit.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        source_entity: str = "agent:stigmem-zep",
        *,
        _zep_client: Any = None,
    ) -> None:
        if _zep_client is not None:
            self._zep = _zep_client
        else:
            try:
                from zep_cloud.client import Zep  # type: ignore[import]
            except ImportError as exc:
                raise ImportError(
                    "zep-cloud is required; install with: pip install zep-cloud"
                ) from exc
            kwargs: dict[str, Any] = {}
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            self._zep = Zep(**kwargs)
        self._source = source_entity

    @classmethod
    def from_env(cls) -> StigmemZepAdapter:
        """Construct from environment variables.

        Optional env vars:
            ZEP_API_KEY           — Zep Cloud API key
            ZEP_BASE_URL          — base URL for self-hosted Zep
            STIGMEM_SOURCE_ENTITY — source entity URI (default: agent:stigmem-zep)
        """
        return cls(
            api_key=os.environ.get("ZEP_API_KEY"),
            base_url=os.environ.get("ZEP_BASE_URL"),
            source_entity=os.environ.get("STIGMEM_SOURCE_ENTITY", "agent:stigmem-zep"),
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def assert_to_zep(
        self,
        fact: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """Mirror a stigmem fact into Zep memory for a session.

        The fact is encoded as a ``system`` role message so Zep's memory
        extractor treats it as ground truth rather than ephemeral user input.
        Subsequent calls to :meth:`query_from_zep` will include it once Zep
        has processed the message (extraction is asynchronous).

        Parameters
        ----------
        fact:
            A stigmem FactRecord dict (plain dict, as returned by
            ``StigmemClient.assert_fact()``).
        session_id:
            Zep session ID to write into.

        Returns
        -------
        dict
            ``{"session_id": ..., "content": ..., "ok": True}`` on success.
        """
        try:
            from zep_cloud import Message  # type: ignore[import]
            msg_cls = Message
        except ImportError:
            msg_cls = _Message  # type: ignore[assignment]

        content = fact_to_message_content(fact)
        message = msg_cls(role="system", role_type="system", content=content)
        self._zep.memory.add(session_id, messages=[message])
        return {"session_id": session_id, "content": content, "ok": True}

    def query_from_zep(
        self,
        scope: str,
        session_id: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return Zep episodic facts for a session as stigmem-compatible records.

        Fetches the session's current Zep memory and returns each extracted
        fact as a stigmem FactRecord dict::

            {
                "id":       "zep:<session_id>:<idx>",
                "entity":   "session:<session_id>",
                "relation": "zep:episodic_fact",
                "value":    {"type": "text", "v": "<fact text>"},
                "scope":    <scope>,
                "source":   "zep:<session_id>",
                ...
            }

        Returns an empty list if the session has no extracted facts yet
        (Zep extracts asynchronously — retry after a few seconds if needed).

        Parameters
        ----------
        scope:
            stigmem scope to stamp on returned records (``"local"``,
            ``"team"``, ``"company"``, or ``"public"``).
        session_id:
            Zep session to query.
        limit:
            Maximum number of facts to return. Default 50.
        """
        try:
            memory = self._zep.memory.get(session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Zep memory.get(%s) failed: %s", session_id, exc)
            return []

        raw_facts: list[Any] = []
        if hasattr(memory, "facts") and memory.facts:
            raw_facts = list(memory.facts)[:limit]

        facts: list[str] = []
        for f in raw_facts:
            if isinstance(f, str):
                facts.append(f)
            elif hasattr(f, "fact"):
                facts.append(str(f.fact))
            elif hasattr(f, "content"):
                facts.append(str(f.content))
            else:
                facts.append(str(f))

        return [
            zep_fact_to_stigmem_record(text, session_id, scope, i)
            for i, text in enumerate(facts)
        ]
