from __future__ import annotations

from collections.abc import Callable

import pytest

import stigmem_node.plugins.lifecycle as lifecycle
from stigmem_node.plugins import (
    Allow,
    AuditEvent,
    CapabilityError,
    CoreApis,
    DiscoveredPlugin,
    HookRegistry,
    ManifestError,
    PluginContext,
    PluginManifest,
    PluginSignatureError,
    PluginSigningInfo,
    RegistryFrozenError,
)


def _manifest(
    name: str,
    hooks: dict[str, Callable[..., object]],
    *,
    capabilities: frozenset[str] = frozenset(),
    depends_on: frozenset[str] = frozenset(),
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        capabilities=capabilities,
        depends_on=depends_on,
        hooks=hooks,
    )


def _discovered(manifest: PluginManifest) -> DiscoveredPlugin:
    return DiscoveredPlugin(
        manifest=manifest,
        entry_point_name=manifest.name,
        entry_point_value=f"{manifest.name}:plugin_manifest",
        distribution=f"{manifest.name}-dist",
    )


def _signed_discovered(manifest: PluginManifest, signing_identity: str) -> DiscoveredPlugin:
    return DiscoveredPlugin(
        manifest=manifest,
        entry_point_name=manifest.name,
        entry_point_value=f"{manifest.name}:plugin_manifest",
        distribution=f"{manifest.name}-dist",
        signing_identity=signing_identity,
        signature_verified=True,
    )


def test_register_discovered_plugins_orders_registers_and_freezes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def base_handler(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("base")
        return Allow()

    def addon_handler(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("addon")
        return Allow()

    base = _manifest("base-plugin", {"pre_assert_authorize": base_handler})
    addon = _manifest(
        "addon-plugin",
        {"pre_assert_authorize": addon_handler},
        depends_on=frozenset({"base-plugin"}),
    )
    registry = HookRegistry()
    monkeypatch.setattr(
        lifecycle,
        "discover_plugin_manifests",
        lambda: (_discovered(addon), _discovered(base)),
    )

    registered = lifecycle.register_discovered_plugins(registry=registry)

    assert [plugin.manifest.name for plugin in registered] == ["base-plugin", "addon-plugin"]
    assert registry.registered_plugins() == frozenset({"base-plugin", "addon-plugin"})
    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    assert sorted(calls) == ["addon", "base"]
    with pytest.raises(RegistryFrozenError):
        registry.register_plugin(_manifest("late-plugin", {}))
    with pytest.raises(RegistryFrozenError):
        registry.register_core_handler(
            "pre_assert_authorize",
            base_handler,
            name="core.999.late",
        )


def test_register_discovered_plugins_emits_discovery_audit_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    manifest = _manifest(
        "audited-plugin",
        {"pre_assert_authorize": handler},
        capabilities=frozenset({"audit.emit", "facts.read"}),
    )
    registry = HookRegistry()
    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    lifecycle.register_discovered_plugins(registry=registry, freeze=False)

    assert [event.event_type for event in events] == ["plugin.registered"]
    metadata = events[0].metadata
    assert metadata["plugin_name"] == "audited-plugin"
    assert metadata["version"] == "1.0.0"
    assert metadata["capabilities"] == ["audit.emit", "facts.read"]
    assert metadata["hooks"] == ["pre_assert_authorize"]
    assert metadata["signed_by"] == "unsigned"
    assert metadata["discovery_source"] == {
        "type": "python_entry_point",
        "entry_point_name": "audited-plugin",
        "entry_point_value": "audited-plugin:plugin_manifest",
        "distribution": "audited-plugin-dist",
    }


def test_register_discovered_plugins_preserves_capability_gated_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_emitter = object()
    captured_contexts: list[PluginContext] = []

    def handler(ctx: PluginContext, **_: object) -> Allow:
        captured_contexts.append(ctx)
        return Allow()

    manifest = _manifest(
        "audit-plugin",
        {"pre_assert_authorize": handler},
        capabilities=frozenset({"audit.emit"}),
    )
    registry = HookRegistry(core_apis=CoreApis(audit_emitter=audit_emitter))
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    lifecycle.register_discovered_plugins(registry=registry, freeze=False)

    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    ctx = captured_contexts[0]
    assert ctx.plugin_name == "audit-plugin"
    assert ctx.get_audit_emitter() is audit_emitter
    with pytest.raises(CapabilityError):
        ctx.get_facts_reader()


def test_register_discovered_plugins_rejects_unsigned_plugin_when_signing_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("unsigned-plugin", {})
    registry = HookRegistry()
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    with pytest.raises(PluginSignatureError, match="production plugin registration requires"):
        lifecycle.register_discovered_plugins(registry=registry, signing_required=True)

    assert registry.registered_plugins() == frozenset()


def test_register_discovered_plugins_records_verified_signing_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    manifest = _manifest("signed-plugin", {})
    discovered = _signed_discovered(manifest, "issuer@example.com")
    registry = HookRegistry()
    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (discovered,))

    def verifier(plugin: DiscoveredPlugin) -> PluginSigningInfo:
        assert plugin is discovered
        return PluginSigningInfo(signing_identity=plugin.signing_identity)

    lifecycle.register_discovered_plugins(
        registry=registry,
        freeze=False,
        signing_required=True,
        signature_verifier=verifier,
    )

    info = registry.plugin_info("signed-plugin")
    assert info is not None
    assert info.signed_by == "issuer@example.com"
    assert events[0].metadata["signed_by"] == "issuer@example.com"


def test_register_discovered_plugins_fails_closed_on_duplicate_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest("dupe-plugin", {})
    registry = HookRegistry()
    registry.register_plugin(manifest)
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    with pytest.raises(ManifestError, match="already registered"):
        lifecycle.register_discovered_plugins(registry=registry)


def test_register_discovered_plugins_emits_failure_audit_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    manifest = _manifest("dupe-audit-plugin", {})
    registry = HookRegistry()
    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    registry.register_plugin(manifest)
    events.clear()
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    with pytest.raises(ManifestError, match="already registered"):
        lifecycle.register_discovered_plugins(registry=registry)

    assert [event.event_type for event in events] == ["plugin.registration_failed"]
    metadata = events[0].metadata
    assert metadata["plugin_name"] == "dupe-audit-plugin"
    assert metadata["reason"] == "duplicate"
    assert metadata["signed_by"] == "unsigned"
    assert metadata["discovery_source"]["type"] == "python_entry_point"
    assert metadata["discovery_source"]["entry_point_name"] == "dupe-audit-plugin"


def test_register_discovered_plugins_fails_closed_on_registration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_handler() -> Allow:
        return Allow()

    manifest = _manifest("bad-plugin", {"pre_assert_authorize": invalid_handler})
    registry = HookRegistry()
    monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (_discovered(manifest),))

    with pytest.raises(ManifestError, match="must accept at least 1 positional argument"):
        lifecycle.register_discovered_plugins(registry=registry)

    assert registry.registered_plugins() == frozenset()
    registry.register_plugin(_manifest("good-plugin", {}))
