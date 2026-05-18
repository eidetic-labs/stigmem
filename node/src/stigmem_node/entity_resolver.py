"""Compatibility alias for :mod:`stigmem_node.recall.entity_resolver`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "FUZZY_SCORE_THRESHOLD",
    "ResolveCandidate",
    "ResolveResult",
    "_id_segment",
    "_token_score",
    "_tokenise",
    "_type_prefix",
    "resolve_entity",
]

if TYPE_CHECKING:
    from .recall.entity_resolver import (
        FUZZY_SCORE_THRESHOLD,
        ResolveCandidate,
        ResolveResult,
        _id_segment,
        _token_score,
        _tokenise,
        _type_prefix,
        resolve_entity,
    )
else:
    from .recall import entity_resolver as _impl

    sys.modules[__name__] = _impl
