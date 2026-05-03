"""Unit tests for StigmemCogneeAdapter (cognee mocked; no live node required).

Run with::

    cd stigmem
    uv run pytest adapters/cognee/tests/ -v

No live stigmem node or Cognee/LLM API key required.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# conftest.py adds the adapter directory to sys.path
from adapter import (
    StigmemCogneeAdapter,
    _fact_to_text,
    _normalize_cognee_results,
    _parse_fact_text,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _fact(
    entity: str = "user:alice",
    relation: str = "memory:role",
    value: dict | None = None,
    source: str = "agent:test",
    scope: str = "company",
    confidence: float = 1.0,
    id: str | None = "fact-001",
) -> dict[str, Any]:
    return {
        "id": id,
        "entity": entity,
        "relation": relation,
        "value": value or {"type": "string", "v": "engineer"},
        "source": source,
        "scope": scope,
        "confidence": confidence,
        "timestamp": "2026-05-02T00:00:00Z",
        "contradicted": False,
        "warnings": [],
    }


def _adapter() -> StigmemCogneeAdapter:
    return StigmemCogneeAdapter(default_dataset="test_dataset")


# ---------------------------------------------------------------------------
# _fact_to_text
# ---------------------------------------------------------------------------

def test_fact_to_text_basic() -> None:
    text = _fact_to_text(_fact())
    assert "entity:user:alice" in text
    assert "relation:memory:role" in text
    assert "value:engineer" in text
    assert "source:agent:test" in text
    assert "scope:company" in text
    assert "confidence:1.0" in text


def test_fact_to_text_includes_id() -> None:
    text = _fact_to_text(_fact(id="abc-123"))
    assert "stigmem_id:abc-123" in text


def test_fact_to_text_null_value() -> None:
    text = _fact_to_text(_fact(value={"type": "null", "v": None}))
    assert "value:null" in text


def test_fact_to_text_ref_value() -> None:
    text = _fact_to_text(_fact(value={"type": "ref", "v": "project:loom"}))
    assert "value:project:loom" in text


def test_fact_to_text_valid_until() -> None:
    f = _fact()
    f["valid_until"] = "2026-12-31T00:00:00Z"
    text = _fact_to_text(f)
    assert "valid_until:2026-12-31T00:00:00Z" in text


# ---------------------------------------------------------------------------
# _parse_fact_text round-trip
# ---------------------------------------------------------------------------

def test_parse_round_trip() -> None:
    original = _fact()
    text = _fact_to_text(original)
    parsed = _parse_fact_text(text, scope="company")
    assert parsed["entity"] == "user:alice"
    assert parsed["relation"] == "memory:role"
    assert parsed["value"] == {"type": "string", "v": "engineer"}
    assert parsed["source"] == "agent:test"
    assert parsed["scope"] == "company"
    assert parsed["confidence"] == 1.0
    assert parsed["id"] == "fact-001"


def test_parse_opaque_text_falls_back_to_raw() -> None:
    text = "Cognee returned something opaque"
    parsed = _parse_fact_text(text, scope="team")
    assert parsed["entity"] == ""
    assert parsed["relation"] == "cognee:result"
    assert parsed["value"] == {"type": "text", "v": text}
    assert parsed["scope"] == "team"
    assert parsed["contradicted"] is False


def test_parse_preserves_confidence_float() -> None:
    f = _fact(confidence=0.75)
    text = _fact_to_text(f)
    parsed = _parse_fact_text(text, scope="company")
    assert abs(parsed["confidence"] - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# _normalize_cognee_results
# ---------------------------------------------------------------------------

def test_normalize_dict_results() -> None:
    raw = [{"text": "entity:x | relation:r | value:v | source:s | scope:company | confidence:1.0"}]
    records = _normalize_cognee_results(raw, "company")
    assert len(records) == 1
    assert records[0]["entity"] == "x"
    assert records[0]["relation"] == "r"


def test_normalize_string_results() -> None:
    raw = ["entity:x | relation:r | value:v | source:s | scope:team | confidence:1.0"]
    records = _normalize_cognee_results(raw, "team")
    assert records[0]["scope"] == "team"


def test_normalize_empty_results() -> None:
    assert _normalize_cognee_results([], "company") == []
    assert _normalize_cognee_results(None, "company") == []  # type: ignore[arg-type]


def test_normalize_dict_content_key() -> None:
    raw = [{"content": "entity:a | relation:b | value:c | source:d | scope:local | confidence:0.9"}]
    records = _normalize_cognee_results(raw, "local")
    assert records[0]["entity"] == "a"


def test_normalize_dict_fallback_to_json_dump() -> None:
    raw = [{"unknown_key": "some_value"}]
    records = _normalize_cognee_results(raw, "company")
    assert len(records) == 1
    assert records[0]["relation"] == "cognee:result"


# ---------------------------------------------------------------------------
# StigmemCogneeAdapter.from_env
# ---------------------------------------------------------------------------

def test_from_env_uses_default_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COGNEE_STIGMEM_DATASET", raising=False)
    adapter = StigmemCogneeAdapter.from_env()
    assert adapter._default_dataset == "stigmem"


def test_from_env_reads_dataset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNEE_STIGMEM_DATASET", "my_facts")
    adapter = StigmemCogneeAdapter.from_env()
    assert adapter._default_dataset == "my_facts"


# ---------------------------------------------------------------------------
# assert_to_cognee_async — mocked cognee
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_cognee(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a mock cognee module so tests run without the real package."""
    cognee_mock = MagicMock()
    cognee_mock.add = AsyncMock()
    cognee_mock.cognify = AsyncMock()
    cognee_mock.search = AsyncMock(return_value=[])
    cognee_mock.config = MagicMock()
    cognee_mock.config.set_llm_config = AsyncMock()
    cognee_mock.config.set_vector_db_config = AsyncMock()

    # Patch both the import inside the adapter module and sys.modules
    sys.modules["cognee"] = cognee_mock
    # Also mock cognee.api.v1.search for SearchType
    search_mod = MagicMock()
    search_mod.SearchType = MagicMock()
    search_mod.SearchType.INSIGHTS = "INSIGHTS"
    search_mod.SearchType.GRAPH_COMPLETION = "GRAPH_COMPLETION"
    sys.modules["cognee.api"] = MagicMock()
    sys.modules["cognee.api.v1"] = MagicMock()
    sys.modules["cognee.api.v1.search"] = search_mod

    return cognee_mock


def test_assert_to_cognee_calls_add_and_cognify(mock_cognee: MagicMock) -> None:
    adapter = _adapter()
    asyncio.run(adapter.assert_to_cognee_async(_fact(), dataset="test_ds"))

    mock_cognee.add.assert_awaited_once()
    call_args = mock_cognee.add.call_args
    text_arg = call_args[0][0]
    assert "entity:user:alice" in text_arg
    assert call_args[1]["dataset_name"] == "test_ds"

    mock_cognee.cognify.assert_awaited_once_with(datasets=["test_ds"])


def test_assert_to_cognee_uses_default_dataset(mock_cognee: MagicMock) -> None:
    adapter = _adapter()
    asyncio.run(adapter.assert_to_cognee_async(_fact()))

    call_args = mock_cognee.add.call_args
    assert call_args[1]["dataset_name"] == "test_dataset"


def test_batch_assert_calls_add_n_times_cognify_once(mock_cognee: MagicMock) -> None:
    adapter = _adapter()
    facts = [_fact(entity=f"user:{i}", id=f"f-{i}") for i in range(3)]
    asyncio.run(adapter.batch_assert_to_cognee_async(facts))

    assert mock_cognee.add.await_count == 3
    mock_cognee.cognify.assert_awaited_once()


def test_assert_applies_llm_config_when_env_set(
    mock_cognee: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COGNEE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("COGNEE_LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("COGNEE_LLM_API_KEY", "sk-test")

    adapter = _adapter()
    asyncio.run(adapter.assert_to_cognee_async(_fact()))

    mock_cognee.config.set_llm_config.assert_awaited_once_with(
        {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"}
    )


def test_assert_skips_llm_config_when_env_absent(
    mock_cognee: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COGNEE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("COGNEE_LLM_MODEL", raising=False)

    adapter = _adapter()
    asyncio.run(adapter.assert_to_cognee_async(_fact()))

    mock_cognee.config.set_llm_config.assert_not_awaited()


# ---------------------------------------------------------------------------
# query_from_cognee_async — mocked cognee
# ---------------------------------------------------------------------------

def test_query_returns_normalized_records(mock_cognee: MagicMock) -> None:
    f = _fact()
    text = (
        f"entity:{f['entity']} | relation:{f['relation']} | "
        f"value:engineer | source:cognee | scope:company | confidence:1.0"
    )
    mock_cognee.search = AsyncMock(return_value=[{"text": text}])

    adapter = _adapter()
    results = asyncio.run(adapter.query_from_cognee_async("company", "What role?"))

    assert len(results) == 1
    assert results[0]["entity"] == f["entity"]
    assert results[0]["relation"] == f["relation"]


def test_query_returns_empty_on_no_results(mock_cognee: MagicMock) -> None:
    mock_cognee.search = AsyncMock(return_value=[])
    adapter = _adapter()
    results = asyncio.run(adapter.query_from_cognee_async("company", "anything"))
    assert results == []


def test_query_passes_search_type(mock_cognee: MagicMock) -> None:
    mock_cognee.search = AsyncMock(return_value=[])
    adapter = _adapter()
    asyncio.run(
        adapter.query_from_cognee_async("company", "test", search_type="GRAPH_COMPLETION")
    )
    mock_cognee.search.assert_awaited_once()


# ---------------------------------------------------------------------------
# ImportError surface — cognee not installed
# ---------------------------------------------------------------------------

def test_assert_raises_import_error_without_cognee(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(sys.modules.keys()):
        if "cognee" in key:
            sys.modules.pop(key, None)

    import builtins
    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "cognee":
            raise ImportError("No module named 'cognee'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    adapter = _adapter()
    with pytest.raises(ImportError, match="pip install cognee"):
        asyncio.run(adapter.assert_to_cognee_async(_fact()))
