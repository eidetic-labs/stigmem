"""Conformance: recall endpoint behavioral contract (spec §20).

Tests focus on the observable HTTP contract: response shape, token budget
enforcement, scope isolation, and recall metadata — not the internal
scoring algorithm.
"""

from __future__ import annotations

from typing import Any

from .conftest import ConformanceClient

_E = "stigmem://conformance/recall/entity"


def _fact(
    entity: str = _E,
    relation: str = "memory:knows",
    v: str = "test",
    scope: str = "local",
) -> dict[str, Any]:
    return {
        "entity": entity,
        "relation": relation,
        "value": {"type": "string", "v": v},
        "source": entity,
        "confidence": 0.9,
        "scope": scope,
    }


def _recall(
    query: str = "test",
    scope: str = "local",
    budget: int = 4000,
    **kw: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "query": query,
        "scope": scope,
        "token_budget": budget,
        "depth": 1,
        "include_neighbors": False,
    }
    body.update(kw)
    return body


class TestRecallBasics:
    def test_endpoint_exists(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/recall", json=_recall())
        assert r.status_code == 200

    def test_response_has_required_fields(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/recall", json=_recall())
        assert r.status_code == 200
        body = r.json()
        for key in ("recall_id", "query_hash", "facts", "total_scored", "tokens_used", "truncated"):
            assert key in body, f"Missing key: {key}"

    def test_recall_id_is_uuid(self, conformance_client: ConformanceClient) -> None:
        body = conformance_client.client.post("/v1/recall", json=_recall()).json()
        assert len(body["recall_id"]) == 36  # UUID4

    def test_query_hash_is_sha256_hex(self, conformance_client: ConformanceClient) -> None:
        body = conformance_client.client.post("/v1/recall", json=_recall()).json()
        assert len(body["query_hash"]) == 64

    def test_empty_db_returns_empty_facts(self, conformance_client: ConformanceClient) -> None:
        body = conformance_client.client.post(
            "/v1/recall", json=_recall(query="nothing-here-xyz")
        ).json()
        assert body["facts"] == []
        assert body["total_scored"] == 0
        assert body["truncated"] is False


class TestRecallResults:
    def test_asserted_fact_appears_in_recall(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(v="alice knows bob"))
        body = c.post("/v1/recall", json=_recall(query="alice")).json()
        # Each item is a ScoredFact: {"fact": FactRecord, "score": float, ...}
        ids = [f["fact"]["id"] for f in body["facts"]]
        assert len(ids) > 0

    def test_score_breakdown_present_per_fact(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(v="score test"))
        body = c.post("/v1/recall", json=_recall(query="score")).json()
        if body["facts"]:
            fact = body["facts"][0]
            assert "score" in fact

    def test_scope_isolation(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(scope="company", v="scoped company value"))
        # Query local scope should NOT return company-scoped facts
        body = c.post("/v1/recall", json=_recall(query="scoped company", scope="local")).json()
        # Each item is a ScoredFact: {"fact": FactRecord, ...}
        for f in body["facts"]:
            assert f["fact"].get("scope") != "company"

    def test_token_budget_zero_returns_truncated(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(v="budget test content"))
        body = c.post("/v1/recall", json=_recall(query="budget", budget=1)).json()
        # With a tiny budget the response may be truncated or return 0 facts
        assert body["tokens_used"] <= 1 or body["facts"] == [] or body["truncated"] is True

    def test_invalid_scope_rejected(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/recall", json=_recall(scope="invalid"))
        assert r.status_code in (400, 422)

    def test_query_required(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post(
            "/v1/recall", json={"scope": "local", "token_budget": 1000}
        )
        assert r.status_code in (400, 422)
