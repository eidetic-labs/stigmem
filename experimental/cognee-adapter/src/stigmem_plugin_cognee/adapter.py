"""Stigmem — Cognee adapter.

Bridge between stigmem's atomic fact store and Cognee's knowledge-graph layer.

Two surfaces::

    from stigmem_plugin_cognee.adapter import StigmemCogneeAdapter

    bridge = StigmemCogneeAdapter.from_env()

    # Push a stigmem fact into Cognee's graph
    bridge.assert_to_cognee(fact_dict, dataset="stigmem")

    # Semantic search over the Cognee graph, results as stigmem-shaped records
    records = bridge.query_from_cognee(scope="company", query="What role does alice have?")

Both surfaces have async equivalents (``assert_to_cognee_async``,
``query_from_cognee_async``) for callers that already run an event loop.  The
synchronous wrappers call ``asyncio.run()`` and are safe to use from scripts or
synchronous tool-dispatch code.

Cognee is configured via environment variables (see ``from_env()``).  The
``cognee`` package itself is a lazy import so this module loads without it
installed; the bridge methods raise ``ImportError`` with a clear install hint
when ``cognee`` is absent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fact serialisation helpers
# ---------------------------------------------------------------------------

_FIELD_SEP = " | "
_KV_SEP = ":"


def _fact_to_text(fact: dict[str, Any]) -> str:
    """Serialize a stigmem fact dict to a structured text string.

    Format: ``entity:<e> | relation:<r> | value:<v> | source:<s> | scope:<sc> | confidence:<c>``

    Cognee ingests this text and extracts it as a typed graph triple.  The
    structured key-prefix format lets ``_parse_fact_text`` reconstruct the
    original fields from Cognee search results.
    """
    value = fact.get("value", {})
    if isinstance(value, dict):
        raw_v = value.get("v", "")
        if raw_v is None:
            raw_v = value.get("type", "null")
    else:
        raw_v = str(value)

    parts = [
        f"entity{_KV_SEP}{fact.get('entity', '')}",
        f"relation{_KV_SEP}{fact.get('relation', '')}",
        f"value{_KV_SEP}{raw_v}",
        f"source{_KV_SEP}{fact.get('source', '')}",
        f"scope{_KV_SEP}{fact.get('scope', 'company')}",
        f"confidence{_KV_SEP}{fact.get('confidence', 1.0)}",
    ]
    if fact.get("valid_until"):
        parts.append(f"valid_until{_KV_SEP}{fact['valid_until']}")
    if fact.get("id"):
        parts.append(f"stigmem_id{_KV_SEP}{fact['id']}")
    return _FIELD_SEP.join(parts)


def _parse_fact_text(text: str, scope: str) -> dict[str, Any]:
    """Parse a structured fact string (or raw text) into a stigmem record shape.

    Returns a dict with the same keys as ``FactRecord.model_dump()``.  Fields
    that cannot be parsed fall back to safe defaults so callers always get a
    well-shaped record, even for opaque Cognee results.
    """
    record: dict[str, Any] = {
        "id": None,
        "entity": "",
        "relation": "cognee:result",
        "value": {"type": "text", "v": text},
        "source": "cognee",
        "timestamp": None,
        "hlc": None,
        "received_from": "cognee",
        "valid_until": None,
        "confidence": 1.0,
        "scope": scope,
        "attested_key_id": None,
        "contradicted": False,
        "warnings": [],
    }

    if _FIELD_SEP not in text:
        return record

    for part in text.split(_FIELD_SEP):
        key, _, val = part.partition(_KV_SEP)
        key = key.strip()
        val = val.strip()
        if key == "entity":
            record["entity"] = val
        elif key == "relation":
            record["relation"] = val
        elif key == "value":
            record["value"] = {"type": "string", "v": val}
        elif key == "source":
            record["source"] = val
        elif key == "scope":
            record["scope"] = val
        elif key == "confidence":
            try:
                record["confidence"] = float(val)
            except ValueError:
                logger.debug("ignoring non-numeric confidence value from search result: %r", val)
        elif key == "valid_until":
            record["valid_until"] = val
        elif key == "stigmem_id":
            record["id"] = val

    return record


def _normalize_cognee_results(
    raw: list[Any],
    scope: str,
) -> list[dict[str, Any]]:
    """Map Cognee search result objects to stigmem-shaped fact dicts."""
    records: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            text = (
                item.get("text")
                or item.get("content")
                or item.get("payload", {}).get("text", "")
                or json.dumps(item)
            )
        else:
            text = str(item)
        records.append(_parse_fact_text(text.strip(), scope))
    return records


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class StigmemCogneeAdapter:
    """Bridge between stigmem facts and Cognee's knowledge graph.

    Two surfaces:

    1. **assert_to_cognee(fact, dataset)** — serialize a stigmem fact dict and
       push it into Cognee via ``cognee.add()`` + ``cognee.cognify()``.  Use
       ``batch_assert_to_cognee()`` when inserting many facts to amortise the
       ``cognify`` LLM call across the whole batch.

    2. **query_from_cognee(scope, query)** — run a semantic search over Cognee's
       graph and return results as a list of stigmem-compatible fact dicts.  The
       ``search_type`` parameter selects the Cognee ``SearchType`` variant
       (default: ``"INSIGHTS"``).
    """

    def __init__(
        self,
        default_dataset: str = "stigmem",
    ) -> None:
        self._default_dataset = default_dataset

    @classmethod
    def from_env(cls) -> StigmemCogneeAdapter:
        """Build adapter from environment variables.

        Cognee configuration variables read here::

            COGNEE_STIGMEM_DATASET   default dataset name (default: "stigmem")
            COGNEE_LLM_PROVIDER      e.g. "openai"
            COGNEE_LLM_MODEL         e.g. "gpt-4o-mini"
            COGNEE_LLM_API_KEY       API key for the LLM provider
            COGNEE_VECTOR_DB_PROVIDER  e.g. "lancedb" (default)
            COGNEE_VECTOR_DB_PATH    local path for LanceDB (default: ".cognee_db")

        LLM and vector-DB config is applied lazily on first use if the relevant
        env vars are present.
        """
        return cls(
            default_dataset=os.environ.get("COGNEE_STIGMEM_DATASET", "stigmem"),
        )

    # ------------------------------------------------------------------
    # Cognee configuration (applied lazily)
    # ------------------------------------------------------------------

    @staticmethod
    async def _apply_cognee_config() -> None:
        """Apply LLM and vector-DB config from env to the Cognee runtime."""
        try:
            import cognee  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "cognee is required for StigmemCogneeAdapter; "
                "install it with: pip install cognee"
            ) from exc

        llm_provider = os.environ.get("COGNEE_LLM_PROVIDER")
        llm_model = os.environ.get("COGNEE_LLM_MODEL")
        llm_api_key = os.environ.get("COGNEE_LLM_API_KEY")
        if llm_provider and llm_model:
            cfg: dict[str, Any] = {"provider": llm_provider, "model": llm_model}
            if llm_api_key:
                cfg["api_key"] = llm_api_key
            await cognee.config.set_llm_config(cfg)

        vdb_provider = os.environ.get("COGNEE_VECTOR_DB_PROVIDER", "lancedb")
        vdb_path = os.environ.get("COGNEE_VECTOR_DB_PATH", ".cognee_db")
        await cognee.config.set_vector_db_config(
            {"provider": vdb_provider, "url": vdb_path}
        )

    # ------------------------------------------------------------------
    # assert_to_cognee
    # ------------------------------------------------------------------

    async def assert_to_cognee_async(
        self,
        fact: dict[str, Any],
        dataset: str | None = None,
    ) -> None:
        """Push a stigmem fact into Cognee's graph (async).

        Calls ``cognee.add()`` to stage the fact text, then ``cognee.cognify()``
        to update the knowledge graph.  For bulk inserts, prefer
        ``batch_assert_to_cognee_async()`` to call ``cognify`` only once.
        """
        try:
            import cognee  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "cognee is required for StigmemCogneeAdapter; "
                "install it with: pip install cognee"
            ) from exc

        await self._apply_cognee_config()
        target = dataset or self._default_dataset
        text = _fact_to_text(fact)
        logger.debug("cognee.add dataset=%s text=%r", target, text)
        await cognee.add(text, dataset_name=target)
        await cognee.cognify(datasets=[target])

    def assert_to_cognee(
        self,
        fact: dict[str, Any],
        dataset: str | None = None,
    ) -> None:
        """Push a stigmem fact into Cognee's graph (sync wrapper)."""
        asyncio.run(self.assert_to_cognee_async(fact, dataset))

    async def batch_assert_to_cognee_async(
        self,
        facts: list[dict[str, Any]],
        dataset: str | None = None,
    ) -> None:
        """Push multiple facts into Cognee with a single ``cognify`` call (async).

        Preferred over calling ``assert_to_cognee`` in a loop — each
        ``cognify`` call invokes an LLM extraction pipeline, so batching
        amortises that cost across the whole set of facts.
        """
        try:
            import cognee  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "cognee is required for StigmemCogneeAdapter; "
                "install it with: pip install cognee"
            ) from exc

        await self._apply_cognee_config()
        target = dataset or self._default_dataset
        for fact in facts:
            text = _fact_to_text(fact)
            logger.debug("cognee.add dataset=%s text=%r", target, text)
            await cognee.add(text, dataset_name=target)
        await cognee.cognify(datasets=[target])

    def batch_assert_to_cognee(
        self,
        facts: list[dict[str, Any]],
        dataset: str | None = None,
    ) -> None:
        """Push multiple facts into Cognee with a single ``cognify`` call (sync)."""
        asyncio.run(self.batch_assert_to_cognee_async(facts, dataset))

    # ------------------------------------------------------------------
    # query_from_cognee
    # ------------------------------------------------------------------

    async def query_from_cognee_async(
        self,
        scope: str,
        query: str,
        *,
        search_type: str = "INSIGHTS",
        dataset: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over Cognee's graph, results as stigmem records (async).

        ``search_type`` maps to a Cognee ``SearchType`` variant.  Use
        ``"INSIGHTS"`` (default) for structured knowledge triples, or
        ``"GRAPH_COMPLETION"`` for LLM-composed narrative answers.

        Results are normalised to stigmem fact-shaped dicts.  Fields that
        Cognee does not carry (``id``, ``hlc``, ``timestamp``) are ``None``
        or empty so the records can be merged or displayed alongside native
        stigmem facts.
        """
        try:
            import cognee  # type: ignore[import]
            from cognee.api.v1.search import SearchType as ST  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "cognee is required for StigmemCogneeAdapter; "
                "install it with: pip install cognee"
            ) from exc

        await self._apply_cognee_config()
        st = getattr(ST, search_type, ST.INSIGHTS)
        logger.debug("cognee.search type=%s query=%r", search_type, query)
        raw = await cognee.search(st, query_text=query)
        return _normalize_cognee_results(raw, scope)

    def query_from_cognee(
        self,
        scope: str,
        query: str,
        *,
        search_type: str = "INSIGHTS",
        dataset: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over Cognee's graph (sync wrapper)."""
        return asyncio.run(
            self.query_from_cognee_async(scope, query, search_type=search_type, dataset=dataset)
        )
