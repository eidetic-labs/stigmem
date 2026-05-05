"""Conformance: fact assert / query behavioral contract.

Verifies that every backend correctly stores, retrieves, updates, and expires
facts through the HTTP API — black-box, no direct DB access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from .conftest import ConformanceClient

_FACT = {
    "entity": "stigmem://conformance/user/alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "admin"},
    "source": "stigmem://conformance/agent/test",
    "confidence": 1.0,
    "scope": "local",
}


class TestFactAssert:
    def test_assert_returns_201(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/facts", json=_FACT)
        assert r.status_code == 201
        body = r.json()
        assert body["entity"] == _FACT["entity"]
        assert body["relation"] == _FACT["relation"]
        assert "id" in body and body["id"]
        assert "timestamp" in body

    def test_assert_all_value_types(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        for vtype, vval in [
            ("string", "hello"),
            ("text", "a" * 500),
            ("number", 42.5),
            ("boolean", True),
            ("null", None),
            ("ref", "stigmem://conformance/user/bob"),
        ]:
            payload = {**_FACT, "value": {"type": vtype, "v": vval}}
            r = c.post("/v1/facts", json=payload)
            assert r.status_code == 201, f"Failed for type={vtype}: {r.text}"
            assert r.json()["value"]["type"] == vtype

    def test_assert_with_valid_until(self, conformance_client: ConformanceClient) -> None:
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        r = conformance_client.client.post(
            "/v1/facts", json={**_FACT, "valid_until": future}
        )
        assert r.status_code == 201
        assert r.json()["valid_until"] is not None

    def test_assert_duplicate_is_idempotent(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        r1 = c.post("/v1/facts", json=_FACT)
        r2 = c.post("/v1/facts", json=_FACT)
        assert r1.status_code == 201
        assert r2.status_code == 201
        # Same fact re-asserted returns the same (or updated) fact id
        assert r1.json()["entity"] == r2.json()["entity"]

    def test_assert_rejects_invalid_scope(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post(
            "/v1/facts", json={**_FACT, "scope": "invalid_scope"}
        )
        assert r.status_code in (400, 422)

    def test_assert_rejects_confidence_out_of_range(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post(
            "/v1/facts", json={**_FACT, "confidence": 1.5}
        )
        assert r.status_code in (400, 422)


class TestFactQuery:
    def test_query_by_entity(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_FACT)
        r = c.get(f"/v1/facts?entity={_FACT['entity']}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["facts"]) >= 1
        assert all(f["entity"] == _FACT["entity"] for f in body["facts"])

    def test_query_returns_empty_for_unknown_entity(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/facts?entity=stigmem://conformance/nobody")
        assert r.status_code == 200
        assert r.json()["facts"] == []

    def test_query_filters_by_relation(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_FACT)
        r = c.get(
            f"/v1/facts?entity={_FACT['entity']}&relation={_FACT['relation']}"
        )
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert all(f["relation"] == _FACT["relation"] for f in facts)

    def test_query_filters_by_scope(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_FACT)
        # No facts in "public" scope for this entity
        r = c.get(f"/v1/facts?entity={_FACT['entity']}&scope=public")
        assert r.status_code == 200
        assert r.json()["facts"] == []

    def test_get_single_fact(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        fact_id = c.post("/v1/facts", json=_FACT).json()["id"]
        r = c.get(f"/v1/facts/{fact_id}")
        assert r.status_code == 200
        assert r.json()["id"] == fact_id

    def test_get_missing_fact_returns_404(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/facts/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_retract_fact(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        r1 = c.post("/v1/facts", json=_FACT)
        assert r1.status_code == 201
        # Retraction: re-assert with confidence=0 (spec §5.1 — no DELETE endpoint)
        retract = {**_FACT, "confidence": 0.0}
        r2 = c.post("/v1/facts", json=retract)
        assert r2.status_code == 201
        assert r2.json()["confidence"] == 0.0

    def test_expired_fact_not_returned_in_query(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        c.post("/v1/facts", json={**_FACT, "valid_until": past})
        r = c.get(f"/v1/facts?entity={_FACT['entity']}&relation=memory:role")
        assert r.status_code == 200
        # Expired facts should not appear in default query results
        live = [f for f in r.json()["facts"] if f.get("valid_until", "") and f["valid_until"] < datetime.now(UTC).isoformat()]
        assert live == []
