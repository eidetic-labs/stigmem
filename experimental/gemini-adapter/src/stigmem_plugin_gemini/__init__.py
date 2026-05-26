"""Public package exports for the Gemini adapter plugin."""

from __future__ import annotations

from .adapter import STIGMEM_FUNCTION_DECLARATIONS, StigmemGeminiAdapter
from .manifest import plugin_manifest

__all__ = [
    "STIGMEM_FUNCTION_DECLARATIONS",
    "StigmemGeminiAdapter",
    "plugin_manifest",
]
