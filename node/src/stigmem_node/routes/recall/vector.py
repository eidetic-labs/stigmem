"""Dense vector recall search stage."""

from __future__ import annotations

from typing import Any

from .common import _public_module, logger


def _semantic_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
) -> dict[str, float]:
    """Return {fact_id: cosine_similarity}. Returns {} when embed_enabled=False."""
    if not _public_module().settings.embed_enabled:
        return {}
    try:
        from ...embedding import get_embedding_model
        from ...recall.vector_search import vector_search

        model = get_embedding_model()
        vecs = model.embed([query])
        if not vecs:
            return {}
        results = vector_search(vecs[0], k=k, scope_filter=scope, tenant_id=tenant_id, conn=conn)
        return {record.id: float(sim) for record, sim in results}
    except Exception as exc:
        logger.warning("Semantic search failed: %s", exc)
        return {}
