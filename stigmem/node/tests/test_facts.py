"""Tests for the Stigmem fact assert/query API."""

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

    def test_namespaced_relation_no_warnings(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json=FACT)  # FACT uses "memory:role"
        assert r.status_code == 201
        assert r.json()["warnings"] == []

    def test_bare_relation_returns_warning(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "relation": "status"})
        assert r.status_code == 201
        body = r.json()
        assert body["warnings"]
        assert any("bare relation" in w for w in body["warnings"])

    def test_system_prefix_relation_returns_warning(self, client: TestClient) -> None:
        r = client.post("/v1/facts", json={**FACT, "relation": "stigmem:custom"})
        assert r.status_code == 201
        body = r.json()
        assert body["warnings"]
        assert any("reserved system prefix" in w for w in body["warnings"])


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

    def test_contradicted_excluded_by_default(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        client.post("/v1/facts", json={**FACT, "value": {"type": "string", "v": "CTO"}})
        r = client.get("/v1/facts?entity=user:alice&relation=memory:role&scope=company")
        assert r.json()["total"] == 0

    def test_contradicted_included_with_flag(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        client.post("/v1/facts", json={**FACT, "value": {"type": "string", "v": "CTO"}})
        r = client.get("/v1/facts?entity=user:alice&relation=memory:role&scope=company&include_contradicted=true")
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
        r = client.get("/.well-known/stigmem")
        assert r.status_code == 200

    def test_shape(self, client: TestClient) -> None:
        body = client.get("/.well-known/stigmem").json()
        assert body["version"] == "0.5"
        assert body["node_id"].startswith("stigmem:node:")
        assert body["auth"] in ("none", "required")
        assert body["federation"] == "disabled"
        assert isinstance(body["namespaces"], list)

    def test_auth_none_when_disabled(self, client: TestClient) -> None:
        assert client.get("/.well-known/stigmem").json()["auth"] == "none"

    def test_auth_required_when_enabled(self, authed_client: tuple[TestClient, str]) -> None:
        c, _ = authed_client
        assert c.get("/.well-known/stigmem").json()["auth"] == "required"


class TestHealthz:
    def test_health(self, client: TestClient) -> None:
        assert client.get("/healthz").json() == {"status": "ok"}


class TestLint:
    """Smoke tests for POST /v1/lint (spec §5.12)."""

    def test_lint_clean_scope(self, client: TestClient) -> None:
        r = client.post("/v1/lint", json={"scope": "company"})
        assert r.status_code == 200
        body = r.json()
        assert body["scope"] == "company"
        assert "findings" in body
        assert "checks_run" in body
        assert "fact_count" in body
        assert "checked_at" in body

    def test_lint_detects_contradiction(self, client: TestClient) -> None:
        FACT = {
            "entity": "lint:entity", "relation": "lint:rel",
            "value": {"type": "string", "v": "A"},
            "source": "agent:test", "confidence": 1.0, "scope": "company",
        }
        client.post("/v1/facts", json=FACT)
        client.post("/v1/facts", json={**FACT, "value": {"type": "string", "v": "B"}})

        r = client.post("/v1/lint", json={"scope": "company", "checks": ["contradiction"]})
        assert r.status_code == 200
        body = r.json()
        contradiction_findings = [f for f in body["findings"] if f["check"] == "contradiction"]
        assert len(contradiction_findings) >= 1
        assert contradiction_findings[0]["severity"] == "error"
        assert len(contradiction_findings[0]["fact_ids"]) == 2

    def test_lint_invalid_scope(self, client: TestClient) -> None:
        r = client.post("/v1/lint", json={"scope": "invalid"})
        assert r.status_code == 400

    def test_lint_detects_bare_relation(self, client: TestClient) -> None:
        client.post("/v1/facts", json={
            "entity": "stigmem://acme/project/test", "relation": "status",
            "value": {"type": "string", "v": "active"},
            "source": "agent:test", "confidence": 1.0, "scope": "company",
        })
        r = client.post("/v1/lint", json={"scope": "company", "checks": ["namespacing"]})
        assert r.status_code == 200
        body = r.json()
        ns_findings = [f for f in body["findings"] if f["check"] == "namespacing"]
        assert len(ns_findings) >= 1
        assert ns_findings[0]["severity"] == "warning"
        assert ns_findings[0]["relation"] == "status"

    def test_lint_no_namespacing_violation_for_prefixed_relation(self, client: TestClient) -> None:
        client.post("/v1/facts", json={
            "entity": "stigmem://acme/project/test", "relation": "pm:status",
            "value": {"type": "string", "v": "active"},
            "source": "agent:test", "confidence": 1.0, "scope": "company",
        })
        r = client.post("/v1/lint", json={"scope": "company", "checks": ["namespacing"]})
        body = r.json()
        ns_findings = [f for f in body["findings"] if f["check"] == "namespacing"]
        assert ns_findings == []

    def test_lint_namespacing_included_in_all_checks(self, client: TestClient) -> None:
        r = client.post("/v1/lint", json={"scope": "company"})
        assert r.status_code == 200
        assert "namespacing" in r.json()["checks_run"]
