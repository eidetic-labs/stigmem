"""Unit tests for StigmemZepAdapter (mock Zep client; no live Zep required).

Run with:
    cd stigmem
    uv run pytest adapters/zep/tests/ -v
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from adapter import (
    StigmemZepAdapter,
    fact_to_message_content,
    zep_fact_to_stigmem_record,
)

SESSION_ID = "session-test-001"
SOURCE = "agent:stigmem-zep"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_adapter() -> tuple[StigmemZepAdapter, MagicMock]:
    mock_zep = MagicMock()
    adapter = StigmemZepAdapter(_zep_client=mock_zep, source_entity=SOURCE)
    return adapter, mock_zep


def _fact(
    id: str = "fact-001",
    entity: str = "user:alice",
    relation: str = "memory:role",
    value: dict | None = None,
    scope: str = "company",
    confidence: float = 1.0,
) -> dict[str, Any]:
    return {
        "id": id,
        "entity": entity,
        "relation": relation,
        "value": value or {"type": "string", "v": "engineer"},
        "source": SOURCE,
        "timestamp": "2026-05-02T00:00:00Z",
        "confidence": confidence,
        "scope": scope,
        "contradicted": False,
    }


def _mock_memory(facts: list[Any]) -> MagicMock:
    m = MagicMock()
    m.facts = facts
    return m


# ---------------------------------------------------------------------------
# fact_to_message_content
# ---------------------------------------------------------------------------

def test_fact_to_message_content_includes_stigmem_tag() -> None:
    assert "[STIGMEM]" in fact_to_message_content(_fact())


def test_fact_to_message_content_includes_entity_and_relation() -> None:
    content = fact_to_message_content(_fact(entity="user:alice", relation="memory:role"))
    assert "user:alice" in content
    assert "memory:role" in content


def test_fact_to_message_content_includes_value() -> None:
    content = fact_to_message_content(_fact(value={"type": "string", "v": "engineer"}))
    assert "engineer" in content


def test_fact_to_message_content_null_value() -> None:
    content = fact_to_message_content(_fact(value={"type": "null"}))
    assert "null" in content


def test_fact_to_message_content_includes_scope_and_confidence() -> None:
    content = fact_to_message_content(_fact(scope="team", confidence=0.75))
    assert "scope=team" in content
    assert "0.75" in content


# ---------------------------------------------------------------------------
# zep_fact_to_stigmem_record
# ---------------------------------------------------------------------------

def test_zep_fact_to_stigmem_record_shape() -> None:
    record = zep_fact_to_stigmem_record("Alice is an engineer", SESSION_ID, "company", 0)
    assert record["entity"] == f"session:{SESSION_ID}"
    assert record["relation"] == "zep:episodic_fact"
    assert record["value"] == {"type": "text", "v": "Alice is an engineer"}
    assert record["scope"] == "company"
    assert record["source"] == f"zep:{SESSION_ID}"
    assert record["contradicted"] is False
    assert record["confidence"] == 1.0


def test_zep_fact_to_stigmem_record_unique_ids() -> None:
    r0 = zep_fact_to_stigmem_record("fact a", SESSION_ID, "company", 0)
    r1 = zep_fact_to_stigmem_record("fact b", SESSION_ID, "company", 1)
    assert r0["id"] != r1["id"]
    assert r0["id"].endswith(":0")
    assert r1["id"].endswith(":1")


def test_zep_fact_to_stigmem_record_id_includes_session() -> None:
    record = zep_fact_to_stigmem_record("some fact", SESSION_ID, "local", 3)
    assert SESSION_ID in record["id"]


# ---------------------------------------------------------------------------
# assert_to_zep
# ---------------------------------------------------------------------------

def test_assert_to_zep_calls_memory_add() -> None:
    adapter, mock_zep = _mock_adapter()
    result = adapter.assert_to_zep(_fact(), SESSION_ID)
    mock_zep.memory.add.assert_called_once()
    assert result["session_id"] == SESSION_ID
    assert result["ok"] is True


def test_assert_to_zep_passes_session_id() -> None:
    adapter, mock_zep = _mock_adapter()
    adapter.assert_to_zep(_fact(), SESSION_ID)
    call_args = mock_zep.memory.add.call_args
    assert call_args.args[0] == SESSION_ID


def test_assert_to_zep_message_content_contains_fact() -> None:
    adapter, mock_zep = _mock_adapter()
    fact = _fact(entity="user:bob", relation="preference:lang", value={"type": "string", "v": "python"})
    adapter.assert_to_zep(fact, SESSION_ID)
    call_args = mock_zep.memory.add.call_args
    messages = call_args.kwargs["messages"]
    msg = messages[0]
    assert "user:bob" in msg.content
    assert "python" in msg.content
    assert "[STIGMEM]" in msg.content


def test_assert_to_zep_message_has_system_role() -> None:
    adapter, mock_zep = _mock_adapter()
    adapter.assert_to_zep(_fact(), SESSION_ID)
    call_args = mock_zep.memory.add.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0].role == "system"


def test_assert_to_zep_returns_content_in_result() -> None:
    adapter, mock_zep = _mock_adapter()
    result = adapter.assert_to_zep(_fact(entity="proj:x", relation="status:phase"), SESSION_ID)
    assert "proj:x" in result["content"]
    assert "status:phase" in result["content"]


# ---------------------------------------------------------------------------
# query_from_zep
# ---------------------------------------------------------------------------

def test_query_from_zep_returns_stigmem_records() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = _mock_memory(["Alice is an engineer", "Alice prefers Python"])
    records = adapter.query_from_zep("company", SESSION_ID)
    assert len(records) == 2
    assert all(r["relation"] == "zep:episodic_fact" for r in records)
    assert all(r["scope"] == "company" for r in records)
    assert records[0]["value"]["v"] == "Alice is an engineer"
    assert records[1]["value"]["v"] == "Alice prefers Python"


def test_query_from_zep_empty_facts() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = _mock_memory([])
    assert adapter.query_from_zep("company", SESSION_ID) == []


def test_query_from_zep_no_facts_attribute() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = MagicMock(spec=[])  # no .facts
    assert adapter.query_from_zep("company", SESSION_ID) == []


def test_query_from_zep_facts_is_none() -> None:
    adapter, mock_zep = _mock_adapter()
    mem = MagicMock()
    mem.facts = None
    mock_zep.memory.get.return_value = mem
    assert adapter.query_from_zep("company", SESSION_ID) == []


def test_query_from_zep_zep_error_returns_empty() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.side_effect = Exception("Zep unavailable")
    assert adapter.query_from_zep("company", SESSION_ID) == []


def test_query_from_zep_respects_limit() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = _mock_memory([f"fact-{i}" for i in range(100)])
    records = adapter.query_from_zep("company", SESSION_ID, limit=10)
    assert len(records) == 10


def test_query_from_zep_scope_stamped_on_records() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = _mock_memory(["some fact"])
    records = adapter.query_from_zep("team", SESSION_ID)
    assert records[0]["scope"] == "team"


def test_query_from_zep_zep_fact_objects_with_fact_attr() -> None:
    """Zep may return Fact objects with a .fact string attribute."""
    adapter, mock_zep = _mock_adapter()
    fact_obj = MagicMock()
    fact_obj.fact = "Alice is an engineer"
    del fact_obj.__str__  # ensure str() fallback not used first
    mock_zep.memory.get.return_value = _mock_memory([fact_obj])
    records = adapter.query_from_zep("company", SESSION_ID)
    assert len(records) == 1
    assert "Alice" in records[0]["value"]["v"]


def test_query_from_zep_calls_memory_get_with_session_id() -> None:
    adapter, mock_zep = _mock_adapter()
    mock_zep.memory.get.return_value = _mock_memory([])
    adapter.query_from_zep("company", SESSION_ID)
    mock_zep.memory.get.assert_called_once_with(SESSION_ID)
