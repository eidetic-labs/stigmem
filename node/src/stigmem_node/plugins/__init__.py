"""Plugin hook registry public API.

PR 4-INF.1 intentionally exposes only manual/core/test registration. Package
discovery, signing, health polling, and operator CLI support land in later
PR 4-INF slices.
"""

from __future__ import annotations

from .bands import Band
from .capabilities import CAPABILITY_ALLOWLIST, Capability
from .context import CoreApis, PluginContext
from .errors import (
    CapabilityError,
    ManifestError,
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
    "Failure",
    "HookName",
    "HookOrdering",
    "HookRegistry",
    "HookSemantic",
    "ManifestError",
    "Migration",
    "Outcome",
    "PluginContext",
    "PluginExecutionError",
    "RegistryFrozenError",
    "PluginManifest",
    "RejectError",
    "Success",
    "TenantContext",
    "VotingDecision",
    "get_registry",
    "handler_timeout",
    "register_core_handler",
    "set_registry",
]
