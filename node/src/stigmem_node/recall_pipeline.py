"""Compatibility alias for :mod:`stigmem_node.recall.recall_pipeline`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["apply_recall_pipeline", "reset_pattern_cache"]

if TYPE_CHECKING:
    from .recall.recall_pipeline import apply_recall_pipeline, reset_pattern_cache
else:
    from .recall import recall_pipeline as _impl

    sys.modules[__name__] = _impl
