"""Opt-in gates for the experimental Memory Garden advanced ACL plugin."""

from __future__ import annotations

import os

from .plugins import get_registry

PLUGIN_NAME = "stigmem-plugin-memory-garden-acl"
_ENV_PREFIX = "STIGMEM_MEMORY_GARDEN_ACL_"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str) -> bool:
    return os.environ.get(f"{_ENV_PREFIX}{name}", "").strip().lower() in _TRUE_VALUES


def plugin_registered() -> bool:
    """Return True when the experimental advanced ACL plugin is explicitly registered."""
    return PLUGIN_NAME in get_registry().registered_plugins()


def _gate_enabled(flag_name: str) -> bool:
    return plugin_registered() and _env_bool("ENABLED") and _env_bool(flag_name)


def oidc_permission_ceiling_enabled() -> bool:
    """Gate membership-derived OIDC permission ceilings."""
    return _gate_enabled("ENABLE_OIDC_PERMISSION_CEILING")


def recall_filter_enabled() -> bool:
    """Gate cross-surface garden ACL filtering for recall, graph, and subscriptions."""
    return _gate_enabled("APPLY_RECALL_FILTER")
