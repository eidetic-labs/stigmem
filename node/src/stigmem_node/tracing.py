"""Compatibility alias for :mod:`stigmem_node.observability.tracing`."""

from __future__ import annotations

import sys

from .observability import tracing as _impl

sys.modules[__name__] = _impl
