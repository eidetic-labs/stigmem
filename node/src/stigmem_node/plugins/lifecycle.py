"""Installed plugin registration lifecycle."""

from __future__ import annotations

import logging

from stigmem_node.settings import settings

from .discovery import DiscoveredPlugin, discover_plugin_manifests, resolve_plugin_dependencies
from .registry import HookRegistry, get_registry
from .signing import PluginSignatureVerifier, require_verified_signature

logger = logging.getLogger("stigmem.plugins.lifecycle")


def register_discovered_plugins(
    *,
    registry: HookRegistry | None = None,
    freeze: bool = True,
    signing_required: bool | None = None,
    signature_verifier: PluginSignatureVerifier = require_verified_signature,
) -> tuple[DiscoveredPlugin, ...]:
    """Discover, dependency-order, and register installed plugin packages.

    This function is intentionally startup-only. It mutates the supplied registry
    during application initialization and freezes it by default so later runtime
    hot unload/reload paths are not introduced by PR 4-INF.2.
    """

    target = registry or get_registry()
    require_signatures = (
        settings.plugin_signing_required if signing_required is None else signing_required
    )
    discovered = discover_plugin_manifests()
    ordered = resolve_plugin_dependencies(
        discovered,
        registered_plugins=target.registered_plugins(),
    )
    for plugin in ordered:
        signing_identity = "unsigned"
        signing_metadata = None
        if require_signatures:
            signing_info = signature_verifier(plugin)
            signing_identity = signing_info.signing_identity
            signing_metadata = signing_info.audit_metadata()
        target.register_plugin(
            plugin.manifest,
            discovery_source=_discovery_source(plugin),
            signing_identity=signing_identity,
            signing_metadata=signing_metadata,
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
