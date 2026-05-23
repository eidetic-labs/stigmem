from __future__ import annotations

import importlib
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import stigmem_node.plugins.discovery as discovery
from stigmem_node.auth import Identity
from stigmem_node.plugins import (
    ENTRY_POINT_GROUP,
    Allow,
    HookRegistry,
    PluginHealthStatus,
    PluginManifest,
    TenantContext,
    discover_plugin_manifests,
)

_FEATURE_DIR = Path(__file__).resolve().parents[3] / "experimental" / "multi-tenant"
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_multi_tenant")
MultiTenantConfig = _PLUGIN.MultiTenantConfig
PLUGIN_NAME = _PLUGIN.PLUGIN_NAME
plugin_manifest = _PLUGIN.plugin_manifest


@dataclass(frozen=True)
class _Dist:
    metadata: dict[str, str]


@dataclass(frozen=True)
class _EntryPoint:
    name: str
    value: str
    loaded: Any
    group: str = ENTRY_POINT_GROUP
    dist: _Dist | None = None

    def load(self) -> Any:
        return self.loaded


class _EntryPointSet(list[_EntryPoint]):
    def select(self, *, group: str) -> _EntryPointSet:
        return _EntryPointSet([entry_point for entry_point in self if entry_point.group == group])


def test_pyproject_declares_stigmem_plugin_entry_point() -> None:
    data = tomllib.loads((_FEATURE_DIR / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == PLUGIN_NAME
    assert (
        data["project"]["entry-points"]["stigmem.plugins"]["multi-tenant"]
        == "stigmem_plugin_multi_tenant:plugin_manifest"
    )


def test_manifest_declares_expected_boundary() -> None:
    manifest = plugin_manifest()

    assert isinstance(manifest, PluginManifest)
    assert manifest.name == PLUGIN_NAME
    assert manifest.version == "0.1.0"
    assert manifest.requires_stigmem == ">=0.9.0a3"
    assert manifest.config_schema is MultiTenantConfig
    assert manifest.capabilities == frozenset(
        {
            "facts.read",
            "facts.write",
            "recall.read",
            "federation.read",
            "federation.write",
            "identity.read",
            "tenant.read",
            "tenant.write",
            "audit.emit",
            "config.read",
        }
    )
    assert set(manifest.hooks) == {
        "config_validate",
        "tenant_resolve",
        "pre_assert_authorize",
        "pre_recall_authorize",
        "recall_filter",
        "federation_outbound_filter",
        "migration_register",
    }
    assert manifest.health_check is not None
    assert manifest.async_safe is True


def test_tenant_resolve_preserves_default_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STIGMEM_MULTI_TENANT_ENABLED", raising=False)
    manifest = plugin_manifest()
    registry = HookRegistry()
    registry.register_plugin(manifest)

    identity = Identity("agent:alice", ["read"], tenant_id="tenant-a")
    tenant = registry.fire_filter_chain(
        "tenant_resolve",
        TenantContext(tenant_id="default", metadata={"source_tenant_id": "tenant-a"}),
        identity=identity,
    )

    assert tenant.tenant_id == "default"


def test_tenant_resolve_uses_identity_tenant_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    manifest = plugin_manifest()
    registry = HookRegistry()
    registry.register_plugin(manifest)

    identity = Identity("agent:alice", ["read"], tenant_id="tenant-a")
    tenant = registry.fire_filter_chain(
        "tenant_resolve",
        TenantContext(tenant_id="default", metadata={"source_tenant_id": "tenant-a"}),
        identity=identity,
    )

    assert tenant.tenant_id == "tenant-a"
    assert tenant.metadata["resolved_by"] == PLUGIN_NAME


def test_tenant_resolve_falls_back_to_source_tenant_metadata_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    manifest = plugin_manifest()
    registry = HookRegistry()
    registry.register_plugin(manifest)

    tenant = registry.fire_filter_chain(
        "tenant_resolve",
        TenantContext(tenant_id="default", metadata={"source_tenant_id": "tenant-from-key"}),
        identity=object(),
    )

    assert tenant.tenant_id == "tenant-from-key"
    assert tenant.metadata["resolved_by"] == PLUGIN_NAME


def test_authorization_hooks_return_allow_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    manifest = plugin_manifest()
    registry = HookRegistry()
    registry.register_plugin(manifest)

    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    assert isinstance(registry.fire_voting("pre_recall_authorize"), Allow)


def test_pass_through_filter_hooks_preserve_payload_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    manifest = plugin_manifest()
    registry = HookRegistry()
    registry.register_plugin(manifest)

    recall_payload = [{"fact_id": "f1"}]
    federation_payload = {"facts": [{"id": "f1"}]}
    migrations_payload = ("core-migration",)

    assert registry.fire_filter_chain("recall_filter", recall_payload) is recall_payload
    assert (
        registry.fire_filter_chain("federation_outbound_filter", federation_payload)
        is federation_payload
    )
    assert (
        registry.fire_filter_chain("migration_register", migrations_payload)
        is migrations_payload
    )


def test_health_check_reports_healthy() -> None:
    manifest = plugin_manifest()
    assert manifest.health_check is not None
    registry = HookRegistry()
    registry.register_plugin(manifest)

    reports = {report.plugin_name: report for report in registry.poll_plugin_health()}
    report = reports[PLUGIN_NAME]

    assert report.status is PluginHealthStatus.HEALTHY
    assert "multi-tenant" in report.message


def test_discovery_loads_multi_tenant_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda: _EntryPointSet(
            [
                _EntryPoint(
                    name="multi-tenant",
                    value="stigmem_plugin_multi_tenant:plugin_manifest",
                    loaded=plugin_manifest,
                    dist=_Dist(metadata={"Name": PLUGIN_NAME}),
                )
            ]
        ),
    )

    discovered = discover_plugin_manifests()

    assert len(discovered) == 1
    assert discovered[0].manifest.name == PLUGIN_NAME
    assert discovered[0].entry_point_value == "stigmem_plugin_multi_tenant:plugin_manifest"
