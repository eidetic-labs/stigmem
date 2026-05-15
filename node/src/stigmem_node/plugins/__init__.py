"""Plugin hook registry public API.

PR 4-INF.1 intentionally exposed only manual/core/test registration. PR 4-INF.2
adds entry-point discovery, installed-plugin lifecycle registration, plugin
migrations, registration audit payloads, and lifecycle health reporting while
signing and operator CLI support continue to land in focused follow-up slices.
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
    PluginMigrationError,
    PluginSignatureError,
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
    PluginHealth,
    PluginHealthReport,
    PluginHealthStatus,
    PluginInfo,
    Success,
    TenantContext,
    VotingDecision,
    handler_timeout,
)
from .hooks import HookName, HookOrdering, HookSemantic
from .lifecycle import register_discovered_plugins
from .manifest import PluginManifest
from .registry import HookRegistry, get_registry, register_core_handler, set_registry
from .signing import (
    PluginSignatureVerifier,
    PluginSigningInfo,
    PluginTrustPolicy,
    require_verified_signature,
)

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
    "PluginHealth",
    "PluginHealthReport",
    "PluginHealthStatus",
    "PluginInfo",
    "PluginMigrationError",
    "PluginSignatureError",
    "PluginSignatureVerifier",
    "PluginSigningInfo",
    "PluginTrustPolicy",
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
    "require_verified_signature",
    "resolve_plugin_dependencies",
    "set_registry",
]
