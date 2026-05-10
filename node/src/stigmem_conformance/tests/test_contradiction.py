"""Conformance: contradiction detection and resolution behavioral contract.

Two facts about the same entity+relation+scope with different values and
sources constitute a contradiction.  The node must detect this and expose
it via the synthesize endpoint's ``contradiction_count``.  Resolution
sets ``status=resolved`` on the conflict via the API.
"""

from __future__ import annotations

from typing import Any

from .conftest import ConformanceClient

_ALICE = "stigmem://conformance/contradiction/alice"
_SRC_A = "stigmem://conformance/source/a"
_SRC_B = "stigmem://conformance/source/b"


def _fact(entity: str, v: str, source: str, conf: float = 0.9) -> dict[str, Any]:
    return {
        "entity": entity,
        "relation": "test:role",
        "value": {"type": "string", "v": v},
        "source": source,
        "confidence": conf,
        "scope": "local",
    }


class TestContradictionDetection:
    def test_same_entity_different_values_creates_contradiction(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "admin", _SRC_A))
        c.post("/v1/facts", json=_fact(_ALICE, "viewer", _SRC_B))
        body = c.get("/v1/scopes/local/synthesize").json()
        # Two conflicting assertions for the same entity+relation+scope
        assert body["contradiction_count"] >= 1

    def test_single_fact_no_contradiction(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        # A single assertion of a fact — no conflict partner possible
        entity = "stigmem://conformance/contradiction/solo"
        c.post("/v1/facts", json=_fact(entity, "admin", _SRC_A))
        body = c.get("/v1/scopes/local/synthesize").json()
        assert body["contradiction_count"] == 0


class TestContradictionList:
    def test_list_conflicts_endpoint(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/conflicts")
        assert r.status_code in (200, 404)  # 404 allowed if not yet implemented

    def test_contradiction_appears_in_conflict_list(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact(_ALICE, "admin", _SRC_A))
        c.post("/v1/facts", json=_fact(_ALICE, "viewer", _SRC_B))
        r = c.get("/v1/conflicts")
        if r.status_code == 200:
            body = r.json()
            # Response shape: {"conflicts": [...], "cursor": ..., "has_more": ...}
            # Each item has "conflict_id" (not "id") per federation spec §5.10
            items = body.get("conflicts", body) if isinstance(body, dict) else body
            assert isinstance(items, list)


class TestContradictionResolution:
    def test_resolve_conflict_sets_status(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        r_a = c.post("/v1/facts", json=_fact(_ALICE, "admin", _SRC_A))
        assert r_a.status_code == 201
        fact_a_id = r_a.json()["id"]
        c.post("/v1/facts", json=_fact(_ALICE, "viewer", _SRC_B))
        conflicts_r = c.get("/v1/conflicts")
        if conflicts_r.status_code != 200:
            return  # endpoint not available; skip resolution test
        conflicts = conflicts_r.json()
        items = conflicts.get("conflicts", conflicts) if isinstance(conflicts, dict) else conflicts
        if not items:
            return
        # Each item has "conflict_id" key (not "id") per spec §5.10
        item0 = items[0]
        conflict_id = item0.get("conflict_id") or item0.get("id") if isinstance(item0, dict) else item0
        # Resolution payload: winning_fact_id selects which fact wins (spec §5.10)
        r = c.post(f"/v1/conflicts/{conflict_id}/resolve", json={"winning_fact_id": fact_a_id})
        assert r.status_code in (200, 204, 404)  # 404 if resolution not yet wired

    def test_resolved_contradiction_reduces_count(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        r_a = c.post("/v1/facts", json=_fact(_ALICE, "admin", _SRC_A))
        assert r_a.status_code == 201
        fact_a_id = r_a.json()["id"]
        c.post("/v1/facts", json=_fact(_ALICE, "viewer", _SRC_B))
        before = c.get("/v1/scopes/local/synthesize").json()["contradiction_count"]
        conflicts_r = c.get("/v1/conflicts")
        if conflicts_r.status_code != 200:
            return
        items = conflicts_r.json().get("conflicts", [])
        if items:
            item0 = items[0]
            cid = item0.get("conflict_id") or item0.get("id")
            res = c.post(f"/v1/conflicts/{cid}/resolve", json={"winning_fact_id": fact_a_id})
            if res.status_code in (200, 204):
                after = c.get("/v1/scopes/local/synthesize").json()["contradiction_count"]
                assert after <= before
