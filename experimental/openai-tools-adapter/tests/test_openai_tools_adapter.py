"""Unit tests for StigmemOpenAIToolsAdapter (respx-mocked; no live node or API key required).

Run with::

    cd stigmem
    uv run pytest adapters/openai-tools/tests/ -v
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

# conftest.py adds the adapter directory to sys.path
from adapter import STIGMEM_TOOLS, StigmemOpenAIToolsAdapter

BASE = "http://test-stigmem"
SOURCE = "agent:openai-tools"


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


def _adapter() -> StigmemOpenAIToolsAdapter:
    return StigmemOpenAIToolsAdapter(url=BASE, api_key="sk-test", source_entity=SOURCE)


def _tool_call(
    name: str,
    args: dict,
    call_id: str = "call-001",
) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


# ---------------------------------------------------------------------------
# STIGMEM_TOOLS schema
# ---------------------------------------------------------------------------

def test_tools_contains_five_entries() -> None:
    assert len(STIGMEM_TOOLS) == 5
    names = [t["function"]["name"] for t in STIGMEM_TOOLS]
    assert names == [
        "assert_fact",
        "query_facts",
        "resolve_contradiction",
        "subscribe_scope",
        "lint_scope",
    ]


def test_tools_use_lowercase_types() -> None:
    for tool in STIGMEM_TOOLS:
        assert tool["function"]["parameters"]["type"] == "object", (
            f"{tool['function']['name']}: top-level type must be 'object'"
        )
    af = next(t for t in STIGMEM_TOOLS if t["function"]["name"] == "assert_fact")
    assert af["function"]["parameters"]["properties"]["entity"]["type"] == "string"


def test_tools_type_field() -> None:
    for tool in STIGMEM_TOOLS:
        assert tool["type"] == "function"


def test_query_facts_has_scope_enum() -> None:
    qf = next(t for t in STIGMEM_TOOLS if t["function"]["name"] == "query_facts")
    scope_prop = qf["function"]["parameters"]["properties"]["scope"]
    assert "enum" in scope_prop
    assert "company" in scope_prop["enum"]


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------

def test_from_env_reads_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://oss-node")
    monkeypatch.delenv("STIGMEM_API_KEY", raising=False)
    monkeypatch.delenv("STIGMEM_SOURCE_ENTITY", raising=False)
    adapter = StigmemOpenAIToolsAdapter.from_env()
    assert adapter._client._url == "http://oss-node"


def test_from_env_default_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_URL", "http://oss-node")
    monkeypatch.delenv("STIGMEM_SOURCE_ENTITY", raising=False)
    adapter = StigmemOpenAIToolsAdapter.from_env()
    assert adapter._source == "agent:openai-tools"


# ---------------------------------------------------------------------------
# dispatch — assert_fact via dict tool_call
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_assert_fact_dict_toolcall() -> None:
    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_fact()))

    adapter = _adapter()
    tc = _tool_call("assert_fact", {
        "entity": "user:alice",
        "relation": "memory:role",
        "value": {"type": "string", "v": "engineer"},
        "source": SOURCE,
    })
    result = adapter.dispatch(tc)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-001"
    payload = json.loads(result["content"])
    assert payload["entity"] == "user:alice"


@respx.mock
def test_dispatch_assert_fact_uses_default_source() -> None:
    route = respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_fact()))

    adapter = _adapter()
    tc = _tool_call("assert_fact", {
        "entity": "user:alice",
        "relation": "memory:role",
        "value": {"type": "string", "v": "engineer"},
        # no source
    })
    adapter.dispatch(tc)
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
    result = adapter.dispatch(_tool_call("query_facts", {"entity": "user:alice"}))
    payload = json.loads(result["content"])
    assert payload["total"] == 1
    assert payload["facts"][0]["entity"] == "user:alice"


# ---------------------------------------------------------------------------
# dispatch — subscribe_scope
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_subscribe_scope() -> None:
    page = _page([_fact()], cursor="c1")
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=page))

    adapter = _adapter()
    result = adapter.dispatch(_tool_call("subscribe_scope", {"scope": "company"}))
    payload = json.loads(result["content"])
    assert payload["has_more"] is True
    assert payload["cursor"] == "c1"


# ---------------------------------------------------------------------------
# dispatch — unknown tool
# ---------------------------------------------------------------------------

def test_dispatch_unknown_tool() -> None:
    adapter = _adapter()
    result = adapter.dispatch(_tool_call("bad_tool", {}))
    payload = json.loads(result["content"])
    assert "error" in payload
    assert "bad_tool" in payload["error"]


# ---------------------------------------------------------------------------
# dispatch — stigmem HTTP error
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_stigmem_error_returns_error_json() -> None:
    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(422, json={"detail": "bad"}))

    adapter = _adapter()
    result = adapter.dispatch(_tool_call("assert_fact", {
        "entity": "x",
        "relation": "y",
        "value": {"type": "string", "v": "z"},
        "source": SOURCE,
    }))
    payload = json.loads(result["content"])
    assert "error" in payload


# ---------------------------------------------------------------------------
# dispatch — SDK-object style tool_call (mock object)
# ---------------------------------------------------------------------------

class _MockFunction:
    def __init__(self, name: str, args: dict) -> None:
        self.name = name
        self.arguments = json.dumps(args)

class _MockToolCall:
    def __init__(self, id: str, name: str, args: dict) -> None:
        self.id = id
        self.function = _MockFunction(name, args)


@respx.mock
def test_dispatch_sdk_object_tool_call() -> None:
    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_fact()))

    adapter = _adapter()
    tc = _MockToolCall("call-sdk", "assert_fact", {
        "entity": "user:bob",
        "relation": "memory:role",
        "value": {"type": "string", "v": "manager"},
        "source": SOURCE,
    })
    result = adapter.dispatch(tc)
    assert result["tool_call_id"] == "call-sdk"
    payload = json.loads(result["content"])
    assert payload["entity"] == "user:alice"  # mock returns _fact() always
