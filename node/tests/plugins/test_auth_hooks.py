from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node.auth import Identity
from stigmem_node.plugins import Allow, Deny, PluginContext, PluginManifest, TenantContext
from stigmem_node.plugins.testing import stigmem_plugins


def test_identity_and_tenant_resolve_hooks_fire_for_dependency(client: TestClient) -> None:
    calls: list[str] = []

    def identity_resolve(_ctx: PluginContext, value: Identity, **_: object) -> Identity:
        calls.append(f"identity:{value.entity_uri}")
        return value

    def tenant_resolve(_ctx: PluginContext, value: TenantContext, **_: object) -> TenantContext:
        calls.append(f"tenant:{value.tenant_id}")
        return value

    manifest = PluginManifest(
        name="auth-tracker",
        version="1.0.0",
        hooks={
            "identity_resolve": identity_resolve,
            "tenant_resolve": tenant_resolve,
        },
    )

    with stigmem_plugins([manifest]):
        response = client.get("/v1/me")

    assert response.status_code == 200
    assert calls == ["identity:anon:trusted", "tenant:default"]


def test_tenant_resolve_can_replace_identity_tenant(client: TestClient) -> None:
    def tenant_resolve(_ctx: PluginContext, _value: TenantContext, **_: object) -> TenantContext:
        return TenantContext(tenant_id="plugin-tenant")

    manifest = PluginManifest(
        name="tenant-plugin",
        version="1.0.0",
        hooks={"tenant_resolve": tenant_resolve},
    )

    with stigmem_plugins([manifest]):
        response = client.get("/v1/me")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "plugin-tenant"


def test_capability_check_can_deny_existing_permission(client: TestClient) -> None:
    calls: list[str] = []

    def capability_check(_ctx: PluginContext, **kwargs: object) -> Deny | Allow:
        calls.append(str(kwargs["capability"]))
        if kwargs["capability"] == "read":
            return Deny("read disabled")
        return Allow()

    manifest = PluginManifest(
        name="capability-deny",
        version="1.0.0",
        hooks={"capability_check": capability_check},
    )

    with stigmem_plugins([manifest]):
        response = client.get("/v1/facts")

    assert response.status_code == 403
    assert response.json()["detail"] == "read permission required"
    assert calls == ["read"]
