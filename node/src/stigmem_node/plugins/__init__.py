"""Plugin hook registry public API.

PR 4-INF.1 intentionally exposed only manual/core/test registration. PR 4-INF.2
adds entry-point discovery while signing, health polling, and operator CLI
support continue to land in focused follow-up slices.
"""

from __future__ import annotations

from .bands import Band
from .capabilities import CAPABILITY_ALLOWLIST, Capability
from .context import CoreApis, PluginContext
from .discovery import (
    ENTRY_POINT_GROUP,
    DiscoveredPlugin,
    discover_plugin_manifests,
    resolve_plugin_dependencies,
)
from .errors import (
    CapabilityError,
    ManifestError,
    PluginDependencyError,
    PluginDiscoveryError,
    PluginExecutionError,
    RegistryFrozenError,
    RejectError,
)
from .handlers import (
    ALLOW_SINGLETON,
    SYSTEM_TENANT,
    Allow,
    AuditEvent,
    Deny,
    Failure,
    Migration,
    Outcome,
    Success,
    TenantContext,
    VotingDecision,
    handler_timeout,
)
from .hooks import HookName, HookOrdering, HookSemantic
from .lifecycle import register_discovered_plugins
from .manifest import PluginManifest
from .registry import HookRegistry, get_registry, register_core_handler, set_registry

__all__ = [
    "ALLOW_SINGLETON",
    "CAPABILITY_ALLOWLIST",
    "SYSTEM_TENANT",
    "Allow",
    "AuditEvent",
    "Band",
    "Capability",
    "CapabilityError",
    "CoreApis",
    "Deny",
    "DiscoveredPlugin",
    "ENTRY_POINT_GROUP",
    "Failure",
    "HookName",
    "HookOrdering",
    "HookRegistry",
    "HookSemantic",
    "ManifestError",
    "Migration",
    "Outcome",
    "PluginContext",
    "PluginDependencyError",
    "PluginDiscoveryError",
    "PluginExecutionError",
    "RegistryFrozenError",
    "PluginManifest",
    "RejectError",
    "Success",
    "TenantContext",
    "VotingDecision",
    "discover_plugin_manifests",
    "get_registry",
    "handler_timeout",
    "register_core_handler",
    "register_discovered_plugins",
    "resolve_plugin_dependencies",
    "set_registry",
]
