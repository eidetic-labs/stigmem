"""Compatibility alias for :mod:`stigmem_node.lifecycle.tombstone_gate`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["TOMBSTONE_PLUGIN_NAME", "tombstone_plugin_registered"]

if TYPE_CHECKING:
    from .lifecycle.tombstone_gate import TOMBSTONE_PLUGIN_NAME, tombstone_plugin_registered
else:
    from .lifecycle import tombstone_gate as _impl

    sys.modules[__name__] = _impl

