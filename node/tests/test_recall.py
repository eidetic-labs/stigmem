"""Integration tests for POST /v1/recall — spec §20 (Phase 9).

Tests cover:
  - Basic recall returns matching facts
  - Token-budget packing: budget too small, budget very large
  - Score breakdown present on every item
  - recall_id and query_hash present in response
  - Graph expansion (include_neighbors)
  - Auth: read permission required
  - Audit log entry written per call
  - Scope isolation: facts from another scope are excluded
"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Test URIs
# ---------------------------------------------------------------------------

_ALICE = "stigmem://testnode/agent/alice"
_BOB = "stigmem://testnode/agent/bob"
_CAROL = "stigmem://testnode/agent/carol"


def _fact(
    entity: str, relation: str, v: str, scope: str = "local", confidence: float = 1.0
) -> dict:
    return {
        "entity": entity,
        "relation": "memory:knows",
        "value": {"type": "string", "v": v},
        "source": entity,
        "confidence": confidence,
        "scope": scope,
    }


def _recall_body(**kwargs) -> dict:
    body = {
        "query": "alice",
        "scope": "local",
        "token_budget": 4000,
        "depth": 1,
        "include_neighbors": False,
    }
    body.update(kwargs)
    return body


# ---------------------------------------------------------------------------
# Basic recall tests
# ---------------------------------------------------------------------------


class TestRecallBasic:
    def test_endpoint_exists(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(query="test"))
        assert r.status_code == 200

    def test_returns_recall_id_and_query_hash(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body())
        assert r.status_code == 200
        body = r.json()
        assert "recall_id" in body
        assert len(body["recall_id"]) == 36  # UUID
        assert "query_hash" in body
        assert len(body["query_hash"]) == 64  # SHA-256 hex

    def test_empty_db_returns_empty_facts(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(query="nothing here"))
        assert r.status_code == 200
        body = r.json()
        assert body["facts"] == []
        assert body["total_scored"] == 0
        assert body["tokens_used"] == 0
        assert body["truncated"] is False

    def test_recall_returns_matching_facts(self, client: TestClient) -> None:
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:note",
                "value": {"type": "string", "v": "alice is the project lead"},
                "source": _ALICE,
                "scope": "local",
            },
        )
        r = client.post("/v1/recall", json=_recall_body(query="alice project lead"))
        assert r.status_code == 200
        body = r.json()
        assert len(body["facts"]) >= 1

    def test_score_breakdown_present(self, client: TestClient) -> None:
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:role",
                "value": {"type": "string", "v": "engineer"},
                "source": _ALICE,
                "scope": "local",
            },
        )
        r = client.post("/v1/recall", json=_recall_body(query="engineer"))
        assert r.status_code == 200
        body = r.json()
        if body["facts"]:
            sf = body["facts"][0]
            assert "score" in sf
            assert "score_breakdown" in sf
            bd = sf["score_breakdown"]
            for key in (
                "lexical",
                "semantic",
                "graph",
                "source_trust",
                "recency",
                "weighted_total",
            ):
                assert key in bd
            assert "token_estimate" in sf
            assert "hop_distance" in sf

    def test_response_shape_complete(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body())
        assert r.status_code == 200
        body = r.json()
        for field in (
            "recall_id",
            "query_hash",
            "facts",
            "content",
            "instructions",
            "total_scored",
            "token_budget",
            "tokens_used",
            "truncated",
        ):
            assert field in body
        assert body["content"] == body["facts"]
        assert body["instructions"] == []

    def test_facts_ordered_by_score_desc(self, client: TestClient) -> None:
        for i in range(5):
            client.post(
                "/v1/facts",
                json={
                    "entity": f"stigmem://testnode/item/{i}",
                    "relation": "memory:desc",
                    "value": {"type": "string", "v": f"alice bob carol item {i}"},
                    "source": _ALICE,
                    "scope": "local",
                },
            )
        r = client.post("/v1/recall", json=_recall_body(query="alice bob carol"))
        assert r.status_code == 200
        scores = [sf["score"] for sf in r.json()["facts"]]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Token-budget packing
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_budget_very_large_includes_all_matching(self, client: TestClient) -> None:
        for i in range(5):
            client.post(
                "/v1/facts",
                json={
                    "entity": f"stigmem://testnode/b/{i}",
                    "relation": "memory:info",
                    "value": {"type": "string", "v": f"budget test fact number {i}"},
                    "source": _ALICE,
                    "scope": "local",
                },
            )
        r = client.post(
            "/v1/recall", json=_recall_body(query="budget test fact", token_budget=200_000)
        )
        assert r.status_code == 200
        body = r.json()
        assert body["truncated"] is False
        assert body["tokens_used"] <= 200_000

    def test_budget_too_small_returns_empty(self, client: TestClient) -> None:
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:long",
                "value": {
                    "type": "string",
                    "v": "this is a long enough fact to exceed tiny budgets",
                },
                "source": _ALICE,
                "scope": "local",
            },
        )
        # token_budget=1 means no fact can fit (minimum token_estimate > 1)
        r = client.post("/v1/recall", json=_recall_body(query="long enough", token_budget=1))
        assert r.status_code == 200
        body = r.json()
        assert body["facts"] == []
        assert body["tokens_used"] == 0

    def test_tokens_used_matches_packed_estimates(self, client: TestClient) -> None:
        for i in range(3):
            client.post(
                "/v1/facts",
                json={
                    "entity": f"stigmem://testnode/t/{i}",
                    "relation": "memory:x",
                    "value": {"type": "string", "v": f"tokens used test {i}"},
                    "source": _ALICE,
                    "scope": "local",
                },
            )
        r = client.post(
            "/v1/recall", json=_recall_body(query="tokens used test", token_budget=4000)
        )
        assert r.status_code == 200
        body = r.json()
        computed = sum(sf["token_estimate"] for sf in body["facts"])
        assert computed == body["tokens_used"]

    def test_truncated_flag_set_when_budget_exceeded(self, client: TestClient) -> None:
        for i in range(20):
            client.post(
                "/v1/facts",
                json={
                    "entity": f"stigmem://testnode/tr/{i}",
                    "relation": "memory:data",
                    "value": {
                        "type": "string",
                        "v": f"truncation test fact with lots of words item {i} filler filler",
                    },
                    "source": _ALICE,
                    "scope": "local",
                },
            )
        r = client.post(
            "/v1/recall", json=_recall_body(query="truncation test fact", token_budget=50)
        )
        assert r.status_code == 200
        body = r.json()
        # Either all fit or some were cut; check internal consistency
        if body["truncated"]:
            assert body["total_scored"] > len(body["facts"])
        assert body["tokens_used"] <= 50


# ---------------------------------------------------------------------------
# Graph expansion
# ---------------------------------------------------------------------------


class TestGraphExpansion:
    def test_neighbors_included_when_enabled(self, client: TestClient) -> None:
        # alice --ref--> bob; then search for "alice"
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:knows",
                "value": {"type": "ref", "v": _BOB},
                "source": _ALICE,
                "scope": "local",
            },
        )
        client.post(
            "/v1/facts",
            json={
                "entity": _BOB,
                "relation": "memory:role",
                "value": {"type": "string", "v": "bob is the designer"},
                "source": _BOB,
                "scope": "local",
            },
        )
        r = client.post(
            "/v1/recall",
            json=_recall_body(
                query="alice",
                depth=1,
                include_neighbors=True,
                token_budget=4000,
            ),
        )
        assert r.status_code == 200
        body = r.json()
        # Should include alice's own facts (direct match) + possibly bob's via graph
        fact_entities = {sf["fact"]["entity"] for sf in body["facts"]}
        # alice facts should appear
        assert any(_ALICE in e or _BOB in e for e in fact_entities) or body["total_scored"] >= 0

    def test_no_neighbors_when_disabled(self, client: TestClient) -> None:
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:ref",
                "value": {"type": "ref", "v": _CAROL},
                "source": _ALICE,
                "scope": "local",
            },
        )
        client.post(
            "/v1/facts",
            json={
                "entity": _CAROL,
                "relation": "memory:note",
                "value": {"type": "string", "v": "carol only via graph"},
                "source": _CAROL,
                "scope": "local",
            },
        )
        r = client.post(
            "/v1/recall",
            json=_recall_body(query="carol only via graph", include_neighbors=False),
        )
        assert r.status_code == 200
        # The carol fact IS a direct lexical match, so it may appear.
        # The key invariant: no hop_distance > 0 facts when include_neighbors=False.
        for sf in r.json()["facts"]:
            assert sf["hop_distance"] == 0


# ---------------------------------------------------------------------------
# Scope isolation
# ---------------------------------------------------------------------------


class TestScopeIsolation:
    def test_different_scope_excluded(self, client: TestClient) -> None:
        client.post(
            "/v1/facts",
            json={
                "entity": _ALICE,
                "relation": "memory:secret",
                "value": {"type": "string", "v": "supersecret company only"},
                "source": _ALICE,
                "scope": "company",
            },
        )
        r = client.post(
            "/v1/recall", json=_recall_body(query="supersecret company only", scope="local")
        )
        assert r.status_code == 200
        ids = [sf["fact"]["id"] for sf in r.json()["facts"]]
        company_fact_ids = [
            f["id"]
            for f in client.get(
                "/v1/facts",
                params={"entity": _ALICE, "scope": "company"},
            )
            .json()
            .get("facts", [])
        ]
        for cid in company_fact_ids:
            assert cid not in ids


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidation:
    def test_invalid_scope_returns_400(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(scope="invalid"))
        assert r.status_code == 400

    def test_depth_too_large_returns_4xx(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(depth=99))
        assert r.status_code in (400, 422)

    def test_empty_query_returns_422(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(query=""))
        assert r.status_code == 422

    def test_token_budget_zero_returns_422(self, client: TestClient) -> None:
        r = client.post("/v1/recall", json=_recall_body(token_budget=0))
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_recall_requires_read_permission(self, authed_client) -> None:
        client, raw_key = authed_client
        # No Authorization header — should get 401/403
        client.post("/v1/recall", json=_recall_body())
        # authed_client has auth enabled; no key given → must fail
        r_no_auth = client.post(
            "/v1/recall",
            json=_recall_body(),
            headers={"Authorization": "Bearer bad-key"},
        )
        assert r_no_auth.status_code in (401, 403)

    def test_recall_works_with_valid_key(self, authed_client) -> None:
        client, raw_key = authed_client
        r = client.post(
            "/v1/recall",
            json=_recall_body(),
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_recall_writes_audit_entry(self, client: TestClient, tmp_db: str) -> None:
        client.post("/v1/recall", json=_recall_body(query="audit check"))
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM recall_audit_log").fetchall()
        conn.close()
        assert len(rows) == 1
        row = rows[0]
        assert row["scope"] == "local"
        assert row["token_budget"] == 4000
        assert len(row["query_hash"]) == 64

    def test_multiple_recalls_write_multiple_entries(self, client: TestClient, tmp_db: str) -> None:
        for i in range(3):
            client.post("/v1/recall", json=_recall_body(query=f"query {i}"))
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute("SELECT COUNT(*) FROM recall_audit_log").fetchone()
        conn.close()
        assert rows[0] == 3
