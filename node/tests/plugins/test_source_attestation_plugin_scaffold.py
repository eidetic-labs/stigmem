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
from stigmem_node.plugins import (
    ENTRY_POINT_GROUP,
    Allow,
    HookRegistry,
    PluginContext,
    PluginHealthStatus,
    PluginManifest,
    discover_plugin_manifests,
)

_FEATURE_DIR = Path(__file__).resolve().parents[3] / "experimental" / "source-attestation"
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_source_attestation")
SourceAttestationConfig = _PLUGIN.SourceAttestationConfig
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
        data["project"]["entry-points"]["stigmem.plugins"]["source-attestation"]
        == "stigmem_plugin_source_attestation:plugin_manifest"
    )


def test_manifest_declares_expected_boundary() -> None:
    manifest = plugin_manifest()

    assert isinstance(manifest, PluginManifest)
    assert manifest.name == PLUGIN_NAME
    assert manifest.version == "0.1.0"
    assert manifest.requires_stigmem == ">=0.9.0a1"
    assert manifest.config_schema is SourceAttestationConfig
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
        }
    )
    assert set(manifest.hooks) == {
        "pre_assert_validate",
        "recall_rank",
        "federation_inbound_validate",
    }
    assert manifest.routes == ()


def test_default_config_keeps_behavior_disabled() -> None:
    config = SourceAttestationConfig()

    assert config.enabled is False
    assert config.enforce_assert_validation is False
    assert config.apply_recall_rank is False
    assert config.enforce_federation_inbound is False
    assert config.warn_only is True


def test_config_loads_environment_gates() -> None:
    config = _PLUGIN.config.load_config_from_env(
        {
            "STIGMEM_SOURCE_ATTESTATION_ENABLED": "true",
            "STIGMEM_SOURCE_ATTESTATION_ENFORCE_ASSERT_VALIDATION": "1",
            "STIGMEM_SOURCE_ATTESTATION_APPLY_RECALL_RANK": "yes",
            "STIGMEM_SOURCE_ATTESTATION_ENFORCE_FEDERATION_INBOUND": "on",
            "STIGMEM_SOURCE_ATTESTATION_WARN_ONLY": "false",
        }
    )

    assert config.enabled is True
    assert config.enforce_assert_validation is True
    assert config.apply_recall_rank is True
    assert config.enforce_federation_inbound is True
    assert config.warn_only is False


def test_config_rejects_warn_only_with_enforcement() -> None:
    with pytest.raises(ValueError, match="warn_only must be false"):
        SourceAttestationConfig(enforce_assert_validation=True, warn_only=True)
    with pytest.raises(ValueError, match="warn_only must be false"):
        SourceAttestationConfig(enforce_federation_inbound=True, warn_only=True)


def test_manifest_registers_with_hook_registry() -> None:
    registry = HookRegistry()
    manifest = plugin_manifest()

    registry.register_plugin(manifest)

    assert PLUGIN_NAME in registry.registered_plugins()
    assert isinstance(registry.fire_voting("pre_assert_validate"), Allow)
    assert registry.fire_score_delta("recall_rank", [{"id": "fact"}]) == {}
    assert isinstance(registry.fire_voting("federation_inbound_validate"), Allow)
    reports = {report.plugin_name: report for report in registry.poll_plugin_health()}
    report = reports[PLUGIN_NAME]
    assert report.status == PluginHealthStatus.HEALTHY
    assert "plugin scaffold registered" in report.message


def test_source_attestation_plugin_hook_order_is_deterministic() -> None:
    calls: list[str] = []
    manifest = _recording_manifest(calls)
    registry = HookRegistry()

    def core_assert_validate(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core:pre_assert_validate")
        return Allow()

    def core_recall_rank(
        _ctx: PluginContext,
        _scored_results: list[object],
        **_: object,
    ) -> dict[str, float]:
        calls.append("core:recall_rank")
        return {}

    def core_inbound_validate(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core:federation_inbound_validate")
        return Allow()

    registry.register_core_handler(
        "pre_assert_validate",
        core_assert_validate,
        name="core.001.assert-validate",
    )
    registry.register_core_handler("recall_rank", core_recall_rank, name="core.001.rank")
    registry.register_core_handler(
        "federation_inbound_validate",
        core_inbound_validate,
        name="core.001.validate",
    )
    registry.register_plugin(manifest)

    assert _handler_names(registry, "pre_assert_validate") == (
        "core.001.assert-validate",
        f"{PLUGIN_NAME}.pre_assert_validate",
    )
    assert _handler_names(registry, "recall_rank") == (
        f"{PLUGIN_NAME}.recall_rank",
        "core.001.rank",
    )
    assert _handler_names(registry, "federation_inbound_validate") == (
        "core.001.validate",
        f"{PLUGIN_NAME}.federation_inbound_validate",
    )

    registry.fire_voting("pre_assert_validate")
    registry.fire_score_delta("recall_rank", [{"id": "fact-1"}])
    registry.fire_voting("federation_inbound_validate")

    assert calls == [
        "core:pre_assert_validate",
        "plugin:pre_assert_validate",
        "plugin:recall_rank",
        "core:recall_rank",
        "core:federation_inbound_validate",
        "plugin:federation_inbound_validate",
    ]


def test_entry_point_factory_is_discoverable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda: _EntryPointSet(
            [
                _EntryPoint(
                    name="source-attestation",
                    value="stigmem_plugin_source_attestation:plugin_manifest",
                    loaded=plugin_manifest,
                    dist=_Dist({"Name": PLUGIN_NAME}),
                )
            ]
        ),
    )

    discovered = discover_plugin_manifests()

    assert len(discovered) == 1
    assert discovered[0].manifest.name == PLUGIN_NAME
    assert discovered[0].entry_point_name == "source-attestation"
    assert discovered[0].entry_point_value == "stigmem_plugin_source_attestation:plugin_manifest"
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
