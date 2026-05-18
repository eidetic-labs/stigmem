"""Compatibility alias for :mod:`stigmem_node.recall.graph`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["MAX_DEPTH", "NeighborEntry", "bfs_neighbors"]

if TYPE_CHECKING:
    from .recall.graph import MAX_DEPTH, NeighborEntry, bfs_neighbors
else:
    from .recall import graph as _impl

    sys.modules[__name__] = _impl
