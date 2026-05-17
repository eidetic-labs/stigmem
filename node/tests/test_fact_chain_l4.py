"""ADR-016 L4 local hash-chain coverage."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _assert_fact(client: TestClient, entity: str, value: str) -> dict[str, Any]:
    response = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": "test:chain",
            "value": {"type": "string", "v": value},
            "source": "stigmem://test/agent/chain",
            "scope": "local",
            "confidence": 1.0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_local_fact_writes_append_chain_entries(client: TestClient) -> None:
    first = _assert_fact(client, "stigmem://test/entity/chain-1", "one")
    second = _assert_fact(client, "stigmem://test/entity/chain-2", "two")

    from stigmem_node.db import db
    from stigmem_node.fact_chain import verify_fact_chain

    with db() as conn:
        rows = conn.execute(
            """
            SELECT fact_id, chain_seq, event_hash, previous_hash, chain_hash
            FROM fact_chain
            WHERE tenant_id = 'default'
            ORDER BY chain_seq
            """
        ).fetchall()
        verification = verify_fact_chain(conn, tenant_id="default")

    assert [row["fact_id"] for row in rows] == [first["id"], second["id"]]
    assert [int(row["chain_seq"]) for row in rows] == [1, 2]
    assert rows[0]["previous_hash"] is None
    assert rows[1]["previous_hash"] == rows[0]["chain_hash"]
    assert rows[0]["event_hash"].startswith("sha256:")
    assert rows[0]["chain_hash"].startswith("sha256:")
    assert verification.valid is True
    assert verification.checked_entries == 2


def test_recall_full_verification_includes_chain_proof(client: TestClient) -> None:
    _assert_fact(client, "stigmem://test/entity/chain-proof-1", "proof one")
    _assert_fact(client, "stigmem://test/entity/chain-proof-2", "proof two")

    response = client.post(
        "/v1/recall",
        json={
            "query": "chain-proof",
            "scope": "local",
            "limit": 5,
            "weights": {"lexical": 1.0, "semantic": 0.0, "graph": 0.0},
        },
        headers={"Stigmem-Verify": "full"},
    )

    assert response.status_code == 200, response.text
    proof = response.json()["chain_proof"]
    assert proof["tenant_id"] == "default"
    assert proof["checked_entries"] == 2
    assert proof["head_hash"].startswith("sha256:")


def test_fact_chain_verification_detects_rewritten_link(client: TestClient) -> None:
    _assert_fact(client, "stigmem://test/entity/chain-rewrite-1", "one")
    second = _assert_fact(client, "stigmem://test/entity/chain-rewrite-2", "two")

    from stigmem_node.db import db
    from stigmem_node.fact_chain import verify_fact_chain

    with db() as conn:
        conn.execute(
            "UPDATE fact_chain SET previous_hash = ? WHERE tenant_id = ? AND chain_seq = ?",
            ("sha256:" + "0" * 64, "default", 2),
        )
        verification = verify_fact_chain(conn, tenant_id="default")

    assert verification.valid is False
    assert verification.mismatch_reason == "previous_hash_mismatch"
    assert verification.fact_id == second["id"]
    assert verification.chain_seq == 2


def test_recall_full_verification_rejects_broken_chain(client: TestClient) -> None:
    _assert_fact(client, "stigmem://test/entity/chain-reject-1", "one")
    second = _assert_fact(client, "stigmem://test/entity/chain-reject-2", "two")

    from stigmem_node.db import db

    with db() as conn:
        conn.execute(
            "UPDATE fact_chain SET previous_hash = ? WHERE tenant_id = ? AND chain_seq = ?",
            ("sha256:" + "0" * 64, "default", 2),
        )

    response = client.post(
        "/v1/recall",
        json={
            "query": "chain-reject",
            "scope": "local",
            "limit": 5,
            "weights": {"lexical": 1.0, "semantic": 0.0, "graph": 0.0},
        },
        headers={"Stigmem-Verify": "full"},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "fact_chain_mismatch"
    assert detail["mismatch_reason"] == "previous_hash_mismatch"
    assert detail["fact_id"] == second["id"]
