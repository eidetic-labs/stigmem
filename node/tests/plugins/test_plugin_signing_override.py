"""Plugin signing override tests."""

from __future__ import annotations

import pytest

from stigmem_node.plugins.discovery import DiscoveredPlugin
from stigmem_node.plugins.manifest import PluginManifest
from stigmem_node.plugins.signing import allow_unsigned_development_override
from stigmem_node.settings import Settings


def _plugin() -> DiscoveredPlugin:
    return DiscoveredPlugin(
        manifest=PluginManifest(name="dev-plugin", version="0.1.0"),
        entry_point_name="dev_plugin",
        entry_point_value="dev_plugin:manifest",
    )


def test_unsigned_override_requires_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    import stigmem_node.settings as settings_mod

    test_settings = Settings(plugin_signing_required=False, plugin_unsigned_ack="")
    monkeypatch.setattr(settings_mod, "settings", test_settings)

    with pytest.raises(RuntimeError, match="STIGMEM_PLUGIN_UNSIGNED_ACK"):
        allow_unsigned_development_override(_plugin())


def test_unsigned_override_rejects_wrong_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    import stigmem_node.settings as settings_mod

    test_settings = Settings(plugin_signing_required=False, plugin_unsigned_ack="yes")
    monkeypatch.setattr(settings_mod, "settings", test_settings)

    with pytest.raises(RuntimeError, match="STIGMEM_PLUGIN_UNSIGNED_ACK"):
        allow_unsigned_development_override(_plugin())


def test_unsigned_override_allows_exact_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    import stigmem_node.settings as settings_mod

    test_settings = Settings(
        plugin_signing_required=False,
        plugin_unsigned_ack="i-understand-plugins-are-unsigned",
    )
    monkeypatch.setattr(settings_mod, "settings", test_settings)

    info = allow_unsigned_development_override(_plugin())

    assert info.trust_decision == "development_unsigned_override"
