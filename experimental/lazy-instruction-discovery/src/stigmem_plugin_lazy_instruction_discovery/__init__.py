"""Experimental lazy instruction discovery plugin scaffold."""

from __future__ import annotations

from .config import LazyInstructionDiscoveryConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "LazyInstructionDiscoveryConfig",
    "PLUGIN_NAME",
    "plugin_manifest",
]
