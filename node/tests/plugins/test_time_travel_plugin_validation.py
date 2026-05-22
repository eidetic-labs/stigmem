from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stigmem_node.plugins.testing import stigmem_plugins

_FEATURE_SRC = Path(__file__).resolve().parents[3] / "experimental" / "time-travel" / "src"
if str(_FEATURE_SRC) not in sys.path:
    sys.path.insert(0, str(_FEATURE_SRC))

_PLUGIN = importlib.import_module("stigmem_plugin_time_travel")


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


def test_registered_plugin_requires_explicit_operator_enablement(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STIGMEM_TIME_TRAVEL_ENABLED", raising=False)
    monkeypatch.delenv("STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF", raising=False)
    monkeypatch.delenv("STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF", raising=False)

    with stigmem_plugins([_PLUGIN.plugin_manifest()]):
        facts_response = client.get("/v1/facts", params={"as_of": _as_of(-1)})
        assert facts_response.status_code == 403
        assert facts_response.json()["detail"]["code"] == "time_travel_plugin_disabled"

        recall_response = client.post(
            "/v1/recall",
            json={"query": "snapshot content", "scope": "local", "as_of": _as_of(-1)},
        )
        assert recall_response.status_code == 403
        assert recall_response.json()["detail"]["code"] == "time_travel_plugin_disabled"


def test_registered_plugin_honors_separate_surface_gates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF", "true")
    monkeypatch.delenv("STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF", raising=False)

    with stigmem_plugins([_PLUGIN.plugin_manifest()]):
        facts_response = client.get("/v1/facts", params={"as_of": _as_of(-1)})
        assert facts_response.status_code == 200, facts_response.text

        recall_response = client.post(
            "/v1/recall",
            json={"query": "snapshot content", "scope": "local", "as_of": _as_of(-1)},
        )
        assert recall_response.status_code == 403
        assert recall_response.json()["detail"]["code"] == "time_travel_plugin_disabled"


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
