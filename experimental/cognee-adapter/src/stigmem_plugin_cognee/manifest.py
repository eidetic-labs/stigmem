"""Plugin manifest factory for the Cognee adapter."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

PLUGIN_NAME = "stigmem-plugin-cognee-adapter"
PLUGIN_VERSION = "0.1.0"
REQUIRES_STIGMEM = ">=0.9.0a10"


def plugin_manifest() -> PluginManifest:
    """Return the entry-point manifest consumed by ``stigmem.plugins`` discovery."""

    return PluginManifest(
        name=PLUGIN_NAME,
        version=PLUGIN_VERSION,
        requires_stigmem=REQUIRES_STIGMEM,
        capabilities=frozenset({"facts.read", "facts.write", "network.outbound"}),
        async_safe=True,
    )
