"""Compatibility alias for :mod:`stigmem_node.recall.fuzzy_resolver`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["register_alias", "resolve_entity"]

if TYPE_CHECKING:
    from .recall.fuzzy_resolver import register_alias, resolve_entity
else:
    from .recall import fuzzy_resolver as _impl

    sys.modules[__name__] = _impl
