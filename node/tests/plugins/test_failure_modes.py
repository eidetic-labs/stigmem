from __future__ import annotations

from collections.abc import Callable

import pytest

import stigmem_node.plugins.lifecycle as lifecycle
from stigmem_node.plugins import (
    Allow,
    CapabilityError,
    DiscoveredPlugin,
    HookRegistry,
    ManifestError,
    PluginContext,
    PluginDiscoveryError,
    PluginExecutionError,
    PluginHealth,
    PluginHealthStatus,
    PluginManifest,
)


def _manifest(
    name: str,
    hooks: dict[str, Callable[..., object]],
    *,
    capabilities: frozenset[str] = frozenset(),
    health_check: Callable[..., object] | None = None,
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        capabilities=capabilities,
        hooks=hooks,
        health_check=health_check,
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


def test_discovery_error_fails_closed_with_actionable_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def fail_discovery() -> tuple[DiscoveredPlugin, ...]:
        raise PluginDiscoveryError("failed to load plugin entry point 'bad-entry': boom")

    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", fail_discovery)

    with pytest.raises(PluginDiscoveryError, match="bad-entry.*boom"):
        lifecycle.register_discovered_plugins(registry=registry, signing_required=False)

    assert registry.registered_plugins() == frozenset()
    assert registry.plugin_registration_order() == ()
    assert registry.handlers_for("pre_assert_authorize") == ()


def test_discovered_registration_error_does_not_register_failed_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_handler() -> Allow:
        return Allow()

    registry = HookRegistry()
    manifest = _manifest("bad-plugin", {"pre_assert_authorize": invalid_handler})

    with pytest.raises(ManifestError, match="must accept at least 1 positional argument"):
        _register_discovered(monkeypatch, registry, manifest)

    assert registry.registered_plugins() == frozenset()
    assert registry.plugin_info("bad-plugin") is None
    assert registry.handlers_for("pre_assert_authorize") == ()


def test_discovered_capability_denial_fails_closed_at_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def handler(ctx: PluginContext, **_: object) -> Allow:
        ctx.get_facts_reader()
        return Allow()

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("reader-plugin", {"pre_assert_authorize": handler}),
    )

    with pytest.raises(
        PluginExecutionError, match="handler 'reader-plugin.handler' failed"
    ) as exc_info:
        registry.fire_voting("pre_assert_authorize")

    assert isinstance(exc_info.value.__cause__, CapabilityError)
    assert "facts.read" in str(exc_info.value.__cause__)
    assert registry.registered_plugins() == frozenset({"reader-plugin"})


def test_discovered_health_degradation_is_reported_without_disabling_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def health(_ctx: PluginContext) -> PluginHealth:
        return PluginHealth(PluginHealthStatus.DEGRADED, "remote dependency slow")

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("handler")
        return Allow()

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("degraded-plugin", {"pre_assert_authorize": handler}, health_check=health),
    )

    reports = registry.poll_plugin_health()

    assert len(reports) == 1
    assert reports[0].plugin_name == "degraded-plugin"
    assert reports[0].status == PluginHealthStatus.DEGRADED
    assert reports[0].message == "remote dependency slow"
    assert reports[0].error_summary is None
    assert registry.plugin_health_reports() == reports
    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    assert calls == ["handler"]
