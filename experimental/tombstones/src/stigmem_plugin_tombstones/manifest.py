"""Plugin manifest factory for RTBF tombstones."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import TombstoneConfig, load_config_from_env

PLUGIN_NAME = "stigmem-plugin-tombstones"
PLUGIN_VERSION = "0.1.0"
REQUIRES_STIGMEM = ">=0.9.0a2"


def plugin_manifest() -> PluginManifest:
    """Return the entry-point manifest consumed by ``stigmem.plugins`` discovery."""
    config = load_config_from_env()

    return PluginManifest(
        name=PLUGIN_NAME,
        version=PLUGIN_VERSION,
        requires_stigmem=REQUIRES_STIGMEM,
        capabilities=frozenset(
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
        ),
        hooks={
            "recall_filter": handlers.recall_filter,
            "federation_inbound_validate": handlers.federation_inbound_validate,
            "post_assert_propagate": handlers.post_assert_propagate,
            "migration_register": handlers.migration_register,
        },
        routes=_routes_for(config),
        config_schema=TombstoneConfig,
        health_check=handlers.health_check,
        async_safe=True,
    )


def _routes_for(config: TombstoneConfig) -> tuple[object, ...]:
    if not config.enabled:
        return ()

    routes: list[object] = []
    if config.allow_admin_routes:
        from stigmem_node.routes.tombstones import router as admin_router

        routes.append(admin_router)
    if config.allow_federation_routes:
        from stigmem_node.routes.federation.tombstones import router as federation_router

        routes.append(federation_router)
    return tuple(routes)
