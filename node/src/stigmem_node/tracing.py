"""Compatibility alias for :mod:`stigmem_node.observability.tracing`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["_NoopSpan", "init_tracing", "is_enabled", "start_span"]

if TYPE_CHECKING:
    from .observability.tracing import _NoopSpan, init_tracing, is_enabled, start_span
else:
    from .observability import tracing as _impl

    sys.modules[__name__] = _impl
