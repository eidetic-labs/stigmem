"""Tests for the Muninn fact assert/query API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "company",
}


class TestAssertFact:
    def test_assert_returns_201(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201
        body = r.json()
        assert body["entity"] == "user:alice"
        assert body["relation"] == "memory:role"
        assert body["id"]
        assert body["timestamp"]
        assert body["valid_until"] is None

    def test_assert_text_type(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={**FACT, "value": {"type": "text", "v": "Long narrative content here."}},
        )
        assert r.status_code == 201
        assert r.json()["value"]["type"] == "text"

    def test_assert_null_type(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "value": {"type": "null"}})
        assert r.status_code == 201
        assert r.json()["value"]["v"] is None

    def test_assert_boolean(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts", json={**FACT, "value": {"type": "boolean", "v": True}}
        )
        assert r.status_code == 201
        assert r.json()["value"]["v"] is True

    def test_assert_number(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts", json={**FACT, "value": {"type": "number", "v": 42.5}}
        )
        assert r.status_code == 201
        assert r.json()["value"]["v"] == 42.5

    def test_assert_with_valid_until(self, client: TestClient) -> None:
        expiry = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        r = client.post("/v1/facts", json={**FACT, "valid_until": expiry})
        assert r.status_code == 201
        assert r.json()["valid_until"] == expiry

    def test_assert_invalid_scope(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "scope": "universe"})
        assert r.status_code == 422

    def test_assert_invalid_value_type(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "value": {"type": "bytes"}})
        assert r.status_code == 422

    def test_assert_confidence_out_of_range(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "confidence": 1.5})
        assert r.status_code == 422


class TestQueryFacts:
    def test_empty_query(self, client: TestClient) -> None:
        r = client.get("/v1/facts")
        assert r.status_code == 200
        body = r.json()
        assert body["facts"] == []
        assert body["total"] == 0
        assert body["cursor"] is None

    def test_query_after_assert(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        r = client.get("/v1/facts?entity=user:alice")
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert len(facts) == 1
        assert facts[0]["entity"] == "user:alice"

    def test_query_by_relation(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        client.post("/v1/facts", json={**FACT, "relation": "memory:team"})
        r = client.get("/v1/facts?relation=memory:role")
        assert r.json()["total"] == 1

    def test_min_confidence_filter(self, client: TestClient) -> None:
        client.post("/v1/facts", json={**FACT, "confidence": 0.3})
        client.post("/v1/facts", json={**FACT, "confidence": 0.9, "relation": "memory:x"})
        r = client.get("/v1/facts?min_confidence=0.5")
        facts = r.json()["facts"]
        assert all(f["confidence"] >= 0.5 for f in facts)

    def test_contradiction_flagged(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        client.post("/v1/facts", json={**FACT, "value": {"type": "string", "v": "CTO"}})
        r = client.get("/v1/facts?entity=user:alice&relation=memory:role&scope=company")
        facts = r.json()["facts"]
        assert len(facts) == 2
        assert all(f["contradicted"] for f in facts)

    def test_no_contradiction_single_fact(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        r = client.get("/v1/facts?entity=user:alice")
        assert r.json()["facts"][0]["contradicted"] is False


class TestExpiry:
    def test_expired_fact_excluded_by_default(self, client: TestClient) -> None:
        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        client.post("/v1/facts", json={**FACT, "valid_until": past})
        r = client.get("/v1/facts?entity=user:alice")
        assert r.json()["total"] == 0

    def test_expired_fact_included_with_flag(self, client: TestClient) -> None:
        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        client.post("/v1/facts", json={**FACT, "valid_until": past})
        r = client.get("/v1/facts?entity=user:alice&include_expired=true")
        assert r.json()["total"] == 1

    def test_non_expiring_fact_always_returned(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        r = client.get("/v1/facts?entity=user:alice")
        assert r.json()["total"] == 1


class TestGetById:
    def test_get_existing_fact(self, client: TestClient) -> None:
        created = client.post("/v1/facts", json=FACT).json()
        r = client.get(f"/v1/facts/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_missing_fact(self, client: TestClient) -> None:
        r = client.get("/v1/facts/nonexistent-id")
        assert r.status_code == 404


class TestAuth:
    def test_no_token_allowed_when_auth_disabled(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

    def test_valid_token_accepted(self, authed_client: tuple[TestClient, str]) -> None:
        c, key = authed_client
        r = c.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key}"})
        assert r.status_code == 201

    def test_missing_token_rejected_when_auth_required(
        self, authed_client: tuple[TestClient, str]
    ) -> None:
        c, _ = authed_client
        r = c.post("/v1/facts", json=FACT)
        assert r.status_code == 401

    def test_bad_token_rejected(self, authed_client: tuple[TestClient, str]) -> None:
        c, _ = authed_client
        r = c.post("/v1/facts", json=FACT, headers={"Authorization": "Bearer bad-key"})
        assert r.status_code == 401


class TestWellKnown:
    def test_returns_200(self, client: TestClient) -> None:
        r = client.get("/.well-known/muninn")
        assert r.status_code == 200

    def test_shape(self, client: TestClient) -> None:
        body = client.get("/.well-known/muninn").json()
        assert body["version"] == "0.3"
        assert body["node_id"].startswith("muninn:node:")
        assert body["auth"] in ("none", "required")
        assert body["federation"] == "disabled"
        assert isinstance(body["namespaces"], list)

    def test_auth_none_when_disabled(self, client: TestClient) -> None:
        assert client.get("/.well-known/muninn").json()["auth"] == "none"

    def test_auth_required_when_enabled(self, authed_client: tuple[TestClient, str]) -> None:
        c, _ = authed_client
        assert c.get("/.well-known/muninn").json()["auth"] == "required"


class TestHealthz:
    def test_health(self, client: TestClient) -> None:
        assert client.get("/healthz").json() == {"status": "ok"}
