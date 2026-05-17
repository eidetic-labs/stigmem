"""Compatibility alias for :mod:`stigmem_node.observability.metrics`."""

from __future__ import annotations

import sys

from .observability import metrics as _impl

sys.modules[__name__] = _impl
