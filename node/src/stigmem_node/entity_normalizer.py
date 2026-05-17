"""Compatibility alias for :mod:`stigmem_node.utility.entity_normalizer`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = ["NormalizationError", "is_informal", "normalize_entity_uri"]

if TYPE_CHECKING:
    from .utility.entity_normalizer import NormalizationError, is_informal, normalize_entity_uri
else:
    from .utility import entity_normalizer as _impl

    sys.modules[__name__] = _impl
