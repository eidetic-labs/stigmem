"""Opt-in gates for the experimental Memory Garden advanced ACL plugin."""

from __future__ import annotations

import os
from logging import Logger

from .db import db
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


def memory_garden_acl_filtering_state() -> str:
    """Return the operator-visible advanced ACL filtering posture.

    ``disabled`` means default core behavior is active: direct garden reads and
    writes are guarded, but tenant-wide query, recall, graph, OIDC ceiling, and
    subscription-delivery filtering are not all enabled.
    """
    if not plugin_registered() or not _env_bool("ENABLED"):
        return "disabled"
    if recall_filter_enabled() and oidc_permission_ceiling_enabled():
        return "enabled-full"
    return "enabled-partial"


def gardens_with_members_exist() -> bool:
    """Return True when at least one garden membership row exists."""
    with db() as conn:
        row = conn.execute("SELECT 1 FROM garden_members LIMIT 1").fetchone()
    return row is not None


def warn_if_memory_garden_acl_filtering_disabled(logger: Logger) -> None:
    """Warn once at startup when gardens exist but advanced ACL filtering is off."""
    if plugin_registered() or not gardens_with_members_exist():
        return
    logger.warning(
        "SECURITY WARNING: Garden ACL filtering is disabled "
        "(stigmem-plugin-memory-garden-acl not registered). Restricted gardens "
        "do not filter tenant-wide queries, recall ranking, push subscriptions, "
        "or graph traversal. Install and enable the plugin, or accept the "
        "documented opt-in Memory Garden ACL posture."
    )
