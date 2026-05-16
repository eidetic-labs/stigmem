"""Unit tests for OpenClawStigmemAdapter (respx-mocked; no live node required).

Run with: uv run pytest stigmem/adapters/openclaw/tests/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

# conftest.py adds the adapter directory to sys.path
from adapter import BootContext, OpenClawStigmemAdapter

BASE = "http://test-stigmem"
SOURCE = "agent:openclaw"

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _fact(
    id: str = "fact-001",
    entity: str = "user:alice",
    relation: str = "preference:theme",
    value: dict | None = None,
    source: str = SOURCE,
    confidence: float = 1.0,
    scope: str = "company",
) -> dict:
    return {
        "id": id,
        "entity": entity,
        "relation": relation,
        "value": value or {"type": "string", "v": "dark"},
        "source": source,
        "timestamp": "2026-05-02T00:00:00Z",
        "confidence": confidence,
        "scope": scope,
        "contradicted": False,
    }


def _page(facts: list[dict], cursor: str | None = None) -> dict:
    return {"facts": facts, "total": len(facts), "cursor": cursor}


def _adapter() -> OpenClawStigmemAdapter:
    return OpenClawStigmemAdapter(url=BASE, api_key="sk-test", source_entity=SOURCE)


# ---------------------------------------------------------------------------
# Boot handshake — happy path
# ---------------------------------------------------------------------------


@respx.mock
def test_boot_collects_user_prefs() -> None:
    pref_fact = _fact(relation="preference:theme")
    non_pref = _fact(id="fact-002", relation="memory:role", value={"type": "string", "v": "CEO"})

    # boot makes 3 queries: user entity, intent:handoff_to, intent:escalation
    call_count = {"n": 0}
    responses = [
        httpx.Response(200, json=_page([pref_fact, non_pref])),  # user entity
        httpx.Response(200, json=_page([])),  # intent:handoff_to
        httpx.Response(200, json=_page([])),  # intent:escalation
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[min(call_count["n"], len(responses) - 1)]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert isinstance(ctx, BootContext)
    # Only preference:* facts collected from user entity; non-pref memory:role is excluded
    assert len(ctx.facts) == 1
    assert ctx.facts[0].relation == "preference:theme"
    assert ctx.summary != ""
    assert "user:alice" in ctx.summary


@respx.mock
def test_boot_collects_project_constraints() -> None:
    constraint = _fact(
        id="fact-c1",
        entity="project:acme",
        relation="roadmap:constraint",
        value={"type": "text", "v": "Must ship before 2026-06-01"},
    )
    # boot with one project makes 4 queries:
    #   user entity, project:acme constraint, intent:handoff_to, intent:escalation
    call_count = {"n": 0}
    responses = [
        httpx.Response(200, json=_page([])),  # user entity (no prefs)
        httpx.Response(200, json=_page([constraint])),  # project:acme constraint
        httpx.Response(200, json=_page([])),  # intent:handoff_to
        httpx.Response(200, json=_page([])),  # intent:escalation
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[min(call_count["n"], len(responses) - 1)]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice", project_entities=["project:acme"])

    assert len(ctx.facts) == 1
    assert ctx.facts[0].relation == "roadmap:constraint"


@respx.mock
def test_boot_collects_handoffs() -> None:
    handoff_fact = _fact(
        id="hf-1",
        entity="handoff:abc",
        relation="intent:handoff_to",
        value={"type": "ref", "v": SOURCE},
    )
    ctx_ref_fact = _fact(
        id="cr-1",
        entity="handoff:abc",
        relation="intent:context_ref",
        value={"type": "ref", "v": "fact-001"},
    )

    call_count = {"n": 0}
    responses = [
        httpx.Response(200, json=_page([])),  # user prefs
        httpx.Response(200, json=_page([handoff_fact])),  # intent:handoff_to
        httpx.Response(200, json=_page([ctx_ref_fact])),  # intent:context_ref for handoff:abc
        httpx.Response(200, json=_page([])),  # intent:handoff_summary
        httpx.Response(200, json=_page([])),  # intent:continuation
        httpx.Response(200, json=_page([])),  # intent:escalation
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[call_count["n"]]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert any(f.relation == "intent:context_ref" for f in ctx.facts)


@respx.mock
def test_boot_pagination() -> None:
    """_query_all must follow cursor until exhausted."""
    pref1 = _fact(id="pf-1", relation="preference:theme")
    pref2 = _fact(id="pf-2", relation="preference:lang", value={"type": "string", "v": "en"})

    call_count = {"n": 0}
    # First call: returns page1 with a cursor; second call: page2 with no cursor
    responses = [
        httpx.Response(200, json=_page([pref1], cursor="page-cursor-1")),
        httpx.Response(200, json=_page([pref2])),  # cursor=None — terminates
        # remaining namespace queries return empty
        httpx.Response(200, json=_page([])),  # intent:handoff_to
        httpx.Response(200, json=_page([])),  # intent:escalation
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[call_count["n"] % len(responses)]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    pref_facts = [f for f in ctx.facts if f.relation.startswith("preference:")]
    assert len(pref_facts) == 2


@respx.mock
def test_boot_node_unavailable_returns_empty() -> None:
    """Node connection failure must return empty BootContext, not raise."""
    respx.get(f"{BASE}/v1/facts").mock(side_effect=httpx.ConnectError("refused"))

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert ctx == BootContext()
    assert not ctx


@respx.mock
def test_boot_http_error_returns_empty() -> None:
    respx.get(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(503, json={"detail": "service unavailable"})
    )

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert not ctx
    assert ctx.summary == ""


# ---------------------------------------------------------------------------
# emit_handoff
# ---------------------------------------------------------------------------


@respx.mock
def test_emit_handoff_validates_refs_and_asserts() -> None:
    good_fact = _fact(id="fact-good")
    # GET fact-good → 200
    respx.get(f"{BASE}/v1/facts/fact-good").mock(return_value=httpx.Response(200, json=good_fact))
    # GET fact-bad → 404 (should be skipped)
    respx.get(f"{BASE}/v1/facts/fact-bad").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    # POST /v1/facts → 201 for each assert
    assert_route = respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=good_fact)
    )

    adapter = _adapter()
    adapter.emit_handoff(
        from_entity="agent:openclaw",
        to_entity="agent:assistant",
        summary="Handoff summary",
        fact_refs=["fact-good", "fact-bad"],
        continuation="Pick up from roadmap discussion.",
    )

    # intent:handoff_to, intent:handoff_summary, intent:context_ref (good only), intent:continuation
    assert assert_route.call_count == 4


@respx.mock
def test_emit_handoff_all_refs_invalid_still_asserts_core() -> None:
    respx.get(f"{BASE}/v1/facts/fact-x").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    assert_route = respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=_fact())
    )

    adapter = _adapter()
    adapter.emit_handoff(
        from_entity="agent:openclaw",
        to_entity="agent:assistant",
        summary="Summary",
        fact_refs=["fact-x"],
    )

    # intent:handoff_to + intent:handoff_summary — no context_ref because ref was invalid
    assert assert_route.call_count == 2


@respx.mock
def test_emit_handoff_partial_assert_failure_does_not_raise() -> None:
    """If one POST fails, the others still proceed."""
    respx.get(f"{BASE}/v1/facts/fact-ok").mock(return_value=httpx.Response(200, json=_fact()))

    call_count = {"n": 0}
    assert_responses = [
        httpx.Response(201, json=_fact()),  # intent:handoff_to succeeds
        httpx.Response(500, json={"detail": "oops"}),  # intent:handoff_summary fails
        httpx.Response(201, json=_fact()),  # intent:context_ref succeeds
    ]

    def assert_side_effect(request: httpx.Request) -> httpx.Response:
        resp = assert_responses[min(call_count["n"], len(assert_responses) - 1)]
        call_count["n"] += 1
        return resp

    respx.post(f"{BASE}/v1/facts").mock(side_effect=assert_side_effect)

    adapter = _adapter()
    # Must not raise even though one assert returns 500
    adapter.emit_handoff(
        from_entity="agent:openclaw",
        to_entity="agent:assistant",
        summary="Summary",
        fact_refs=["fact-ok"],
    )


# ---------------------------------------------------------------------------
# emit_decision
# ---------------------------------------------------------------------------


@respx.mock
def test_emit_decision_asserts_when_no_existing() -> None:
    # query returns empty — no existing decision
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([])))
    assert_route = respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=_fact(relation="roadmap:decision"))
    )

    adapter = _adapter()
    adapter.emit_decision(entity="decision:db-choice", summary="Chose PostgreSQL.")

    assert assert_route.call_count == 1


@respx.mock
def test_emit_decision_skips_when_existing() -> None:
    existing = _fact(id="d-001", relation="roadmap:decision")
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([existing])))
    assert_route = respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=_fact())
    )

    adapter = _adapter()
    adapter.emit_decision(entity="decision:db-choice", summary="Chose PostgreSQL.")

    assert assert_route.call_count == 0


# ---------------------------------------------------------------------------
# emit_escalation
# ---------------------------------------------------------------------------


@respx.mock
def test_emit_escalation_includes_valid_until() -> None:
    captured: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        import json

        captured.append(json.loads(request.content))
        return httpx.Response(201, json=_fact())

    respx.post(f"{BASE}/v1/facts").mock(side_effect=capture)

    adapter = _adapter()
    adapter.emit_escalation(
        to_entity="agent:cto",
        goal="Approve infra spend",
        priority="high",
    )

    # Should be 3 asserts: intent:escalation, intent:escalate_to, intent:goal
    assert len(captured) == 3

    escalation_body = captured[0]
    assert escalation_body["relation"] == "intent:escalation"
    assert escalation_body["value"] == {"type": "string", "v": "high"}
    assert "valid_until" in escalation_body

    escalate_to_body = captured[1]
    assert escalate_to_body["relation"] == "intent:escalate_to"
    assert escalate_to_body["value"] == {"type": "ref", "v": "agent:cto"}

    goal_body = captured[2]
    assert goal_body["relation"] == "intent:goal"


@respx.mock
def test_emit_escalation_default_priority_is_medium() -> None:
    captured: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        import json

        captured.append(json.loads(request.content))
        return httpx.Response(201, json=_fact())

    respx.post(f"{BASE}/v1/facts").mock(side_effect=capture)

    adapter = _adapter()
    adapter.emit_escalation(to_entity="agent:cto", goal="Some goal")

    assert captured[0]["value"]["v"] == "medium"


# ---------------------------------------------------------------------------
# Summary formatting
# ---------------------------------------------------------------------------


@respx.mock
def test_boot_summary_groups_by_namespace() -> None:
    facts = [
        _fact(id="f1", relation="preference:theme", value={"type": "string", "v": "dark"}),
        _fact(id="f2", relation="preference:lang", value={"type": "string", "v": "en"}),
    ]
    # query returns both prefs; subsequent namespace queries return empty
    call_count = {"n": 0}
    responses = [
        httpx.Response(200, json=_page(facts)),
        httpx.Response(200, json=_page([])),
        httpx.Response(200, json=_page([])),
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[min(call_count["n"], len(responses) - 1)]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert "### preference" in ctx.summary
    assert "preference:theme" in ctx.summary
    assert "preference:lang" in ctx.summary


@respx.mock
def test_boot_summary_shows_confidence_for_low_confidence_facts() -> None:
    low_conf_fact = _fact(id="f1", relation="preference:theme", confidence=0.75)
    call_count = {"n": 0}
    responses = [
        httpx.Response(200, json=_page([low_conf_fact])),
        httpx.Response(200, json=_page([])),
        httpx.Response(200, json=_page([])),
    ]

    def side_effect(request: httpx.Request) -> httpx.Response:
        resp = responses[min(call_count["n"], len(responses) - 1)]
        call_count["n"] += 1
        return resp

    respx.get(f"{BASE}/v1/facts").mock(side_effect=side_effect)

    adapter = _adapter()
    ctx = adapter.boot(user_entity="user:alice")

    assert "0.75" in ctx.summary


# ---------------------------------------------------------------------------
# from_env constructor
# ---------------------------------------------------------------------------


def test_from_env() -> None:
    env = {
        "STIGMEM_URL": "http://my-node",
        "STIGMEM_API_KEY": "sk-abc",
        "STIGMEM_SOURCE_ENTITY": "agent:my-openclaw",
    }
    with patch.dict(os.environ, env):
        adapter = OpenClawStigmemAdapter.from_env()
    assert adapter._source == "agent:my-openclaw"


def test_from_env_defaults() -> None:
    env = {"STIGMEM_URL": "http://my-node", "STIGMEM_API_KEY": "sk-abc"}
    with patch.dict(os.environ, env, clear=False):
        # Remove optional vars if present
        for k in ("STIGMEM_SOURCE_ENTITY",):
            os.environ.pop(k, None)
        adapter = OpenClawStigmemAdapter.from_env()
    assert adapter._source == "agent:openclaw"


def test_from_env_requires_api_key() -> None:
    env = {"STIGMEM_URL": "http://my-node"}
    with (
        patch.dict(os.environ, env, clear=True),
        pytest.raises(RuntimeError, match="STIGMEM_API_KEY is required"),
    ):
        OpenClawStigmemAdapter.from_env()


# ---------------------------------------------------------------------------
# Conformance vector smoke tests (mocked, no live node)
# ---------------------------------------------------------------------------

_CONFORMANCE_DIR = Path(__file__).resolve()
for _ in range(5):
    _CONFORMANCE_DIR = _CONFORMANCE_DIR.parent
_CONFORMANCE_DIR = _CONFORMANCE_DIR / "sdks" / "stigmem-py" / "tests"
sys.path.insert(0, str(_CONFORMANCE_DIR))

try:
    from conformance_vectors import ASSERT_VECTORS, NODE_INFO_VECTOR

    _CONFORMANCE_AVAILABLE = True
except ImportError:
    _CONFORMANCE_AVAILABLE = False
    ASSERT_VECTORS = []  # type: ignore[assignment]
    NODE_INFO_VECTOR = {}  # type: ignore[assignment]

SAMPLE_NODE_INFO = {
    "version": "0.5",
    "node_id": "stigmem://node.acme",
    "node_url": BASE,
    "auth": "required",
    "federation": "disabled",
    "namespaces": [],
}


@pytest.mark.skipif(not _CONFORMANCE_AVAILABLE, reason="conformance_vectors not importable")
@pytest.mark.parametrize(
    "vec",
    ASSERT_VECTORS,
    ids=[v["id"] for v in ASSERT_VECTORS],
)
def test_conformance_assert_vector(vec: dict) -> None:
    """Smoke-test each ASSERT_VECTOR against a mocked node to verify wire format."""
    import pydantic
    from stigmem import StigmemClient
    from stigmem.models import FactValue

    req = vec["request"]
    mock_fact = {
        "id": f"fact-{vec['id']}",
        "entity": req["entity"],
        "relation": req["relation"],
        "value": req["value"],
        "source": req["source"],
        "timestamp": "2026-05-02T00:00:00Z",
        "confidence": req.get("confidence", 1.0),
        "scope": req.get("scope", "company"),
        "contradicted": False,
    }

    with respx.mock:
        respx.post(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(vec["expected_status"], json=mock_fact)
        )
        client = StigmemClient(url=BASE, api_key="sk-test")
        val_obj = pydantic.TypeAdapter(FactValue).validate_python(req["value"])
        fact = client.assert_fact(
            entity=req["entity"],
            relation=req["relation"],
            value=val_obj,
            source=req["source"],
            confidence=req.get("confidence", 1.0),
            scope=req.get("scope", "company"),
        )

    if "expected_value_type" in vec:
        assert fact.value.type == vec["expected_value_type"]  # type: ignore[union-attr]
    if "expected_confidence" in vec:
        assert fact.confidence == vec["expected_confidence"]


@pytest.mark.skipif(not _CONFORMANCE_AVAILABLE, reason="conformance_vectors not importable")
@respx.mock
def test_conformance_node_info_vector() -> None:
    from stigmem import StigmemClient

    respx.get(f"{BASE}/.well-known/stigmem").mock(
        return_value=httpx.Response(200, json=SAMPLE_NODE_INFO)
    )
    client = StigmemClient(url=BASE, api_key="sk-test")
    info = client.node_info()

    for f in NODE_INFO_VECTOR.get("expected_fields", []):
        assert hasattr(info, f), f"NodeInfo missing field: {f}"
