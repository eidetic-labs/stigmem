from __future__ import annotations

from fastapi.testclient import TestClient


def test_mcp_connectors_endpoint(client: TestClient) -> None:
    from stigmem_node.cli.mcp import EDITOR_CONFIGS

    response = client.get("/v1/mcp/connectors")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "1"
    connectors = payload["connectors"]
    assert {connector["editor"] for connector in connectors} == set(EDITOR_CONFIGS)
    for connector in connectors:
        assert connector["validation_tier"] in {"validated", "caveated", "experimental"}
        assert connector["docs_link"].startswith("https://docs.stigmem.dev/")
        assert connector["config_path"].startswith("~/")
