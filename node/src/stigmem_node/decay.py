"""Compatibility alias for :mod:`stigmem_node.lifecycle.decay`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["run_decay_sweep"]

if TYPE_CHECKING:
    from .lifecycle.decay import run_decay_sweep
else:
    from .lifecycle import decay as _impl

    sys.modules[__name__] = _impl
