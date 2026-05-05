"""Conformance: graph adjacency / neighbors behavioral contract (spec §20).

All tests are black-box against the HTTP API.  They verify that the backend
correctly maintains the entity-edge index when ref-type facts are asserted,
and serves accurate traversal results at varying depths and scopes.
"""

from __future__ import annotations

import pytest

from .conftest import ConformanceClient

_A = "stigmem://conformance/graph/alice"
_B = "stigmem://conformance/graph/bob"
_C = "stigmem://conformance/graph/carol"


def _ref(entity: str, rel: str, target: str, scope: str = "local", conf: float = 1.0) -> dict:
    return {
        "entity": entity,
        "relation": rel,
        "value": {"type": "ref", "v": target},
        "source": entity,
        "confidence": conf,
        "scope": scope,
    }


class TestGraphNeighbors:
    def test_endpoint_exists(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get(f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local")
        assert r.status_code == 200

    def test_no_edges_returns_empty_neighbors(self, conformance_client: ConformanceClient) -> None:
        body = conformance_client.client.get(
            f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local"
        ).json()
        assert body["entity"] == _A
        assert body["neighbors"] == []

    def test_ref_fact_creates_edge(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_ref(_A, "memory:knows", _B))
        body = c.get(f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local").json()
        entities = [n["entity"] for n in body["neighbors"]]
        assert _B in entities

    def test_hops_field_is_1_for_direct_neighbor(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_ref(_A, "memory:knows", _B))
        body = c.get(f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local").json()
        b_entry = next((n for n in body["neighbors"] if n["entity"] == _B), None)
        assert b_entry is not None
        assert b_entry["hops"] == 1

    def test_depth2_reaches_second_hop(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_ref(_A, "memory:knows", _B))
        c.post("/v1/facts", json=_ref(_B, "memory:knows", _C))
        body = c.get(f"/v1/graph/neighbors?entity={_A}&depth=2&scope=local").json()
        entities = [n["entity"] for n in body["neighbors"]]
        assert _C in entities
        c_entry = next(n for n in body["neighbors"] if n["entity"] == _C)
        assert c_entry["hops"] == 2

    def test_scope_filters_edges(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_ref(_A, "memory:knows", _B, scope="company"))
        # query local scope — should not see company-scoped edge
        body = c.get(f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local").json()
        entities = [n["entity"] for n in body["neighbors"]]
        assert _B not in entities

    def test_retracted_ref_removes_edge(self, conformance_client: ConformanceClient) -> None:
        pytest.skip(
            "Graph edge removal via HTTP is not yet implemented in the reference node: "
            "POST /v1/facts with confidence=0 creates a new edge record rather than zeroing "
            "the original edge. Tracked as a known limitation in spec §20.1.3."
        )

    def test_response_has_entity_field(self, conformance_client: ConformanceClient) -> None:
        body = conformance_client.client.get(
            f"/v1/graph/neighbors?entity={_A}&depth=1&scope=local"
        ).json()
        assert "entity" in body
        assert "neighbors" in body
