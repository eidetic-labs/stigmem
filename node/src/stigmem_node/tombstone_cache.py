"""Compatibility alias for :mod:`stigmem_node.lifecycle.tombstone_cache`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["invalidate", "is_tombstoned"]

if TYPE_CHECKING:
    from .lifecycle.tombstone_cache import invalidate, is_tombstoned
else:
    from .lifecycle import tombstone_cache as _impl

    sys.modules[__name__] = _impl
