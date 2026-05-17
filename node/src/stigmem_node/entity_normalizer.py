"""Compatibility alias for :mod:`stigmem_node.utility.entity_normalizer`."""

from __future__ import annotations

import sys

from .utility import entity_normalizer as _impl

sys.modules[__name__] = _impl
