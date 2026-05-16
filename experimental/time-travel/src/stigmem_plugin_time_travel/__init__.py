"""Experimental time-travel query plugin scaffold."""

from __future__ import annotations

from .config import TimeTravelConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "PLUGIN_NAME",
    "TimeTravelConfig",
    "plugin_manifest",
]
