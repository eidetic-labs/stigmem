"""Public package exports for the Letta adapter plugin."""

from __future__ import annotations

from .adapter import StigmemLettaAdapter
from .manifest import plugin_manifest

__all__ = [
    "StigmemLettaAdapter",
    "plugin_manifest",
]
