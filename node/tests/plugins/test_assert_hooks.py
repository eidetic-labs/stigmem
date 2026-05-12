from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node.plugins import Allow, Deny, PluginContext, PluginManifest
from stigmem_node.plugins.testing import stigmem_plugins

FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "company",
}


def test_assert_hooks_fire_in_lifecycle_order(client: TestClient) -> None:
    calls: list[str] = []

    def authorize(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("authorize")
        return Allow()

    def validate(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("validate")
        return Allow()

    def transform(_ctx: PluginContext, value: object, **_: object) -> object:
        calls.append("transform")
        return value

    def persist(_ctx: PluginContext, **_: object) -> None:
        calls.append("persist")

    def propagate(_ctx: PluginContext, **_: object) -> None:
        calls.append("propagate")

    def audit(_ctx: PluginContext, **_: object) -> None:
        calls.append("audit")

    manifest = PluginManifest(
        name="assert-tracker",
        version="1.0.0",
        hooks={
            "pre_assert_authorize": authorize,
            "pre_assert_validate": validate,
            "pre_assert_transform": transform,
            "post_assert_persist": persist,
            "post_assert_propagate": propagate,
            "post_assert_audit": audit,
        },
    )

    with stigmem_plugins([manifest]):
        response = client.post("/v1/facts", json=FACT)

    assert response.status_code == 201
    assert calls == ["authorize", "validate", "transform", "persist", "propagate", "audit"]


def test_assert_authorize_deny_aborts_before_validate(client: TestClient) -> None:
    calls: list[str] = []

    def authorize(_ctx: PluginContext, **_: object) -> Deny:
        calls.append("authorize")
        return Deny("blocked by plugin")

    def validate(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("validate")
        return Allow()

    manifest = PluginManifest(
        name="assert-deny",
        version="1.0.0",
        hooks={
            "pre_assert_authorize": authorize,
            "pre_assert_validate": validate,
        },
    )

    with stigmem_plugins([manifest]):
        response = client.post("/v1/facts", json=FACT)

    assert response.status_code == 403
    assert response.json()["detail"] == "blocked by plugin"
    assert calls == ["authorize"]
