"""Installed plugin registration lifecycle."""

from __future__ import annotations

import logging

from .discovery import DiscoveredPlugin, discover_plugin_manifests, resolve_plugin_dependencies
from .registry import HookRegistry, get_registry

logger = logging.getLogger("stigmem.plugins.lifecycle")


def register_discovered_plugins(
    *,
    registry: HookRegistry | None = None,
    freeze: bool = True,
) -> tuple[DiscoveredPlugin, ...]:
    """Discover, dependency-order, and register installed plugin packages.

    This function is intentionally startup-only. It mutates the supplied registry
    during application initialization and freezes it by default so later runtime
    hot unload/reload paths are not introduced by PR 4-INF.2.
    """

    target = registry or get_registry()
    discovered = discover_plugin_manifests()
    ordered = resolve_plugin_dependencies(
        discovered,
        registered_plugins=target.registered_plugins(),
    )
    for plugin in ordered:
        target.register_plugin(
            plugin.manifest,
            discovery_source=_discovery_source(plugin),
            signing_identity="unsigned",
        )
    if freeze:
        target.freeze()
    if ordered:
        logger.info(
            "registered installed plugins: %s",
            ", ".join(plugin.manifest.name for plugin in ordered),
        )
    return ordered


def _discovery_source(plugin: DiscoveredPlugin) -> dict[str, str | None]:
    return {
        "type": "python_entry_point",
        "entry_point_name": plugin.entry_point_name,
        "entry_point_value": plugin.entry_point_value,
        "distribution": plugin.distribution,
    }
