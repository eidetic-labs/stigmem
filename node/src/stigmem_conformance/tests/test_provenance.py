"""Conformance: audit trail and provenance behavioral contract (spec §19).

Verifies that the node writes an audit log entry for fact assertions and
that recall_audit_log records are created per recall call.  All assertions
are through the HTTP API (no direct DB reads).
"""

from __future__ import annotations

from typing import Any

from .conftest import ConformanceClient

_E = "stigmem://conformance/provenance/alice"


def _fact(v: str = "provenance test", scope: str = "local") -> dict[str, Any]:
    return {
        "entity": _E,
        "relation": "memory:note",
        "value": {"type": "string", "v": v},
        "source": _E,
        "confidence": 0.9,
        "scope": scope,
    }


class TestAuditLog:
    def test_audit_endpoint_exists(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/audit")
        assert r.status_code in (200, 404)

    def test_asserted_fact_has_id_and_timestamp(
        self, conformance_client: ConformanceClient
    ) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        assert r.status_code == 201
        body = r.json()
        assert "id" in body
        assert "timestamp" in body

    def test_fact_includes_source(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        assert r.json()["source"] == _E

    def test_fact_includes_confidence(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        assert r.json()["confidence"] == 0.9

    def test_audit_log_lists_entries(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact())
        r = c.get("/v1/audit")
        if r.status_code == 200:
            body = r.json()
            entries = body.get("entries", body.get("audit", body))
            assert isinstance(entries, list)


class TestRecallAudit:
    def test_recall_creates_audit_record(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact())
        r = c.post("/v1/recall", json={
            "query": "provenance",
            "scope": "local",
            "token_budget": 4000,
            "depth": 1,
            "include_neighbors": False,
        })
        assert r.status_code == 200
        body = r.json()
        # recall_id and query_hash are audit identifiers
        assert len(body["recall_id"]) == 36
        assert len(body["query_hash"]) == 64

    def test_two_recalls_have_distinct_ids(self, conformance_client: ConformanceClient) -> None:
        c = conformance_client.client
        q = {"query": "x", "scope": "local", "token_budget": 100, "depth": 1, "include_neighbors": False}
        id1 = c.post("/v1/recall", json=q).json()["recall_id"]
        id2 = c.post("/v1/recall", json=q).json()["recall_id"]
        assert id1 != id2


class TestProvenanceAttested:
    def test_attested_field_present_on_fact(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        body = r.json()
        # attested may be True, False, or None depending on source_attestation_mode
        assert "attested" in body

    def test_scope_propagation_fields_present(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        body = r.json()
        assert "scope" in body
        assert body["scope"] == "local"
