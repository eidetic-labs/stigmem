"""Compatibility alias for :mod:`stigmem_node.utility.net_util`."""

from __future__ import annotations

import sys

from .utility import net_util as _impl

sys.modules[__name__] = _impl
