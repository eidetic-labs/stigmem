from __future__ import annotations

import importlib
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import stigmem_node.plugins.discovery as discovery
from stigmem_node.plugins import (
    ENTRY_POINT_GROUP,
    Allow,
    HookRegistry,
    PluginHealthStatus,
    PluginManifest,
    discover_plugin_manifests,
)

_FEATURE_DIR = Path(__file__).resolve().parents[3] / "experimental" / "time-travel"
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_time_travel")
TimeTravelConfig = _PLUGIN.TimeTravelConfig
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
        data["project"]["entry-points"]["stigmem.plugins"]["time-travel"]
        == "stigmem_plugin_time_travel:plugin_manifest"
    )


def test_manifest_declares_expected_boundary() -> None:
    manifest = plugin_manifest()

    assert isinstance(manifest, PluginManifest)
    assert manifest.name == PLUGIN_NAME
    assert manifest.version == "0.1.0"
    assert manifest.requires_stigmem == ">=0.9.0a1"
    assert manifest.config_schema is TimeTravelConfig
    assert manifest.capabilities == frozenset(
        {
            "facts.read",
            "recall.read",
            "config.read",
            "audit.emit",
        }
    )
    assert set(manifest.hooks) == {
        "pre_recall_authorize",
        "pre_recall_rewrite",
        "post_recall_audit",
    }
    assert manifest.routes == ()


def test_default_config_keeps_behavior_disabled() -> None:
    config = TimeTravelConfig()

    assert config.enabled is False
    assert config.allow_fact_query_as_of is False
    assert config.allow_recall_as_of is False
    assert config.retention_floor is None


def test_config_loads_environment_gates() -> None:
    config = _PLUGIN.config.load_config_from_env(
        {
            "STIGMEM_TIME_TRAVEL_ENABLED": "true",
            "STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF": "1",
            "STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF": "yes",
            "STIGMEM_TIME_TRAVEL_RETENTION_FLOOR": "2026-05-01T00:00:00Z",
        }
    )

    assert config.enabled is True
    assert config.allow_fact_query_as_of is True
    assert config.allow_recall_as_of is True
    assert config.retention_floor == "2026-05-01T00:00:00+00:00"


def test_manifest_registers_with_hook_registry() -> None:
    registry = HookRegistry()
    manifest = plugin_manifest()

    registry.register_plugin(manifest)

    assert PLUGIN_NAME in registry.registered_plugins()
    assert isinstance(registry.fire_voting("pre_recall_authorize"), Allow)
    decision = registry.fire_voting(
        "pre_recall_authorize",
        query={"query": "alice", "as_of": "2026-05-01T00:00:00Z"},
    )
    assert isinstance(decision, Allow)
    assert registry.fire_filter_chain("pre_recall_rewrite", {"query": "hello"}) == {
        "query": "hello"
    }
    registry.fire_fire_and_forget("post_recall_audit")
    reports = {report.plugin_name: report for report in registry.poll_plugin_health()}
    report = reports[PLUGIN_NAME]
    assert report.status == PluginHealthStatus.HEALTHY
    assert "plugin scaffold registered" in report.message


def test_entry_point_factory_is_discoverable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda: _EntryPointSet(
            [
                _EntryPoint(
                    name="time-travel",
                    value="stigmem_plugin_time_travel:plugin_manifest",
                    loaded=plugin_manifest,
                    dist=_Dist({"Name": PLUGIN_NAME}),
                )
            ]
        ),
    )

    discovered = discover_plugin_manifests()

    assert len(discovered) == 1
    assert discovered[0].manifest.name == PLUGIN_NAME
    assert discovered[0].entry_point_name == "time-travel"
    assert discovered[0].entry_point_value == "stigmem_plugin_time_travel:plugin_manifest"
    assert discovered[0].distribution == PLUGIN_NAME
