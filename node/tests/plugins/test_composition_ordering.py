from __future__ import annotations

from collections.abc import Callable

import pytest

import stigmem_node.plugins.lifecycle as lifecycle
from stigmem_node.plugins import (
    Allow,
    DiscoveredPlugin,
    HookRegistry,
    PluginContext,
    PluginManifest,
)


def _manifest(
    name: str,
    hooks: dict[str, Callable[..., object]],
    *,
    depends_on: frozenset[str] = frozenset(),
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        hooks=hooks,
        depends_on=depends_on,
    )


def _discovered(manifest: PluginManifest) -> DiscoveredPlugin:
    return DiscoveredPlugin(
        manifest=manifest,
        entry_point_name=manifest.name,
        entry_point_value=f"{manifest.name}:plugin_manifest",
        distribution=f"{manifest.name}-dist",
    )


def _register_discovered(
    monkeypatch: pytest.MonkeyPatch,
    registry: HookRegistry,
    *manifests: PluginManifest,
) -> None:
    monkeypatch.setattr(
        lifecycle,
        "discover_plugin_manifests",
        lambda: tuple(_discovered(manifest) for manifest in manifests),
    )
    lifecycle.register_discovered_plugins(
        registry=registry,
        freeze=False,
        signing_required=False,
    )


def test_discovered_dependency_registration_order_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(_ctx: PluginContext, **_: object) -> None:
        return None

    manifests = (
        _manifest(
            "zeta-addon",
            {"post_assert_persist": handler},
            depends_on=frozenset({"base-plugin"}),
        ),
        _manifest("base-plugin", {"post_assert_persist": handler}),
        _manifest(
            "alpha-addon",
            {"post_assert_persist": handler},
            depends_on=frozenset({"base-plugin"}),
        ),
    )

    orders: list[tuple[str, ...]] = []
    for _ in range(3):
        registry = HookRegistry()
        _register_discovered(monkeypatch, registry, *manifests)
        orders.append(registry.plugin_registration_order())

    assert orders == [
        ("base-plugin", "alpha-addon", "zeta-addon"),
        ("base-plugin", "alpha-addon", "zeta-addon"),
        ("base-plugin", "alpha-addon", "zeta-addon"),
    ]


def test_discovered_core_first_hook_orders_core_handlers_before_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def core_010(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core-010")
        return Allow()

    def core_020(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core-020")
        return Allow()

    def plugin_aaa(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("aaa-plugin")
        return Allow()

    def plugin_zzz(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("zzz-plugin")
        return Allow()

    registry.register_core_handler(
        "pre_assert_authorize", core_020, name="core.020.second"
    )
    registry.register_core_handler(
        "pre_assert_authorize", core_010, name="core.010.first"
    )
    _register_discovered(
        monkeypatch,
        registry,
        _manifest("zzz-plugin", {"pre_assert_authorize": plugin_zzz}),
        _manifest("aaa-plugin", {"pre_assert_authorize": plugin_aaa}),
    )

    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    assert calls == ["core-010", "core-020", "aaa-plugin", "zzz-plugin"]


def test_discovered_plugins_first_hook_orders_plugins_before_core_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def core_010(_ctx: PluginContext, value: str, **_: object) -> str:
        calls.append("core-010")
        return value

    def core_020(_ctx: PluginContext, value: str, **_: object) -> str:
        calls.append("core-020")
        return value

    def plugin_aaa(_ctx: PluginContext, value: str, **_: object) -> str:
        calls.append("aaa-plugin")
        return value

    def plugin_zzz(_ctx: PluginContext, value: str, **_: object) -> str:
        calls.append("zzz-plugin")
        return value

    registry.register_core_handler(
        "pre_assert_transform", core_020, name="core.020.second"
    )
    registry.register_core_handler(
        "pre_assert_transform", core_010, name="core.010.first"
    )
    _register_discovered(
        monkeypatch,
        registry,
        _manifest("zzz-plugin", {"pre_assert_transform": plugin_zzz}),
        _manifest("aaa-plugin", {"pre_assert_transform": plugin_aaa}),
    )

    assert registry.fire_filter_chain("pre_assert_transform", "fact") == "fact"
    assert calls == ["aaa-plugin", "zzz-plugin", "core-010", "core-020"]
