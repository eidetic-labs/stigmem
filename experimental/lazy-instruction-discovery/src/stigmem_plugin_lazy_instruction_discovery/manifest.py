"""Plugin manifest factory for lazy instruction discovery."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import LazyInstructionDiscoveryConfig
from .routes import router

PLUGIN_NAME = "stigmem-plugin-lazy-instruction-discovery"
PLUGIN_VERSION = "0.9.0-alpha.3"
REQUIRES_STIGMEM = ">=0.9.0a3"


def plugin_manifest() -> PluginManifest:
    """Return the entry-point manifest consumed by ``stigmem.plugins`` discovery."""

    return PluginManifest(
        name=PLUGIN_NAME,
        version=PLUGIN_VERSION,
        requires_stigmem=REQUIRES_STIGMEM,
        capabilities=frozenset(
            {
                "facts.read",
                "facts.write",
                "recall.read",
                "audit.emit",
                "audit.read",
                "config.read",
            }
        ),
        hooks={
            "pre_recall_authorize": handlers.pre_recall_authorize,
            "pre_recall_rewrite": handlers.pre_recall_rewrite,
            "recall_filter": handlers.recall_filter,
            "post_recall_audit": handlers.post_recall_audit,
            "migration_register": handlers.migration_register,
        },
        routes=(router,),
        health_check=handlers.health_check,
        config_schema=LazyInstructionDiscoveryConfig,
        async_safe=True,
    )
