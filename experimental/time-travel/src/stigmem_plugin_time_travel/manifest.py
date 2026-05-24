"""Plugin manifest factory for time-travel queries."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import TimeTravelConfig

PLUGIN_NAME = "stigmem-plugin-time-travel"
PLUGIN_VERSION = "0.1.0"
REQUIRES_STIGMEM = ">=0.9.0a4"


def plugin_manifest() -> PluginManifest:
    """Return the entry-point manifest consumed by ``stigmem.plugins`` discovery."""

    return PluginManifest(
        name=PLUGIN_NAME,
        version=PLUGIN_VERSION,
        requires_stigmem=REQUIRES_STIGMEM,
        capabilities=frozenset(
            {
                "facts.read",
                "recall.read",
                "config.read",
                "audit.emit",
            }
        ),
        hooks={
            "pre_recall_authorize": handlers.pre_recall_authorize,
            "pre_recall_rewrite": handlers.pre_recall_rewrite,
            "post_recall_audit": handlers.post_recall_audit,
        },
        config_schema=TimeTravelConfig,
        health_check=handlers.health_check,
        async_safe=True,
    )
