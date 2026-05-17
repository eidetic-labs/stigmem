"""Experimental source-attestation plugin scaffold."""

from __future__ import annotations

from .config import SourceAttestationConfig
from .manifest import PLUGIN_NAME, plugin_manifest

__all__ = [
    "PLUGIN_NAME",
    "SourceAttestationConfig",
    "plugin_manifest",
]
