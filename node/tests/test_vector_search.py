"""Phase 4c coverage: vector_search unit tests.

Covers ``stigmem_node.vector_search`` paths that don't require sqlite-vec
(extension not installed in the test image).  Tests that need the extension
are skipped with an explicit reason.

Targets:
- ``EmbeddingModelMismatch`` (raised by check_or_register_model paths)
- ``ensure_vec_table``: success + RuntimeError wrapping
- ``check_or_register_model``: insert / no-op / mismatch (id, dim)
- ``_encode_vector``: round-trip via struct
- ``store_embedding``: INSERT into vec_facts + update fact_embedding_status projection
- ``embed_and_store_fact``: invokes model.embed and persists
- ``backfill_missing_embeddings``: success / per-fact failure / LIMIT
- ``vector_search``: skipped (requires sqlite-vec)
"""

from __future__ import annotations

import sqlite3
import struct
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stigmem_node.db import apply_migrations
from stigmem_node.embedding.base import EmbeddingModel, Vector
from stigmem_node.embedding.stub_adapter import StubEmbeddingModel
from stigmem_node.vector_search import (
    EmbeddingModelMismatch,
    _encode_vector,
    backfill_missing_embeddings,
    check_or_register_model,
    embed_and_store_fact,
    ensure_vec_table,
    store_embedding,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_plain(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _create_vec_facts_stub(conn: sqlite3.Connection) -> None:
    """Create a plain table named ``vec_facts`` so store_embedding's
    INSERT OR REPLACE works without the sqlite-vec extension.

    This mirrors the schema sqlite-vec exposes (fact_id PRIMARY KEY, embedding BLOB)
    closely enough for unit testing the write path.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS vec_facts (  fact_id TEXT PRIMARY KEY,  embedding BLOB)"
    )


def _insert_fact(
    conn: sqlite3.Connection,
    *,
    fact_id: str | None = None,
    entity: str = "user:alice",
    relation: str = "memory:role",
    value_v: str = "CEO",
    embedding_missing: int = 1,
    confidence: float = 1.0,
) -> str:
    fact_id = fact_id or str(uuid.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute(
        """INSERT INTO facts
           (id, entity, relation, value_type, value_v, source, timestamp,
            valid_until, confidence, scope, hlc, received_from, attested_key_id,
            garden_id, attested, tenant_id, embedding_missing)
           VALUES (?, ?, ?, 'string', ?, 'agent:test', ?, NULL, ?, 'local', ?,
                   NULL, NULL, NULL, NULL, 'default', ?)""",
        (fact_id, entity, relation, value_v, now, confidence, now, embedding_missing),
    )
    return fact_id


def _embedding_missing(conn: sqlite3.Connection, fact_id: str) -> int | None:
    row = conn.execute(
        "SELECT embedding_missing FROM fact_embedding_status WHERE fact_id = ?",
        (fact_id,),
    ).fetchone()
    return None if row is None else int(row["embedding_missing"])


# ---------------------------------------------------------------------------
# ensure_vec_table
# ---------------------------------------------------------------------------


def test_ensure_vec_table_runtime_error_when_execute_fails() -> None:
    """Without sqlite-vec, vec0 CREATE fails → wrapped as RuntimeError."""
    conn = MagicMock()
    conn.execute.side_effect = sqlite3.OperationalError("no such module: vec0")
    with pytest.raises(RuntimeError, match="vec_facts"):
        ensure_vec_table(conn, 4)


def test_ensure_vec_table_succeeds_with_passing_conn() -> None:
    """When conn.execute succeeds, ensure_vec_table returns silently."""
    conn = MagicMock()
    conn.execute.return_value = None
    ensure_vec_table(conn, 4)  # must not raise
    args, _ = conn.execute.call_args
    assert "FLOAT[4]" in args[0]
    assert "vec_facts" in args[0]


# ---------------------------------------------------------------------------
# check_or_register_model
# ---------------------------------------------------------------------------


def test_check_or_register_model_inserts_when_empty(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)

    check_or_register_model(conn, "test-model", 8)
    conn.commit()

    row = conn.execute("SELECT model_id, dimension FROM embedding_meta WHERE id=1").fetchone()
    assert row["model_id"] == "test-model"
    assert int(row["dimension"]) == 8
    conn.close()


def test_check_or_register_model_noop_when_match(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)

    check_or_register_model(conn, "test-model", 8)
    conn.commit()
    # Second call with identical values must not raise / not duplicate row.
    check_or_register_model(conn, "test-model", 8)
    rows = conn.execute("SELECT * FROM embedding_meta").fetchall()
    assert len(rows) == 1
    conn.close()


def test_check_or_register_model_raises_on_id_mismatch(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)

    check_or_register_model(conn, "model-a", 8)
    conn.commit()
    with pytest.raises(EmbeddingModelMismatch, match="mismatch"):
        check_or_register_model(conn, "model-b", 8)
    conn.close()


def test_check_or_register_model_raises_on_dim_mismatch(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)

    check_or_register_model(conn, "model-a", 8)
    conn.commit()
    with pytest.raises(EmbeddingModelMismatch, match="mismatch"):
        check_or_register_model(conn, "model-a", 16)
    conn.close()


# ---------------------------------------------------------------------------
# _encode_vector
# ---------------------------------------------------------------------------


def test_encode_vector_length_is_4_bytes_per_float() -> None:
    vec: Vector = [0.1, 0.2, 0.3, 0.4]
    blob = _encode_vector(vec)
    assert len(blob) == len(vec) * 4


def test_encode_vector_round_trips_via_struct() -> None:
    vec: Vector = [1.0, -2.5, 0.5]
    blob = _encode_vector(vec)
    decoded = list(struct.unpack(f"<{len(vec)}f", blob))
    assert decoded == pytest.approx(vec, rel=1e-6)


# ---------------------------------------------------------------------------
# store_embedding (uses a plain table standing in for vec_facts)
# ---------------------------------------------------------------------------


def test_store_embedding_persists_vector_and_clears_flag(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    fact_id = _insert_fact(conn, embedding_missing=1)
    vec: Vector = [0.0, 1.0, 0.0, 0.0]
    store_embedding(conn, fact_id, vec)
    conn.commit()

    assert _embedding_missing(conn, fact_id) == 0

    blob = conn.execute("SELECT embedding FROM vec_facts WHERE fact_id=?", (fact_id,)).fetchone()
    assert blob is not None
    assert blob["embedding"] == _encode_vector(vec)
    conn.close()


# ---------------------------------------------------------------------------
# embed_and_store_fact
# ---------------------------------------------------------------------------


class _DeterministicModel(EmbeddingModel):
    """Tiny stub that returns a fixed vector regardless of input."""

    def __init__(self, vec: Vector) -> None:
        self._vec = vec
        self.calls: list[list[str]] = []

    @property
    def model_id(self) -> str:
        return "det-model"

    @property
    def dimension(self) -> int:
        return len(self._vec)

    def embed(self, texts: list[str]) -> list[Vector]:
        self.calls.append(list(texts))
        return [list(self._vec) for _ in texts]


def test_embed_and_store_fact_calls_model_and_persists(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    fact_id = _insert_fact(conn)
    model = _DeterministicModel([0.5, 0.5, 0.5, 0.5])
    embed_and_store_fact(fact_id, "user:alice", "memory:role", "string", "CEO", conn, model)
    conn.commit()

    # Model was called with the composed triple text.
    assert len(model.calls) == 1
    text = model.calls[0][0]
    assert "alice" in text and "memory:role" in text and "CEO" in text

    # Vector landed in vec_facts and the projection flag is cleared.
    blob = conn.execute("SELECT embedding FROM vec_facts WHERE fact_id=?", (fact_id,)).fetchone()
    assert blob["embedding"] == _encode_vector([0.5, 0.5, 0.5, 0.5])
    assert _embedding_missing(conn, fact_id) == 0
    conn.close()


# ---------------------------------------------------------------------------
# backfill_missing_embeddings
# ---------------------------------------------------------------------------


def test_backfill_embeds_all_missing(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    ids = [_insert_fact(conn, entity=f"user:p{i}") for i in range(3)]
    model = StubEmbeddingModel(dim=4)
    count = backfill_missing_embeddings(conn, model, limit=10)
    conn.commit()

    assert count == 3
    for fid in ids:
        assert _embedding_missing(conn, fid) == 0
    conn.close()


def test_backfill_continues_after_per_fact_failure(tmp_path: Path) -> None:
    """When a single embed call raises, backfill logs and continues; the
    return value reflects only the successful embeds."""
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    _insert_fact(conn, entity="user:good1")
    _insert_fact(conn, entity="user:good2")
    _insert_fact(conn, entity="user:bad")

    class _FlakyModel(EmbeddingModel):
        @property
        def model_id(self) -> str:
            return "flaky"

        @property
        def dimension(self) -> int:
            return 4

        def embed(self, texts: list[str]) -> list[Vector]:
            # Fail when the composed text mentions "bad", succeed otherwise.
            if any("bad" in t for t in texts):
                raise RuntimeError("simulated embed failure")
            return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    count = backfill_missing_embeddings(conn, _FlakyModel(), limit=10)
    conn.commit()

    assert count == 2
    conn.close()


def test_backfill_respects_limit(tmp_path: Path) -> None:
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    for i in range(5):
        _insert_fact(conn, entity=f"user:p{i}")
    model = StubEmbeddingModel(dim=4)
    count = backfill_missing_embeddings(conn, model, limit=2)
    conn.commit()

    assert count == 2
    remaining = conn.execute(
        """SELECT COUNT(*) AS n
           FROM facts f
           LEFT JOIN fact_embedding_status fes ON fes.fact_id = f.id
           WHERE COALESCE(fes.embedding_missing, f.embedding_missing) = 1"""
    ).fetchone()
    assert remaining["n"] == 3
    conn.close()


def test_backfill_skips_low_confidence_facts(tmp_path: Path) -> None:
    """Facts with confidence <= 0.1 are intentionally excluded by the query."""
    db_file = str(tmp_path / "t.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    _create_vec_facts_stub(conn)

    _insert_fact(conn, entity="user:lowconf", confidence=0.05)
    model = StubEmbeddingModel(dim=4)
    count = backfill_missing_embeddings(conn, model, limit=10)
    conn.commit()
    assert count == 0
    conn.close()


# ---------------------------------------------------------------------------
# vector_search — requires the sqlite-vec extension
# ---------------------------------------------------------------------------


def _load_sqlite_vec(conn: sqlite3.Connection, dim: int) -> bool:
    try:
        import sqlite_vec  # type: ignore[import]

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        from stigmem_node.vector_search import ensure_vec_table as _ensure

        _ensure(conn, dim)
        return True
    except Exception:
        return False


def test_vector_search_returns_ranked_results(tmp_path: Path) -> None:
    """Full vector_search round-trip when sqlite-vec is available."""
    pytest.importorskip("sqlite_vec", reason="sqlite-vec extension not installed")

    db_file = str(tmp_path / "vs.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    if not _load_sqlite_vec(conn, 4):
        pytest.skip("sqlite-vec failed to load")

    model = StubEmbeddingModel(dim=4)
    check_or_register_model(conn, model.model_id, model.dimension)

    fid_a = _insert_fact(conn, entity="user:alice", value_v="CEO")
    fid_b = _insert_fact(conn, entity="user:bob", value_v="CTO")
    embed_and_store_fact(fid_a, "user:alice", "memory:role", "string", "CEO", conn, model)
    embed_and_store_fact(fid_b, "user:bob", "memory:role", "string", "CTO", conn, model)
    conn.commit()

    # Query with the same text used to embed fid_a — alice should rank first.
    from stigmem_node.embedding.base import compose_triple_text
    from stigmem_node.vector_search import vector_search as _vs

    query_text = compose_triple_text("user:alice", "memory:role", "string", "CEO")
    qvec = model.embed([query_text])[0]
    results = _vs(qvec, k=2, conn=conn)
    assert len(results) >= 1
    top_record, top_sim = results[0]
    assert top_record.id == fid_a
    assert 0.0 <= top_sim <= 1.0
    conn.close()


def test_vector_search_with_scope_filter(tmp_path: Path) -> None:
    """scope_filter restricts results to facts with a matching scope."""
    pytest.importorskip("sqlite_vec", reason="sqlite-vec extension not installed")

    db_file = str(tmp_path / "vs.db")
    apply_migrations(db_path=db_file)
    conn = _open_plain(db_file)
    if not _load_sqlite_vec(conn, 4):
        pytest.skip("sqlite-vec failed to load")

    model = StubEmbeddingModel(dim=4)
    check_or_register_model(conn, model.model_id, model.dimension)

    # Two facts in different scopes; only one should match the scope filter.
    fid_pub = str(uuid.uuid4())
    fid_priv = str(uuid.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for fid, scope in [(fid_pub, "public"), (fid_priv, "team")]:
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                valid_until, confidence, scope, hlc, received_from, attested_key_id,
                garden_id, attested, tenant_id, embedding_missing)
               VALUES (?, 'user:carol', 'memory:role', 'string', 'engineer',
                       'agent:test', ?, NULL, 1.0, ?, ?, NULL, NULL, NULL, NULL,
                       'default', 1)""",
            (fid, now, scope, now),
        )

    embed_and_store_fact(fid_pub, "user:carol", "memory:role", "string", "engineer", conn, model)
    embed_and_store_fact(fid_priv, "user:carol", "memory:role", "string", "engineer", conn, model)
    conn.commit()

    from stigmem_node.embedding.base import compose_triple_text
    from stigmem_node.vector_search import vector_search as _vs

    query_text = compose_triple_text("user:carol", "memory:role", "string", "engineer")
    qvec = model.embed([query_text])[0]
    results = _vs(qvec, k=10, scope_filter="public", conn=conn)
    returned_ids = {rec.id for rec, _ in results}
    # All returned facts must have scope=public.
    for rec, _ in results:
        assert rec.scope == "public"
    assert fid_pub in returned_ids
    assert fid_priv not in returned_ids
    conn.close()
