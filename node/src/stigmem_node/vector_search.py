"""Vector search primitive — Phase 9 (spec §20 / design memo §2–3).

Public API::

    vector_search(query_embedding, k=10, scope_filter=None, tenant_id="default")
        -> list[tuple[FactRecord, float]]

    embed_and_store_fact(fact_id, entity, relation, value_type, value_v, conn, model)

    backfill_missing_embeddings(conn, model, limit=500)

    EmbeddingModelMismatch  — raised when stored model_id / dimension differs
                              from configured model.
"""

from __future__ import annotations

import json
import logging
import struct
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .embedding.base import EmbeddingModel, Vector
    from .models import FactRecord

logger = logging.getLogger("stigmem.vector_search")


class EmbeddingModelMismatch(RuntimeError):
    """Raised when the configured model conflicts with a stored embedding_meta row."""


# ---------------------------------------------------------------------------
# vec_facts virtual table management
# ---------------------------------------------------------------------------

def ensure_vec_table(conn: Any, dimension: int) -> None:
    """Create the ``vec_facts`` virtual table if it does not exist.

    Called after the sqlite-vec extension is loaded.  Safe to call on every
    connection open (the CREATE is guarded by IF NOT EXISTS).

    Raises ``RuntimeError`` if sqlite-vec is not loaded.
    """
    try:
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts "
            f"USING vec0(fact_id TEXT PRIMARY KEY, embedding FLOAT[{dimension}])"
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to create vec_facts virtual table (is sqlite-vec loaded?): {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Mixed-model safety
# ---------------------------------------------------------------------------

def check_or_register_model(conn: Any, model_id: str, dimension: int) -> None:
    """Assert that the stored embedding_meta matches *model_id* / *dimension*.

    On first use (empty table) registers the model.  Raises
    ``EmbeddingModelMismatch`` on conflicts.  Callers must hold a transaction.
    """
    row = conn.execute("SELECT model_id, dimension FROM embedding_meta WHERE id = 1").fetchone()
    if row is None:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO embedding_meta (id, model_id, dimension, created_at) VALUES (1, ?, ?, ?)",
            (model_id, dimension, now),
        )
        return

    stored_model = row["model_id"]
    stored_dim = int(row["dimension"])
    if stored_model != model_id or stored_dim != dimension:
        raise EmbeddingModelMismatch(
            f"Embedding model mismatch: stored=({stored_model!r}, dim={stored_dim}) "
            f"!= configured=({model_id!r}, dim={dimension}). "
            "Run `stigmem embed reindex` to re-embed all facts with the new model, "
            "or restore the original model configuration."
        )


# ---------------------------------------------------------------------------
# Encode / decode vectors for sqlite-vec BLOB storage
# ---------------------------------------------------------------------------

def _encode_vector(vec: "Vector") -> bytes:
    """Encode a float list as a little-endian IEEE 754 BLOB for sqlite-vec."""
    return struct.pack(f"<{len(vec)}f", *vec)


# ---------------------------------------------------------------------------
# Write-path: store a single embedding
# ---------------------------------------------------------------------------

def store_embedding(conn: Any, fact_id: str, vec: "Vector") -> None:
    """Upsert a vector into ``vec_facts`` and mark the fact as embedded."""
    blob = _encode_vector(vec)
    conn.execute(
        "INSERT OR REPLACE INTO vec_facts (fact_id, embedding) VALUES (?, ?)",
        (fact_id, blob),
    )
    conn.execute(
        "UPDATE facts SET embedding_missing = 0 WHERE id = ?",
        (fact_id,),
    )


def embed_and_store_fact(
    fact_id: str,
    entity: str,
    relation: str,
    value_type: str,
    value_v: str,
    conn: Any,
    model: "EmbeddingModel",
) -> None:
    """Embed one fact and persist the vector.  Caller owns the transaction."""
    from .embedding.base import compose_triple_text

    text = compose_triple_text(entity, relation, value_type, value_v)
    vecs = model.embed([text])
    store_embedding(conn, fact_id, vecs[0])


# ---------------------------------------------------------------------------
# Backfill job
# ---------------------------------------------------------------------------

def backfill_missing_embeddings(
    conn: Any,
    model: "EmbeddingModel",
    limit: int = 500,
) -> int:
    """Embed facts with ``embedding_missing = 1``.

    Returns the number of facts successfully embedded.  Skips facts on per-fact
    failures and continues (graceful degradation).
    """
    from .embedding.base import compose_triple_text

    rows = conn.execute(
        """SELECT id, entity, relation, value_type, value_v
           FROM facts
           WHERE embedding_missing = 1 AND confidence > 0.1
           LIMIT ?""",
        (limit,),
    ).fetchall()

    count = 0
    for row in rows:
        try:
            text = compose_triple_text(
                row["entity"], row["relation"], row["value_type"], row["value_v"] or ""
            )
            vecs = model.embed([text])
            store_embedding(conn, row["id"], vecs[0])
            count += 1
        except Exception as exc:
            logger.warning("Backfill embed failed for fact %s: %s", row["id"], exc)

    return count


# ---------------------------------------------------------------------------
# Query-path: vector_search
# ---------------------------------------------------------------------------

def vector_search(
    query_embedding: "Vector",
    k: int = 10,
    scope_filter: str | None = None,
    tenant_id: str = "default",
    conn: Any = None,
) -> list[tuple["FactRecord", float]]:
    """Return the top-k facts closest to *query_embedding* by cosine similarity.

    *query_embedding* MUST be L2-normalised (stored vectors are also normalised,
    so dot product == cosine similarity — design memo §2).

    Args:
        query_embedding: Unit-length query vector.
        k: Maximum results to return.
        scope_filter: When set, restrict to facts with this scope.
        tenant_id: Tenant to search within.
        conn: Optional existing DB connection; if None, opens one via ``db()``.

    Returns:
        List of (FactRecord, similarity) tuples, sorted descending by similarity.
    """
    from .db import db
    from .models import row_to_record

    blob = _encode_vector(query_embedding)

    def _run(c: Any) -> list[tuple["FactRecord", float]]:
        # scope_clause is a literal SQL fragment ("AND f.scope = ?" or ""),
        # never user-supplied text; the actual scope value flows through scope_params.
        scope_clause = "AND f.scope = ?" if scope_filter else ""
        scope_params: tuple = (scope_filter,) if scope_filter else ()

        sql = f"""
            SELECT f.*, v.distance
            FROM vec_facts v
            JOIN facts f ON f.id = v.fact_id
            WHERE v.embedding MATCH ?
              AND k = ?
              AND f.confidence > 0.1
              AND f.tenant_id = ?
              {scope_clause}
            ORDER BY v.distance
        """  # nosec B608 — scope_clause is a literal fragment; all user values in params
        params: tuple = (blob, k, tenant_id) + scope_params

        rows = c.execute(sql, params).fetchall()
        results: list[tuple["FactRecord", float]] = []
        for row in rows:
            distance = float(row["distance"])
            similarity = max(0.0, 1.0 - distance)
            record = row_to_record(row)
            results.append((record, similarity))
        return results

    if conn is not None:
        return _run(conn)

    with db() as c:
        return _run(c)
