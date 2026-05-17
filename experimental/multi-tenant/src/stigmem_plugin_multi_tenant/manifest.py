"""Plugin manifest factory for multi-tenant isolation."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import MultiTenantConfig

PLUGIN_NAME = "stigmem-plugin-multi-tenant"
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
                "federation.read",
                "federation.write",
                "identity.read",
                "tenant.read",
                "tenant.write",
                "audit.emit",
                "config.read",
            }
        ),
        hooks={
            "config_validate": handlers.config_validate,
            "tenant_resolve": handlers.tenant_resolve,
            "pre_assert_authorize": handlers.pre_assert_authorize,
            "pre_recall_authorize": handlers.pre_recall_authorize,
            "recall_filter": handlers.recall_filter,
            "federation_outbound_filter": handlers.federation_outbound_filter,
            "migration_register": handlers.migration_register,
        },
        config_schema=MultiTenantConfig,
        health_check=handlers.health_check,
        async_safe=True,
    )
