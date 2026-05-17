"""Experimental multi-tenant plugin."""

from __future__ import annotations

from .config import MultiTenantConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "PLUGIN_NAME",
    "MultiTenantConfig",
    "plugin_manifest",
]
