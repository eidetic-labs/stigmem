"""Plugin manifest factory for Memory Garden advanced ACL."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import MemoryGardenAclConfig

PLUGIN_NAME = "stigmem-plugin-memory-garden-acl"
PLUGIN_VERSION = "0.1.0"
REQUIRES_STIGMEM = ">=0.9.0a1"


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
                "identity.read",
                "audit.emit",
                "config.read",
            }
        ),
        hooks={
            "pre_assert_authorize": handlers.pre_assert_authorize,
            "pre_recall_authorize": handlers.pre_recall_authorize,
            "recall_filter": handlers.recall_filter,
        },
        routes=(),
        config_schema=MemoryGardenAclConfig,
        health_check=handlers.health_check,
        async_safe=True,
    )
