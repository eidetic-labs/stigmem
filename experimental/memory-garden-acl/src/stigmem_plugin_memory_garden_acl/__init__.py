"""Experimental Memory Garden advanced ACL plugin scaffold."""

from __future__ import annotations

from .config import MemoryGardenAclConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "PLUGIN_NAME",
    "MemoryGardenAclConfig",
    "plugin_manifest",
]
