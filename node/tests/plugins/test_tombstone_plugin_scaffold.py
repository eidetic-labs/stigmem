from __future__ import annotations

import importlib
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import pytest

import stigmem_node.plugins.discovery as discovery
from stigmem_node.lifecycle.tombstone_gate import tombstone_filter_enabled
from stigmem_node.plugins import (
    ENTRY_POINT_GROUP,
    Allow,
    HookRegistry,
    PluginContext,
    PluginHealthStatus,
    PluginManifest,
    discover_plugin_manifests,
)
from stigmem_node.plugins.testing import stigmem_plugins

_FEATURE_DIR = Path(__file__).resolve().parents[3] / "experimental" / "tombstones"
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_tombstones")
TombstoneConfig = _PLUGIN.TombstoneConfig
PLUGIN_NAME = _PLUGIN.PLUGIN_NAME
plugin_manifest = _PLUGIN.plugin_manifest
T = TypeVar("T")


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
        data["project"]["entry-points"]["stigmem.plugins"]["tombstones"]
        == "stigmem_plugin_tombstones:plugin_manifest"
    )


def test_manifest_declares_expected_boundary() -> None:
    data = tomllib.loads((_FEATURE_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = plugin_manifest()

    assert isinstance(manifest, PluginManifest)
    assert manifest.name == PLUGIN_NAME
    assert manifest.version == data["project"]["version"]
    assert manifest.requires_stigmem == ">=0.9.0a3"
    assert manifest.config_schema is TombstoneConfig
    assert manifest.capabilities == frozenset(
        {
            "facts.read",
            "facts.write",
            "recall.read",
            "federation.read",
            "federation.write",
            "identity.read",
            "audit.emit",
            "config.read",
            "network.outbound",
        }
    )
    assert set(manifest.hooks) == {
        "recall_filter",
        "federation_inbound_validate",
        "post_assert_propagate",
        "migration_register",
    }
    assert manifest.routes == ()


def test_manifest_exposes_legacy_routes_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ALLOW_ADMIN_ROUTES", "true")
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ALLOW_FEDERATION_ROUTES", "true")

    manifest = plugin_manifest()

    route_paths = {
        route.path
        for router in manifest.routes
        for route in getattr(router, "routes", ())
        if hasattr(route, "path")
    }
    assert "/v1/tombstones" in route_paths
    assert "/v1/federation/tombstones" in route_paths
    assert "/v1/federation/tombstones/ingest" in route_paths


def test_manifest_keeps_routes_absent_when_route_gates_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ENABLED", "true")
    monkeypatch.delenv("STIGMEM_TOMBSTONES_ALLOW_ADMIN_ROUTES", raising=False)
    monkeypatch.delenv("STIGMEM_TOMBSTONES_ALLOW_FEDERATION_ROUTES", raising=False)

    manifest = plugin_manifest()

    assert manifest.routes == ()


def test_default_config_keeps_behavior_disabled() -> None:
    config = TombstoneConfig()

    assert config.enabled is False
    assert config.allow_admin_routes is False
    assert config.allow_federation_routes is False
    assert config.allow_recall_filter is False
    assert config.propagate_to_peers is False
    assert config.require_signed_inbound is True
    assert config.cache_ttl_seconds == 60


def test_runtime_filter_gate_requires_plugin_and_operator_enablement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = plugin_manifest()

    monkeypatch.delenv("STIGMEM_TOMBSTONES_ENABLED", raising=False)
    monkeypatch.delenv("STIGMEM_TOMBSTONES_ALLOW_RECALL_FILTER", raising=False)
    assert tombstone_filter_enabled() is False

    with stigmem_plugins([manifest]):
        assert tombstone_filter_enabled() is False
        assert (
            tombstone_filter_enabled(
                {
                    "STIGMEM_TOMBSTONES_ENABLED": "true",
                    "STIGMEM_TOMBSTONES_ALLOW_RECALL_FILTER": "false",
                }
            )
            is False
        )
        assert (
            tombstone_filter_enabled(
                {
                    "STIGMEM_TOMBSTONES_ENABLED": "true",
                    "STIGMEM_TOMBSTONES_ALLOW_RECALL_FILTER": "true",
                }
            )
            is True
        )


def test_config_loads_environment_gates() -> None:
    config = _PLUGIN.config.load_config_from_env(
        {
            "STIGMEM_TOMBSTONES_ENABLED": "true",
            "STIGMEM_TOMBSTONES_ALLOW_ADMIN_ROUTES": "1",
            "STIGMEM_TOMBSTONES_ALLOW_FEDERATION_ROUTES": "yes",
            "STIGMEM_TOMBSTONES_ALLOW_RECALL_FILTER": "on",
            "STIGMEM_TOMBSTONES_PROPAGATE_TO_PEERS": "true",
            "STIGMEM_TOMBSTONES_REQUIRE_SIGNED_INBOUND": "false",
            "STIGMEM_TOMBSTONES_CACHE_TTL_SECONDS": "30",
        }
    )

    assert config.enabled is True
    assert config.allow_admin_routes is True
    assert config.allow_federation_routes is True
    assert config.allow_recall_filter is True
    assert config.propagate_to_peers is True
    assert config.require_signed_inbound is False
    assert config.cache_ttl_seconds == 30


def test_config_requires_federation_routes_for_propagation() -> None:
    with pytest.raises(ValueError, match="propagate_to_peers requires allow_federation_routes"):
        TombstoneConfig(propagate_to_peers=True)


def test_manifest_registers_with_hook_registry() -> None:
    registry = HookRegistry()
    manifest = plugin_manifest()

    registry.register_plugin(manifest)

    assert PLUGIN_NAME in registry.registered_plugins()
    assert registry.fire_filter_chain("recall_filter", ["fact"]) == ["fact"]
    assert isinstance(registry.fire_voting("federation_inbound_validate"), Allow)
    registry.fire_fire_and_forget("post_assert_propagate")
    migrations = registry.fire_filter_chain("migration_register", [])
    assert len(migrations) == 1
    assert migrations[0].plugin_name == PLUGIN_NAME
    assert migrations[0].migration_id == 1
    assert "CREATE TABLE IF NOT EXISTS tombstones" in migrations[0].sql
    assert "CREATE TABLE IF NOT EXISTS tombstone_revocations" in migrations[0].sql
    assert "fact_retractions" not in migrations[0].sql
    reports = {report.plugin_name: report for report in registry.poll_plugin_health()}
    report = reports[PLUGIN_NAME]
    assert report.status == PluginHealthStatus.HEALTHY
    assert "plugin scaffold registered" in report.message


def test_tombstone_plugin_hook_order_is_deterministic() -> None:
    calls: list[str] = []
    manifest = _recording_manifest(calls)
    registry = HookRegistry()

    def core_recall_filter(_ctx: PluginContext, value: list[str], **_: object) -> list[str]:
        calls.append("core:recall_filter")
        return value

    def core_inbound_validate(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core:federation_inbound_validate")
        return Allow()

    def core_post_assert_propagate(_ctx: PluginContext, **_: object) -> None:
        calls.append("core:post_assert_propagate")

    def core_migration(_ctx: PluginContext, value: list[object], **_: object) -> list[object]:
        calls.append("core:migration_register")
        return value

    registry.register_core_handler("recall_filter", core_recall_filter, name="core.001.filter")
    registry.register_core_handler(
        "federation_inbound_validate",
        core_inbound_validate,
        name="core.001.validate",
    )
    registry.register_core_handler(
        "post_assert_propagate",
        core_post_assert_propagate,
        name="core.001.propagate",
    )
    registry.register_core_handler(
        "migration_register",
        core_migration,
        name="core.001.migration",
    )
    registry.register_plugin(manifest)

    assert _handler_names(registry, "recall_filter") == (
        f"{PLUGIN_NAME}.recall_filter",
        "core.001.filter",
    )
    assert _handler_names(registry, "federation_inbound_validate") == (
        "core.001.validate",
        f"{PLUGIN_NAME}.federation_inbound_validate",
    )
    assert _handler_names(registry, "post_assert_propagate") == (
        "core.001.propagate",
        f"{PLUGIN_NAME}.post_assert_propagate",
    )
    assert _handler_names(registry, "migration_register") == (
        "core.001.migration",
        f"{PLUGIN_NAME}.migration_register",
    )

    registry.fire_filter_chain("recall_filter", ["fact-1"])
    registry.fire_voting("federation_inbound_validate")
    registry.fire_fire_and_forget("post_assert_propagate")
    registry.fire_filter_chain("migration_register", [])

    assert calls == [
        "plugin:recall_filter",
        "core:recall_filter",
        "core:federation_inbound_validate",
        "plugin:federation_inbound_validate",
        "core:post_assert_propagate",
        "plugin:post_assert_propagate",
        "core:migration_register",
        "plugin:migration_register",
    ]


def test_entry_point_factory_is_discoverable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda: _EntryPointSet(
            [
                _EntryPoint(
                    name="tombstones",
                    value="stigmem_plugin_tombstones:plugin_manifest",
                    loaded=plugin_manifest,
                    dist=_Dist({"Name": PLUGIN_NAME}),
                )
            ]
        ),
    )

    discovered = discover_plugin_manifests()

    assert len(discovered) == 1
    assert discovered[0].manifest.name == PLUGIN_NAME
    assert discovered[0].entry_point_name == "tombstones"
    assert discovered[0].entry_point_value == "stigmem_plugin_tombstones:plugin_manifest"
    assert discovered[0].distribution == PLUGIN_NAME


def _recording_manifest(calls: list[str]) -> PluginManifest:
    manifest = plugin_manifest()
    hooks: dict[str, Callable[..., Any]] = {}
    for hook_name, handler in manifest.hooks.items():
        hooks[hook_name] = _recording_handler(hook_name, handler, calls)
    return manifest.model_copy(update={"hooks": hooks})


def _recording_handler(
    hook_name: str,
    handler: Callable[..., T],
    calls: list[str],
) -> Callable[..., T]:
    def wrapper(ctx: PluginContext, *args: object, **kwargs: object) -> T:
        calls.append(f"plugin:{hook_name}")
        return handler(ctx, *args, **kwargs)

    wrapper.__name__ = handler.__name__
    return wrapper


def _handler_names(registry: HookRegistry, hook_name: str) -> tuple[str, ...]:
    return tuple(entry.handler_name for entry in registry.handlers_for(hook_name))
