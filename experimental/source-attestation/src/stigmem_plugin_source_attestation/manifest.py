"""Plugin manifest factory for source attestation."""

from __future__ import annotations

from stigmem_node.plugins import PluginManifest

from . import handlers
from .config import SourceAttestationConfig

PLUGIN_NAME = "stigmem-plugin-source-attestation"
PLUGIN_VERSION = "0.1.0"
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
                "federation.read",
                "federation.write",
                "identity.read",
                "audit.emit",
                "config.read",
            }
        ),
        hooks={
            "config_validate": handlers.config_validate,
            "pre_assert_validate": handlers.pre_assert_validate,
            "recall_rank": handlers.recall_rank,
            "federation_inbound_validate": handlers.federation_inbound_validate,
        },
        config_schema=SourceAttestationConfig,
        health_check=handlers.health_check,
        async_safe=True,
    )
