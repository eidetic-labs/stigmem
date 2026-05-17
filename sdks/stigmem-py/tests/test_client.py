"""Unit tests for StigmemClient and AsyncStigmemClient (no live node required)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from stigmem import (
    AsyncStigmemClient,
    StigmemAuthError,
    StigmemClient,
    StigmemNotFoundError,
    StigmemVerificationError,
    compute_fact_cid,
    string_value,
    text_value,
    verify_fact_chain_proof,
    verify_fact_cid,
)
from stigmem.models import (
    ConflictPage,
    ConflictResolution,
    Fact,
    FactPage,
    NodeInfo,
    RecallResponse,
)

BASE = "http://test-node"
KEY = "sk-test"

SAMPLE_FACT = {
    "id": "fact-001",
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:test",
    "timestamp": "2026-05-02T00:00:00Z",
    "hlc": "1746230400000.001",
    "confidence": 1.0,
    "scope": "company",
    "contradicted": False,
}

SAMPLE_NODE_INFO = {
    "version": "0.5",
    "node_id": "stigmem://node.acme",
    "node_url": "http://test-node",
    "auth": "required",
    "federation": "disabled",
    "namespaces": ["memory:", "intent:"],
}

SAMPLE_RECALL_RESPONSE = {
    "recall_id": "recall-001",
    "query_hash": "abc123",
    "facts": [
        {
            "fact": SAMPLE_FACT,
            "score": 0.92,
            "score_breakdown": {
                "lexical": 0.4,
                "semantic": 0.3,
                "graph": 0.1,
                "source_trust": 0.1,
                "recency": 0.02,
                "weighted_total": 0.92,
            },
            "hop_distance": 0,
            "token_estimate": 42,
        }
    ],
    "total_scored": 1,
    "token_budget": 1000,
    "tokens_used": 42,
    "truncated": False,
}


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------

@respx.mock
def test_node_info() -> None:
    respx.get(f"{BASE}/.well-known/stigmem").mock(
        return_value=httpx.Response(200, json=SAMPLE_NODE_INFO)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    info = client.node_info()
    assert isinstance(info, NodeInfo)
    assert info.version == "0.5"
    assert info.node_id == "stigmem://node.acme"


@respx.mock
def test_assert_fact_string() -> None:
    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=SAMPLE_FACT)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    fact = client.assert_fact(
        entity="user:alice",
        relation="memory:role",
        value=string_value("CEO"),
        source="agent:test",
    )
    assert isinstance(fact, Fact)
    assert fact.id == "fact-001"
    assert fact.value.type == "string"  # type: ignore[union-attr]


@respx.mock
def test_assert_fact_text() -> None:
    sample = {**SAMPLE_FACT, "id": "fact-002", "value": {"type": "text", "v": "long text"}}
    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=sample)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    fact = client.assert_fact(
        entity="project:acme",
        relation="roadmap:summary",
        value=text_value("long text"),
        source="agent:cto",
    )
    assert fact.value.type == "text"  # type: ignore[union-attr]


@respx.mock
def test_session_header_and_provenance_are_sent() -> None:
    def side_effect(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.headers["Stigmem-Session"] == "session-123"
        assert payload["write_mode"] == "summarize_with_provenance"
        assert payload["derived_from"] == [{"fact_id": "fact-source"}]
        return httpx.Response(
            201,
            json={**SAMPLE_FACT, "derived_from": [{"fact_id": "fact-source"}]},
        )

    respx.post(f"{BASE}/v1/facts").mock(side_effect=side_effect)
    client = StigmemClient(url=BASE, api_key=KEY)
    client.assert_fact(
        entity="summary:1",
        relation="roadmap:summary",
        value=text_value("summary"),
        source="agent:test",
        write_mode="summarize_with_provenance",
        derived_from=[{"fact_id": "fact-source"}],
        session_id="session-123",
    )


@respx.mock
def test_retract() -> None:
    retracted = {**SAMPLE_FACT, "id": "fact-003", "confidence": 0.0}
    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=retracted)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    fact = client.retract("user:alice", "memory:role", "company", "agent:test")
    assert fact.confidence == 0.0


@respx.mock
def test_get_fact() -> None:
    respx.get(f"{BASE}/v1/facts/fact-001").mock(
        return_value=httpx.Response(200, json=SAMPLE_FACT)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    fact = client.get("fact-001")
    assert fact.id == "fact-001"


@respx.mock
def test_get_fact_not_found() -> None:
    respx.get(f"{BASE}/v1/facts/missing").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    with pytest.raises(StigmemNotFoundError):
        client.get("missing")


@respx.mock
def test_query() -> None:
    respx.get(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(200, json={"facts": [SAMPLE_FACT], "total": 1, "cursor": None})
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    page = client.query(entity="user:alice")
    assert isinstance(page, FactPage)
    assert len(page.facts) == 1
    assert page.facts[0].entity == "user:alice"


@respx.mock
def test_list_conflicts() -> None:
    respx.get(f"{BASE}/v1/conflicts").mock(
        return_value=httpx.Response(200, json={"conflicts": [], "cursor": None, "has_more": False})
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    page = client.list_conflicts()
    assert isinstance(page, ConflictPage)
    assert page.conflicts == []


@respx.mock
def test_resolve_conflict() -> None:
    respx.post(f"{BASE}/v1/conflicts/c-001/resolve").mock(
        return_value=httpx.Response(
            200,
            json={
                "resolution_fact_id": "fact-999",
                "conflict_status": "resolved",
            },
        )
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    result = client.resolve_conflict(
        "c-001",
        winning_fact_id="fact-001",
        resolution_note="prefer fact-001",
    )
    assert isinstance(result, ConflictResolution)
    assert result.conflict_status == "resolved"


@respx.mock
def test_federation_status() -> None:
    respx.get(f"{BASE}/v1/federation/peers").mock(
        return_value=httpx.Response(200, json={"peers": []})
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    peers = client.federation_status()
    assert peers == []


@respx.mock
def test_recall_legacy_format_param() -> None:
    respx.post(f"{BASE}/v1/recall", params={"legacy_format": "true"}).mock(
        return_value=httpx.Response(200, json=SAMPLE_RECALL_RESPONSE)
    )
    client = StigmemClient(url=BASE, api_key=KEY)
    result = client.recall("what is Alice's role?", token_budget=1000, legacy_format=True)
    assert isinstance(result, RecallResponse)
    assert result.recall_id == "recall-001"


@respx.mock
def test_recall_sends_session_header() -> None:
    def side_effect(request: httpx.Request) -> httpx.Response:
        assert request.headers["Stigmem-Session"] == "session-123"
        return httpx.Response(200, json=SAMPLE_RECALL_RESPONSE)

    respx.post(f"{BASE}/v1/recall").mock(side_effect=side_effect)
    client = StigmemClient(url=BASE, api_key=KEY)
    result = client.recall("what is Alice's role?", session_id="session-123")
    assert result.recall_id == "recall-001"


@respx.mock
def test_recall_verify_full_sends_header_and_parses_chain_proof() -> None:
    response_body = {
        **SAMPLE_RECALL_RESPONSE,
        "chain_proof": {
            "tenant_id": "default",
            "checked_entries": 2,
            "head_hash": "sha256:abc",
            "checkpoint": {
                "id": "chaincp_1",
                "tenant_id": "default",
                "covered_chain_seq": 2,
                "chain_hash": "sha256:abc",
                "status": "submitted",
                "attempt_count": 1,
                "created_at": "2026-01-01T00:00:00+00:00",
                "submitted_at": "2026-01-01T00:00:01+00:00",
                "tl_backend": "local",
                "tl_log_id": "local-log",
                "tl_leaf_hash": "a" * 64,
                "tl_log_index": 0,
                "tl_integrated_time": 1_767_225_601,
                "tl_inclusion_proof": {"chain_hash": "sha256:abc"},
                "tl_raw": {"index": 0},
            },
        },
    }

    def side_effect(request: httpx.Request) -> httpx.Response:
        assert request.headers["Stigmem-Verify"] == "full"
        return httpx.Response(200, json=response_body)

    respx.post(f"{BASE}/v1/recall").mock(side_effect=side_effect)
    client = StigmemClient(url=BASE, api_key=KEY)
    result = client.recall("what is Alice's role?", verify_full=True)
    assert result.chain_proof is not None
    assert result.chain_proof.checked_entries == 2
    assert result.chain_proof.checkpoint is not None
    assert result.chain_proof.checkpoint.status == "submitted"


def test_verify_fact_cid_accepts_matching_cid() -> None:
    fact = Fact.model_validate(SAMPLE_FACT)
    cid = compute_fact_cid(fact)
    verified = Fact.model_validate({**SAMPLE_FACT, "cid": cid})

    assert verify_fact_cid(verified) == cid


def test_verify_fact_cid_rejects_mismatch() -> None:
    fact = Fact.model_validate({**SAMPLE_FACT, "cid": "sha256:" + ("0" * 64)})

    with pytest.raises(StigmemVerificationError, match="CID mismatch"):
        verify_fact_cid(fact)


def test_verify_fact_chain_proof_rejects_mismatched_checkpoint_head() -> None:
    response = RecallResponse.model_validate(
        {
            **SAMPLE_RECALL_RESPONSE,
            "chain_proof": {
                "tenant_id": "default",
                "checked_entries": 2,
                "head_hash": "sha256:head-a",
                "checkpoint": {
                    "id": "chaincp_1",
                    "tenant_id": "default",
                    "covered_chain_seq": 2,
                    "chain_hash": "sha256:head-b",
                    "status": "submitted",
                    "attempt_count": 1,
                    "created_at": "2026-05-02T00:00:00Z",
                    "tl_backend": "local",
                    "tl_leaf_hash": "abc",
                    "tl_log_index": 0,
                    "tl_inclusion_proof": {},
                    "tl_raw": {},
                },
            },
        }
    )

    with pytest.raises(StigmemVerificationError, match="chain_hash"):
        verify_fact_chain_proof(response.chain_proof, require_checkpoint=True)


@respx.mock
def test_auth_error() -> None:
    respx.get(f"{BASE}/.well-known/stigmem").mock(
        return_value=httpx.Response(401, json={"detail": "unauthorized"})
    )
    client = StigmemClient(url=BASE, api_key="bad-key")
    with pytest.raises(StigmemAuthError) as exc_info:
        client.node_info()
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_async_assert_fact() -> None:
    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=SAMPLE_FACT)
    )
    async with AsyncStigmemClient(url=BASE, api_key=KEY) as client:
        fact = await client.assert_fact(
            entity="user:alice",
            relation="memory:role",
            value=string_value("CEO"),
            source="agent:test",
        )
    assert fact.entity == "user:alice"


@pytest.mark.asyncio
@respx.mock
async def test_async_query() -> None:
    respx.get(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(200, json={"facts": [SAMPLE_FACT], "total": 1, "cursor": None})
    )
    async with AsyncStigmemClient(url=BASE, api_key=KEY) as client:
        page = await client.query(entity="user:alice")
    assert len(page.facts) == 1


@pytest.mark.asyncio
@respx.mock
async def test_async_federation_status() -> None:
    respx.get(f"{BASE}/v1/federation/peers").mock(
        return_value=httpx.Response(200, json={"peers": []})
    )
    async with AsyncStigmemClient(url=BASE, api_key=KEY) as client:
        peers = await client.federation_status()
    assert peers == []
