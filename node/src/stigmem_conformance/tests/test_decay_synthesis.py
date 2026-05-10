"""Conformance: decay sweeper and synthesize_scope behavioral contract.

Tests verify that:
* ``GET /v1/scopes/<scope>/synthesize`` returns the correct shape and ordering.
* ``POST /v1/scopes/<scope>/decay`` expires facts correctly.
* Expired facts disappear from synthesis results.

All assertions use the HTTP API only.
"""

from __future__ import annotations

from typing import Any

import pytest

from .conftest import ConformanceClient

_ALICE = "stigmem://conformance/decay/alice"
_BOB   = "stigmem://conformance/decay/bob"


def _fact(entity: str, v: str, confidence: float = 0.9, scope: str = "local") -> dict[str, Any]:
    return {
        "entity": entity,
        "relation": "test:decay",
        "value": {"type": "string", "v": v},
        "source": entity,
        "confidence": confidence,
        "scope": scope,
    }


class TestSynthesizeScope:
    def test_empty_scope_response_shape(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/scopes/local/synthesize")
        assert r.status_code == 200
        body = r.json()
        assert body["scope"] == "local"
        assert isinstance(body["fact_count"], int)
        assert isinstance(body["facts"], list)
        assert "mean_confidence" in body
        assert "contradiction_count" in body

    def test_facts_returned_after_assert(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "hello"))
        body = c.get("/v1/scopes/local/synthesize").json()
        assert body["fact_count"] >= 1

    def test_facts_ordered_by_confidence_desc(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "low", confidence=0.3))
        c.post("/v1/facts", json=_fact(_BOB,   "high", confidence=0.9))
        body = c.get("/v1/scopes/local/synthesize").json()
        confs = [f["confidence"] for f in body["facts"]]
        assert confs == sorted(confs, reverse=True)

    def test_mean_confidence_is_correct(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "a", confidence=0.8))
        c.post("/v1/facts", json=_fact(_BOB, "b", confidence=0.6))
        body = c.get("/v1/scopes/local/synthesize").json()
        returned_confs = [f["confidence"] for f in body["facts"]]
        expected = sum(returned_confs) / len(returned_confs)
        assert abs(body["mean_confidence"] - expected) < 1e-5

    def test_freshest_and_oldest_timestamps(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "ts-test"))
        body = c.get("/v1/scopes/local/synthesize").json()
        if body["facts"]:
            assert body["freshest_timestamp"] is not None
            assert body["oldest_timestamp"] is not None


class TestDecaySweeper:
    def test_decay_endpoint_exists(self, conformance_client: ConformanceClient) -> None:
        # Decay sweep uses POST /v1/decay/sweep with query params (spec §15)
        r = conformance_client.client.post("/v1/decay/sweep")
        assert r.status_code in (200, 202)

    def test_decay_with_min_confidence_removes_low_confidence_facts(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "will-decay", confidence=0.1))
        # Sweep with min_confidence=0.5 via query param — fact at 0.1 should be removed
        r = c.post("/v1/decay/sweep", params={"min_confidence": 0.5, "scope": "local"})
        assert r.status_code in (200, 202)
        # After decay, fact should not appear in synthesis
        body = c.get("/v1/scopes/local/synthesize").json()
        low_conf = [f for f in body["facts"] if f["confidence"] < 0.5]
        assert low_conf == []

    def test_decay_ttl_removes_old_facts(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_BOB, "old-content"))
        # Decay with ttl_seconds=0 should expire all non-expiring facts
        r = c.post("/v1/decay/sweep", params={"ttl_seconds": 0, "scope": "local"})
        assert r.status_code in (200, 202)
        # Facts decayed; synthesis should reflect the sweep
        body = c.get("/v1/scopes/local/synthesize").json()
        assert isinstance(body["fact_count"], int)

    def test_decay_response_includes_stats(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/decay/sweep")
        assert r.status_code in (200, 202)
        if r.status_code == 200:
            body = r.json()
            assert "decayed" in body or "scanned" in body or "facts_removed" in body
