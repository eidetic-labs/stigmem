"""Experimental RTBF tombstone plugin scaffold."""

from __future__ import annotations

from .config import TombstoneConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "PLUGIN_NAME",
    "TombstoneConfig",
    "plugin_manifest",
]
