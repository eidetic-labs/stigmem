"""Compatibility alias for :mod:`stigmem_node.recall.vector_search`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "EmbeddingModelMismatch",
    "backfill_missing_embeddings",
    "check_or_register_model",
    "embed_and_store_fact",
    "ensure_vec_table",
    "store_embedding",
    "vector_search",
]

if TYPE_CHECKING:
    from .recall.vector_search import (
        EmbeddingModelMismatch,
        backfill_missing_embeddings,
        check_or_register_model,
        embed_and_store_fact,
        ensure_vec_table,
        store_embedding,
        vector_search,
    )
else:
    from .recall import vector_search as _impl

    sys.modules[__name__] = _impl
