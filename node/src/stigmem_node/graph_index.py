"""Compatibility alias for :mod:`stigmem_node.recall.graph_index`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["sync_edge_confidence", "sync_edge_expiry", "upsert_edge"]

if TYPE_CHECKING:
    from .recall.graph_index import sync_edge_confidence, sync_edge_expiry, upsert_edge
else:
    from .recall import graph_index as _impl

    sys.modules[__name__] = _impl
