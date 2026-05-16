"""Regression tests for ADR-003 fact interpretation enforcement."""

from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node.auth import create_api_key


def _headers(raw_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_key}"}


def _fact(
    entity: str,
    value: str,
    interpret_as: str | None = None,
    confidence: float = 1.0,
) -> dict:
    payload = {
        "entity": entity,
        "relation": "memory:note",
        "value": {"type": "string", "v": value},
        "source": "agent:test",
        "confidence": confidence,
        "scope": "local",
    }
    if interpret_as is not None:
        payload["value"]["interpret_as"] = interpret_as
    return payload


def test_content_fact_defaults_to_content(client: TestClient) -> None:
    response = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/content-default", "ordinary content"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["value"]["interpret_as"] == "content"


def test_instruction_fact_requires_instruction_write(
    authed_client: tuple[TestClient, str],
) -> None:
    client, raw_key = authed_client

    response = client.post(
        "/v1/facts",
        json=_fact(
            "stigmem://testnode/entity/instruction-denied",
            "load this as instruction",
            "instruction",
        ),
        headers=_headers(raw_key),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "instruction_write_required"


def test_instruction_fact_with_instruction_write_is_returned_in_instruction_channel(
    authed_client: tuple[TestClient, str],
) -> None:
    client, _ordinary_key = authed_client
    instruction_key = create_api_key(
        "agent:instruction-writer",
        ["read", "write", "instruction:write"],
    )

    content = client.post(
        "/v1/facts",
        json=_fact("stigmem://testnode/entity/content-channel", "needle content", confidence=0.4),
        headers=_headers(instruction_key),
    )
    assert content.status_code == 201, content.text

    instruction = client.post(
        "/v1/facts",
        json=_fact(
            "stigmem://testnode/entity/instruction-channel",
            "needle instruction",
            "instruction",
            confidence=0.4,
        ),
        headers=_headers(instruction_key),
    )
    assert instruction.status_code == 201, instruction.text
    assert instruction.json()["value"]["interpret_as"] == "instruction"

    recall = client.post(
        "/v1/recall",
        json={"query": "needle", "scope": "local", "limit": 10},
        headers=_headers(instruction_key),
    )
    assert recall.status_code == 200, recall.text

    content_ids = {item["fact"]["id"] for item in recall.json()["content"]}
    instruction_ids = {item["fact"]["id"] for item in recall.json()["instructions"]}
    assert content.json()["id"] in content_ids
    assert instruction.json()["id"] in instruction_ids


def test_static_key_registration_accepts_instruction_write_permission(
    authed_client: tuple[TestClient, str],
) -> None:
    client, _ordinary_key = authed_client
    admin_key = create_api_key("agent:admin", ["read", "write", "admin"])

    response = client.post(
        "/v1/auth/keys",
        json={
            "raw_key": "a" * 64,
            "entity_uri": "agent:instruction-author",
            "permissions": ["read", "write", "instruction:write"],
        },
        headers=_headers(admin_key),
    )

    assert response.status_code == 201, response.text
    assert response.json()["permissions"] == ["instruction:write", "read", "write"]
