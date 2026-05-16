"""Regression tests for R-21 per-session feedback-loop defense."""

from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node.db import db


def _fact(entity: str, value: str, scope: str = "local") -> dict:
    return {
        "entity": entity,
        "relation": "memory:note",
        "value": {"type": "string", "v": value},
        "source": "agent:test",
        "confidence": 1.0,
        "scope": scope,
    }


def test_session_read_then_write_same_scope_requires_provenance(client: TestClient) -> None:
    source = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/source", "source"),
    )
    assert source.status_code == 201, source.text

    headers = {"Stigmem-Session": "session-r21-reject"}
    read = client.get("/v1/facts?scope=local", headers=headers)
    assert read.status_code == 200, read.text
    assert read.json()["facts"]

    blocked = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/poisoned", "poisoned"),
        headers=headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "feedback_loop_provenance_required"


def test_session_read_then_duplicate_cid_write_requires_provenance(
    client: TestClient,
) -> None:
    payload = _fact("stigmem://testnode/entity/duplicate-source", "source")
    source = client.post("/v1/facts", json=payload)
    assert source.status_code == 201, source.text

    headers = {"Stigmem-Session": "session-r21-duplicate"}
    read = client.get("/v1/facts?scope=local", headers=headers)
    assert read.status_code == 200, read.text
    assert read.json()["facts"]

    duplicate = client.post("/v1/facts", json=payload, headers=headers)
    assert duplicate.status_code == 403
    assert duplicate.json()["detail"]["code"] == "feedback_loop_provenance_required"


def test_session_summary_write_with_source_provenance_is_allowed(
    client: TestClient,
) -> None:
    source = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/source-provenance", "source"),
    )
    assert source.status_code == 201, source.text
    source_body = source.json()

    headers = {"Stigmem-Session": "session-r21-provenance"}
    read = client.get("/v1/facts?scope=local", headers=headers)
    assert read.status_code == 200, read.text

    summary = client.post(
        "/v1/facts",
        json={
            **_fact("stigmem://testnode/entity/summary", "summary"),
            "write_mode": "summarize_with_provenance",
            "derived_from": [
                {
                    "fact_id": source_body["id"],
                    "hash": source_body["cid"],
                }
            ],
        },
        headers=headers,
    )
    assert summary.status_code == 201, summary.text

    with db() as conn:
        access_rows = conn.execute(
            """SELECT access_type FROM session_scope_access
               WHERE session_id = ? AND scope = ?""",
            ("session-r21-provenance", "local"),
        ).fetchall()
    assert {row["access_type"] for row in access_rows} == {"read", "write"}

    provenance = client.get(f"/v1/facts/{summary.json()['id']}/provenance")
    assert provenance.status_code == 200, provenance.text
    entries = provenance.json()["derived_from"]
    assert entries == [
        {
            "hash": source_body["cid"],
            "fact_id": source_body["id"],
            "entity": "stigmem://testnode/entity/source-provenance",
            "exists": True,
        }
    ]


def test_read_then_write_without_session_remains_compatible(client: TestClient) -> None:
    source = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/no-session-source", "source"),
    )
    assert source.status_code == 201, source.text

    read = client.get("/v1/facts?scope=local")
    assert read.status_code == 200, read.text

    write = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/no-session-write", "still allowed"),
    )
    assert write.status_code == 201, write.text
