"""Runtime gate for experimental RTBF tombstone behavior."""

from __future__ import annotations

import os
from collections.abc import Mapping

TOMBSTONE_PLUGIN_NAME = "stigmem-plugin-tombstones"
_ENV_PREFIX = "STIGMEM_TOMBSTONES_"


def tombstone_plugin_registered() -> bool:
    """Return True when the RTBF tombstone plugin is active in the registry."""
    from ..plugins import get_registry

    return TOMBSTONE_PLUGIN_NAME in get_registry().registered_plugins()


def tombstone_filter_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return True only when tombstone filtering is explicitly enabled."""

    if not tombstone_plugin_registered():
        return False
    env = environ if environ is not None else os.environ
    return _env_bool(env, f"{_ENV_PREFIX}ENABLED") and _env_bool(
        env, f"{_ENV_PREFIX}ALLOW_RECALL_FILTER"
    )


def _env_bool(env: Mapping[str, str], name: str, *, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
