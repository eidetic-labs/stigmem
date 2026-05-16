"""Runtime gate for experimental RTBF tombstone behavior."""

from __future__ import annotations

TOMBSTONE_PLUGIN_NAME = "stigmem-plugin-tombstones"


def tombstone_plugin_registered() -> bool:
    """Return True when the RTBF tombstone plugin is active in the registry."""
    from .plugins import get_registry

    return TOMBSTONE_PLUGIN_NAME in get_registry().registered_plugins()

