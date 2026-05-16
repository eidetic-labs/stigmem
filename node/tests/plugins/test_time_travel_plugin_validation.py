from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _as_of(offset_seconds: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


def _assert_fact(client: TestClient, *, entity: str, value: str) -> str:
    response = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": "rel:time-travel-validation",
            "value": {"type": "string", "v": value},
            "source": "agent:test",
            "scope": "local",
            "confidence": 1.0,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_default_install_rejects_as_of_until_time_travel_plugin_loads(
    client: TestClient,
) -> None:
    facts_response = client.get("/v1/facts", params={"as_of": _as_of(-1)})
    assert facts_response.status_code == 501
    assert facts_response.json()["detail"]["code"] == "time_travel_plugin_not_loaded"

    recall_response = client.post(
        "/v1/recall",
        json={"query": "snapshot content", "scope": "local", "as_of": _as_of(-1)},
    )
    assert recall_response.status_code == 501
    assert recall_response.json()["detail"]["code"] == "time_travel_plugin_not_loaded"


def test_plugin_loaded_client_accepts_as_of_fact_query_and_recall(
    time_travel_client: TestClient,
) -> None:
    before = _as_of(-2)
    fact_id = _assert_fact(
        time_travel_client,
        entity="stigmem://plugins/time-travel-validation",
        value="snapshot content",
    )
    after = _as_of(2)

    facts_after = time_travel_client.get(
        "/v1/facts",
        params={
            "entity": "stigmem://plugins/time-travel-validation",
            "as_of": after,
        },
    )
    assert facts_after.status_code == 200, facts_after.text
    returned_after = {fact["id"] for fact in facts_after.json()["facts"]}
    assert fact_id in returned_after

    facts_before = time_travel_client.get(
        "/v1/facts",
        params={
            "entity": "stigmem://plugins/time-travel-validation",
            "as_of": before,
        },
    )
    assert facts_before.status_code == 200, facts_before.text
    returned_before = {fact["id"] for fact in facts_before.json()["facts"]}
    assert fact_id not in returned_before

    recall_after = time_travel_client.post(
        "/v1/recall",
        json={"query": "snapshot content", "scope": "local", "as_of": after},
    )
    assert recall_after.status_code == 200, recall_after.text
    assert any(item["fact"]["id"] == fact_id for item in recall_after.json()["facts"])
