"""Unit tests for StigmemGeminiAdapter (respx-mocked; no live node or Gemini key required).

Run with::

    cd stigmem
    uv run pytest adapters/gemini/tests/ -v
"""

from __future__ import annotations

import json
import os

import httpx
import pytest
import respx

# conftest.py adds the adapter directory to sys.path
from adapter import STIGMEM_FUNCTION_DECLARATIONS, StigmemGeminiAdapter

BASE = "http://test-stigmem"
SOURCE = "agent:gemini"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fact(
    id: str = "fact-001",
    entity: str = "user:alice",
    relation: str = "memory:role",
    value: dict | None = None,
    source: str = SOURCE,
    confidence: float = 1.0,
    scope: str = "company",
) -> dict:
    return {
        "id": id,
        "entity": entity,
        "relation": relation,
        "value": value or {"type": "string", "v": "engineer"},
        "source": source,
        "timestamp": "2026-05-02T00:00:00Z",
        "hlc": None,
        "received_from": None,
        "valid_until": None,
        "confidence": confidence,
        "scope": scope,
        "attested_key_id": None,
        "contradicted": False,
        "warnings": [],
    }


def _page(facts: list[dict], cursor: str | None = None) -> dict:
    return {"facts": facts, "total": len(facts), "cursor": cursor}


def _adapter() -> StigmemGeminiAdapter:
    return StigmemGeminiAdapter(url=BASE, api_key="sk-test", source_entity=SOURCE)


# ---------------------------------------------------------------------------
# STIGMEM_FUNCTION_DECLARATIONS schema
# ---------------------------------------------------------------------------

def test_declarations_contains_five_tools() -> None:
    names = [d["name"] for d in STIGMEM_FUNCTION_DECLARATIONS]
    assert names == [
        "assert_fact",
        "query_facts",
        "resolve_contradiction",
        "subscribe_scope",
        "lint_scope",
    ]


def test_declarations_use_uppercase_types() -> None:
    for decl in STIGMEM_FUNCTION_DECLARATIONS:
        assert decl["parameters"]["type"] == "OBJECT", (
            f"{decl['name']}: top-level type must be OBJECT"
        )
    # assert_fact entity is STRING
    assert_fact = next(d for d in STIGMEM_FUNCTION_DECLARATIONS if d["name"] == "assert_fact")
    assert assert_fact["parameters"]["properties"]["entity"]["type"] == "STRING"
    assert assert_fact["parameters"]["properties"]["confidence"]["type"] == "NUMBER"


def test_declarations_required_fields() -> None:
    assert_fact = next(d for d in STIGMEM_FUNCTION_DECLARATIONS if d["name"] == "assert_fact")
    assert "entity" in assert_fact["parameters"]["required"]
    assert "relation" in assert_fact["parameters"]["required"]
    assert "value" in assert_fact["parameters"]["required"]
    assert "source" in assert_fact["parameters"]["required"]


def test_query_facts_has_no_required_fields() -> None:
    qf = next(d for d in STIGMEM_FUNCTION_DECLARATIONS if d["name"] == "query_facts")
    assert qf["parameters"]["required"] == []


def test_lint_scope_has_array_checks() -> None:
    lint = next(d for d in STIGMEM_FUNCTION_DECLARATIONS if d["name"] == "lint_scope")
    checks = lint["parameters"]["properties"]["checks"]
    assert checks["type"] == "ARRAY"
    assert checks["items"]["type"] == "STRING"


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------

def test_from_env_reads_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://env-node")
    monkeypatch.delenv("STIGMEM_API_KEY", raising=False)
    monkeypatch.delenv("STIGMEM_SOURCE_ENTITY", raising=False)
    adapter = StigmemGeminiAdapter.from_env()
    assert adapter._client._url == "http://env-node"


def test_from_env_default_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://env-node")
    monkeypatch.delenv("STIGMEM_SOURCE_ENTITY", raising=False)
    adapter = StigmemGeminiAdapter.from_env()
    assert adapter._source == "agent:gemini"


def test_from_env_reads_source_entity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://env-node")
    monkeypatch.setenv("STIGMEM_SOURCE_ENTITY", "agent:mybot")
    adapter = StigmemGeminiAdapter.from_env()
    assert adapter._source == "agent:mybot"


def test_from_env_reads_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://env-node")
    monkeypatch.setenv("STIGMEM_GEMINI_MODEL", "gemini-1.5-pro")
    adapter = StigmemGeminiAdapter.from_env()
    assert adapter._model == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# gemini_tools()
# ---------------------------------------------------------------------------

def test_gemini_tools_returns_declarations() -> None:
    adapter = _adapter()
    tools = adapter.gemini_tools()
    assert tools is STIGMEM_FUNCTION_DECLARATIONS
    assert len(tools) == 5


# ---------------------------------------------------------------------------
# dispatch — assert_fact
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_assert_fact() -> None:
    f = _fact()
    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=f))

    adapter = _adapter()
    result_json = adapter.dispatch("assert_fact", {
        "entity": "user:alice",
        "relation": "memory:role",
        "value": {"type": "string", "v": "engineer"},
        "source": SOURCE,
    })
    result = json.loads(result_json)
    assert result["entity"] == "user:alice"
    assert result["relation"] == "memory:role"


@respx.mock
def test_dispatch_assert_fact_uses_default_source() -> None:
    f = _fact()
    route = respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=f))

    adapter = _adapter()
    adapter.dispatch("assert_fact", {
        "entity": "user:alice",
        "relation": "memory:role",
        "value": {"type": "string", "v": "engineer"},
        # no source supplied
    })
    sent = json.loads(route.calls[0].request.content)
    assert sent["source"] == SOURCE


# ---------------------------------------------------------------------------
# dispatch — query_facts
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_query_facts() -> None:
    page = _page([_fact()])
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=page))

    adapter = _adapter()
    result_json = adapter.dispatch("query_facts", {"entity": "user:alice"})
    result = json.loads(result_json)
    assert result["total"] == 1
    assert result["facts"][0]["entity"] == "user:alice"


@respx.mock
def test_dispatch_query_facts_no_filters() -> None:
    page = _page([])
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=page))

    adapter = _adapter()
    result_json = adapter.dispatch("query_facts", {})
    result = json.loads(result_json)
    assert result["facts"] == []


# ---------------------------------------------------------------------------
# dispatch — subscribe_scope
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_subscribe_scope() -> None:
    f = _fact()
    page = _page([f], cursor="next-cursor")
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=page))

    adapter = _adapter()
    result_json = adapter.dispatch("subscribe_scope", {"scope": "company"})
    result = json.loads(result_json)
    assert result["has_more"] is True
    assert result["cursor"] == "next-cursor"
    assert len(result["facts"]) == 1


# ---------------------------------------------------------------------------
# dispatch — unknown tool
# ---------------------------------------------------------------------------

def test_dispatch_unknown_tool() -> None:
    adapter = _adapter()
    result_json = adapter.dispatch("not_a_tool", {})
    result = json.loads(result_json)
    assert "error" in result
    assert "not_a_tool" in result["error"]


# ---------------------------------------------------------------------------
# dispatch — stigmem error
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_stigmem_error_returns_error_json() -> None:
    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(422, json={"detail": "bad"}))

    adapter = _adapter()
    result_json = adapter.dispatch("assert_fact", {
        "entity": "x",
        "relation": "y",
        "value": {"type": "string", "v": "z"},
        "source": SOURCE,
    })
    result = json.loads(result_json)
    assert "error" in result
