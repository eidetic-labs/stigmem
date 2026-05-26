"""Unit tests for StigmemLettaAdapter (letta client mocked; no live deps required).

Run with::

    cd stigmem
    uv run pytest experimental/letta-adapter/tests/ -v
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from stigmem_plugin_letta.adapter import (
    _STIGMEM_PREFIX,
    StigmemLettaAdapter,
    _fact_to_text,
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


def _adapter() -> StigmemLettaAdapter:
    return StigmemLettaAdapter(  # noqa: S106
        letta_url="http://letta-test:8283",
        letta_token="fixture-token-value",  # noqa: S106
    )


@pytest.fixture()
def mock_letta(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a mock Letta client so tests run without the real package."""
    mock_client = MagicMock()
    mock_client.agents.archival_memory.insert = MagicMock()
    mock_client.agents.archival_memory.list = MagicMock(return_value=[])

    mock_letta_module = MagicMock()
    mock_letta_module.Letta.return_value = mock_client
    sys.modules["letta"] = mock_letta_module

    return mock_client


# ---------------------------------------------------------------------------
# _fact_to_text
# ---------------------------------------------------------------------------

def test_fact_to_text_has_prefix() -> None:
    text = _fact_to_text(_fact())
    assert text.startswith(_STIGMEM_PREFIX)


def test_fact_to_text_contains_fields() -> None:
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


def test_fact_to_text_valid_until() -> None:
    f = _fact()
    f["valid_until"] = "2026-12-31T00:00:00Z"
    text = _fact_to_text(f)
    assert "valid_until:2026-12-31T00:00:00Z" in text


# ---------------------------------------------------------------------------
# _parse_fact_text round-trip
# ---------------------------------------------------------------------------

def test_parse_round_trip_with_prefix() -> None:
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


def test_parse_non_stigmem_text_fallback() -> None:
    text = "Alice told me about her favourite project yesterday."
    parsed = _parse_fact_text(text, scope="team")
    assert parsed["entity"] == ""
    assert parsed["relation"] == "letta:archival_memory"
    assert parsed["value"] == {"type": "text", "v": text}
    assert parsed["scope"] == "team"
    assert parsed["contradicted"] is False


def test_parse_confidence_float() -> None:
    f = _fact(confidence=0.8)
    text = _fact_to_text(f)
    parsed = _parse_fact_text(text, scope="company")
    assert abs(parsed["confidence"] - 0.8) < 1e-9


# ---------------------------------------------------------------------------
# StigmemLettaAdapter.from_env
# ---------------------------------------------------------------------------

def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LETTA_URL", raising=False)
    monkeypatch.delenv("LETTA_TOKEN", raising=False)
    adapter = StigmemLettaAdapter.from_env()
    assert adapter._letta_url == "http://localhost:8283"
    assert adapter._letta_token is None


def test_from_env_reads_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LETTA_URL", "http://my-letta:9000")
    adapter = StigmemLettaAdapter.from_env()
    assert adapter._letta_url == "http://my-letta:9000"


def test_from_env_reads_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token_value = "fixture-token-value"  # noqa: S105
    monkeypatch.setenv("LETTA_URL", "http://letta")
    monkeypatch.setenv("LETTA_TOKEN", token_value)
    adapter = StigmemLettaAdapter.from_env()
    assert adapter._letta_token == token_value


# ---------------------------------------------------------------------------
# push_to_letta
# ---------------------------------------------------------------------------

def test_push_to_letta_calls_insert(mock_letta: MagicMock) -> None:
    adapter = _adapter()
    adapter.push_to_letta(_fact(), agent_id="agent-abc")

    mock_letta.agents.archival_memory.insert.assert_called_once()
    call_kwargs = mock_letta.agents.archival_memory.insert.call_args
    assert call_kwargs.kwargs["agent_id"] == "agent-abc"
    text = call_kwargs.kwargs["text"]
    assert text.startswith(_STIGMEM_PREFIX)
    assert "entity:user:alice" in text


def test_push_to_letta_serializes_fact(mock_letta: MagicMock) -> None:
    adapter = _adapter()
    adapter.push_to_letta(_fact(entity="project:loom", relation="roadmap:phase"), agent_id="x")
    text = mock_letta.agents.archival_memory.insert.call_args.kwargs["text"]
    assert "entity:project:loom" in text
    assert "relation:roadmap:phase" in text


def test_batch_push_calls_insert_n_times(mock_letta: MagicMock) -> None:
    adapter = _adapter()
    facts = [_fact(entity=f"user:{i}", id=f"f-{i}") for i in range(4)]
    adapter.batch_push_to_letta(facts, agent_id="agent-abc")
    assert mock_letta.agents.archival_memory.insert.call_count == 4


# ---------------------------------------------------------------------------
# pull_from_letta
# ---------------------------------------------------------------------------

class _MockPassage:
    def __init__(self, text: str) -> None:
        self.text = text


def test_pull_returns_empty_on_no_passages(mock_letta: MagicMock) -> None:
    mock_letta.agents.archival_memory.list.return_value = []
    adapter = _adapter()
    records = adapter.pull_from_letta("agent-abc", scope="company")
    assert records == []


def test_pull_parses_stigmem_fact(mock_letta: MagicMock) -> None:
    f = _fact()
    text = _fact_to_text(f)
    mock_letta.agents.archival_memory.list.return_value = [_MockPassage(text)]

    adapter = _adapter()
    records = adapter.pull_from_letta("agent-abc", scope="company")
    assert len(records) == 1
    assert records[0]["entity"] == "user:alice"
    assert records[0]["relation"] == "memory:role"


def test_pull_includes_non_stigmem_by_default(mock_letta: MagicMock) -> None:
    passages = [
        _MockPassage(_fact_to_text(_fact())),
        _MockPassage("Some other memory the agent accumulated."),
    ]
    mock_letta.agents.archival_memory.list.return_value = passages

    adapter = _adapter()
    records = adapter.pull_from_letta("agent-abc", scope="company")
    assert len(records) == 2
    assert records[1]["relation"] == "letta:archival_memory"


def test_pull_stigmem_only_filters(mock_letta: MagicMock) -> None:
    passages = [
        _MockPassage(_fact_to_text(_fact())),
        _MockPassage("Some other memory."),
    ]
    mock_letta.agents.archival_memory.list.return_value = passages

    adapter = _adapter()
    records = adapter.pull_from_letta("agent-abc", scope="company", stigmem_only=True)
    assert len(records) == 1
    assert records[0]["entity"] == "user:alice"


def test_pull_passes_limit(mock_letta: MagicMock) -> None:
    mock_letta.agents.archival_memory.list.return_value = []
    adapter = _adapter()
    adapter.pull_from_letta("agent-abc", scope="company", limit=25)
    mock_letta.agents.archival_memory.list.assert_called_once_with(
        agent_id="agent-abc", limit=25
    )


# ---------------------------------------------------------------------------
# ImportError surface — letta not installed
# ---------------------------------------------------------------------------

def test_push_raises_import_error_without_letta(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    real_import = builtins.__import__

    for key in list(sys.modules.keys()):
        if "letta" in key:
            sys.modules.pop(key, None)

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "letta":
            raise ImportError("No module named 'letta'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    adapter = _adapter()
    with pytest.raises(ImportError, match="pip install letta"):
        adapter.push_to_letta(_fact(), agent_id="x")
