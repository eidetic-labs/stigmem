"""Phase 9 tests: sqlite-vec embeddings + embedding-model adapter.

Scope (ACM-211 acceptance criteria):
  - embed-on-write: embedding_missing flag set/cleared; entity_edges populated for ref facts
  - vector_search primitive: returns ranked results
  - dimension-mismatch refusal (EmbeddingModelMismatch)
  - backfill task
  - EmbeddingModel adapter interface (stub / dimension / model_id)

All tests use the StubEmbeddingModel (no external deps) and bypass the
background thread by calling embedding helpers directly.
"""

from __future__ import annotations

import math
import sqlite3
import time
import uuid
from pathlib import Path

import pytest

import stigmem_node.db as db_mod
from stigmem_node.embedding import compose_triple_text
from stigmem_node.embedding.base import l2_normalize
from stigmem_node.embedding.stub_adapter import StubEmbeddingModel
from stigmem_node.vector_search import (
    EmbeddingModelMismatch,
    backfill_missing_embeddings,
    check_or_register_model,
    embed_and_store_fact,
    ensure_vec_table,
    vector_search,
)

apply_migrations = db_mod.apply_migrations


def _open_plain(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _load_sqlite_vec(conn: sqlite3.Connection, dim: int) -> bool:
    """Try to load sqlite-vec; return True if available, False otherwise."""
    try:
        import sqlite_vec  # type: ignore[import]

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        ensure_vec_table(conn, dim)
        return True
    except (ImportError, Exception):
        return False


def _insert_fact(conn: sqlite3.Connection, **overrides: object) -> str:
    fact_id = str(uuid.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    defaults = dict(
        id=fact_id,
        entity="user:alice",
        relation="memory:role",
        value_type="string",
        value_v="CEO",
        source="agent:assistant",
        timestamp=now,
        valid_until=None,
        confidence=1.0,
        scope="local",
        hlc=now,
        received_from=None,
        attested_key_id=None,
        garden_id=None,
        attested=None,
        tenant_id="default",
        embedding_missing=1,
    )
    defaults.update(overrides)
    conn.execute(
        """INSERT INTO facts
           (id, entity, relation, value_type, value_v, source, timestamp,
            valid_until, confidence, scope, hlc, received_from, attested_key_id,
            garden_id, attested, tenant_id, embedding_missing)
           VALUES (:id,:entity,:relation,:value_type,:value_v,:source,:timestamp,
                   :valid_until,:confidence,:scope,:hlc,:received_from,:attested_key_id,
                   :garden_id,:attested,:tenant_id,:embedding_missing)""",
        defaults,
    )
    conn.commit()
    return str(defaults["id"])


# ---------------------------------------------------------------------------
# StubEmbeddingModel unit tests
# ---------------------------------------------------------------------------


class TestStubEmbeddingModel:
    def test_dimension(self) -> None:
        model = StubEmbeddingModel(dim=8)
        assert model.dimension == 8

    def test_model_id(self) -> None:
        model = StubEmbeddingModel(model_id="stub-test")
        assert model.model_id == "stub-test"

    def test_embed_returns_unit_vector(self) -> None:
        model = StubEmbeddingModel(dim=16)
        vecs = model.embed(["hello world"])
        assert len(vecs) == 1
        vec = vecs[0]
        assert len(vec) == 16
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_embed_deterministic(self) -> None:
        model = StubEmbeddingModel(dim=8)
        a = model.embed(["alice memory:role CEO"])
        b = model.embed(["alice memory:role CEO"])
        assert a == b

    def test_embed_different_texts_differ(self) -> None:
        model = StubEmbeddingModel(dim=8)
        a = model.embed(["alice memory:role CEO"])
        b = model.embed(["bob roadmap:status done"])
        assert a != b

    def test_embed_batch(self) -> None:
        model = StubEmbeddingModel(dim=4)
        vecs = model.embed(["text one", "text two", "text three"])
        assert len(vecs) == 3
        for v in vecs:
            assert len(v) == 4


# ---------------------------------------------------------------------------
# compose_triple_text
# ---------------------------------------------------------------------------


class TestComposeTripleText:
    def test_string_type(self) -> None:
        text = compose_triple_text("user:alice", "memory:role", "string", "CEO")
        assert "alice" in text
        assert "memory:role" in text
        assert "CEO" in text

    def test_ref_type_uses_last_segment(self) -> None:
        text = compose_triple_text("user:alice", "org:member-of", "ref", "stigmem://company/acme")
        assert "acme" in text
        assert "stigmem://company/acme" not in text

    def test_null_value(self) -> None:
        text = compose_triple_text("user:alice", "memory:role", "null", "")
        assert "alice" in text


# ---------------------------------------------------------------------------
# l2_normalize
# ---------------------------------------------------------------------------


class TestL2Normalize:
    def test_unit_vector_unchanged(self) -> None:
        vec = [1.0, 0.0, 0.0]
        result = l2_normalize(vec)
        assert abs(result[0] - 1.0) < 1e-9

    def test_normalizes_correctly(self) -> None:
        vec = [3.0, 4.0]
        result = l2_normalize(vec)
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-9

    def test_zero_vector_returned_unchanged(self) -> None:
        vec = [0.0, 0.0, 0.0]
        result = l2_normalize(vec)
        assert result == vec


# ---------------------------------------------------------------------------
# Mixed-model safety (EmbeddingModelMismatch)
# ---------------------------------------------------------------------------


class TestEmbeddingModelMismatch:
    def test_first_registration_succeeds(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)
        check_or_register_model(conn, "nomic-embed-text-v1.5", 768)
        conn.commit()
        row = conn.execute("SELECT * FROM embedding_meta WHERE id=1").fetchone()
        assert row["model_id"] == "nomic-embed-text-v1.5"
        assert row["dimension"] == 768
        conn.close()

    def test_same_model_ok(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)
        check_or_register_model(conn, "nomic-embed-text-v1.5", 768)
        conn.commit()
        # Second call with same values must not raise
        check_or_register_model(conn, "nomic-embed-text-v1.5", 768)
        conn.close()

    def test_different_model_id_raises(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)
        check_or_register_model(conn, "nomic-embed-text-v1.5", 768)
        conn.commit()
        with pytest.raises(EmbeddingModelMismatch, match="mismatch"):
            check_or_register_model(conn, "text-embedding-3-small", 768)
        conn.close()

    def test_different_dimension_raises(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)
        check_or_register_model(conn, "nomic-embed-text-v1.5", 768)
        conn.commit()
        with pytest.raises(EmbeddingModelMismatch, match="mismatch"):
            check_or_register_model(conn, "nomic-embed-text-v1.5", 256)
        conn.close()


# ---------------------------------------------------------------------------
# embed_and_store_fact + backfill (sqlite-vec required for full path)
# ---------------------------------------------------------------------------


class TestEmbedAndStore:
    def test_embed_on_write_updates_flag(self, tmp_path: Path) -> None:
        """embed_and_store_fact sets embedding_missing=0 and inserts into vec_facts."""
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)

        vec_available = _load_sqlite_vec(conn, 4)
        if not vec_available:
            pytest.skip("sqlite-vec not installed")

        fact_id = _insert_fact(conn)

        model = StubEmbeddingModel(dim=4)
        check_or_register_model(conn, model.model_id, model.dimension)
        embed_and_store_fact(fact_id, "user:alice", "memory:role", "string", "CEO", conn, model)
        conn.commit()

        row = conn.execute("SELECT embedding_missing FROM facts WHERE id=?", (fact_id,)).fetchone()
        assert row["embedding_missing"] == 0

        vec_row = conn.execute("SELECT * FROM vec_facts WHERE fact_id=?", (fact_id,)).fetchone()
        assert vec_row is not None
        conn.close()

    def test_backfill_embeds_missing_facts(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)

        vec_available = _load_sqlite_vec(conn, 4)
        if not vec_available:
            pytest.skip("sqlite-vec not installed")

        ids = [_insert_fact(conn, entity=f"user:person{i}", embedding_missing=1) for i in range(5)]

        model = StubEmbeddingModel(dim=4)
        check_or_register_model(conn, model.model_id, model.dimension)
        count = backfill_missing_embeddings(conn, model, limit=10)
        conn.commit()

        assert count == 5
        for fid in ids:
            row = conn.execute("SELECT embedding_missing FROM facts WHERE id=?", (fid,)).fetchone()
            assert row["embedding_missing"] == 0
        conn.close()

    def test_backfill_skips_low_confidence(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)

        vec_available = _load_sqlite_vec(conn, 4)
        if not vec_available:
            pytest.skip("sqlite-vec not installed")

        dead_id = _insert_fact(conn, confidence=0.05, embedding_missing=1)
        _insert_fact(conn, entity="user:bob", confidence=1.0, embedding_missing=1)

        model = StubEmbeddingModel(dim=4)
        check_or_register_model(conn, model.model_id, model.dimension)
        count = backfill_missing_embeddings(conn, model, limit=10)
        conn.commit()

        assert count == 1
        dead_row = conn.execute(
            "SELECT embedding_missing FROM facts WHERE id=?", (dead_id,)
        ).fetchone()
        # Low-confidence fact was not embedded; flag stays 1
        assert dead_row["embedding_missing"] == 1
        conn.close()


# ---------------------------------------------------------------------------
# vector_search primitive
# ---------------------------------------------------------------------------


class TestVectorSearch:
    def test_returns_closest_fact(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)

        vec_available = _load_sqlite_vec(conn, 4)
        if not vec_available:
            pytest.skip("sqlite-vec not installed")

        model = StubEmbeddingModel(dim=4)
        check_or_register_model(conn, model.model_id, model.dimension)

        texts = [
            ("user:alice", "memory:role", "string", "CEO"),
            ("user:bob", "roadmap:status", "string", "done"),
        ]
        fact_ids: list[str] = []
        for entity, relation, vtype, val in texts:
            fid = _insert_fact(
                conn, entity=entity, relation=relation, value_v=val, embedding_missing=1
            )
            fact_ids.append(fid)
            embed_and_store_fact(fid, entity, relation, vtype, val, conn, model)
        conn.commit()

        query_text = compose_triple_text("user:alice", "memory:role", "string", "CEO")
        query_vec = model.embed([query_text])[0]
        results = vector_search(query_vec, k=5, conn=conn)

        assert len(results) >= 1
        top_id, top_sim = results[0]
        assert top_id.id == fact_ids[0]
        assert 0.0 <= top_sim <= 1.0

    def test_scope_filter(self, tmp_path: Path) -> None:
        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)
        conn = _open_plain(db_file)

        vec_available = _load_sqlite_vec(conn, 4)
        if not vec_available:
            pytest.skip("sqlite-vec not installed")

        model = StubEmbeddingModel(dim=4)
        check_or_register_model(conn, model.model_id, model.dimension)

        local_id = _insert_fact(conn, entity="user:alice", scope="local", embedding_missing=1)
        team_id = _insert_fact(conn, entity="user:bob", scope="team", embedding_missing=1)
        for fid, entity, _scope in [
            (local_id, "user:alice", "local"),
            (team_id, "user:bob", "team"),
        ]:
            embed_and_store_fact(fid, entity, "memory:role", "string", "CEO", conn, model)
        conn.commit()

        query_vec = model.embed(["any query"])[0]
        results = vector_search(query_vec, k=10, scope_filter="local", conn=conn)
        result_ids = {r.id for r, _ in results}
        assert local_id in result_ids
        assert team_id not in result_ids


# ---------------------------------------------------------------------------
# entity_edges write path (via HTTP; does not need sqlite-vec)
# ---------------------------------------------------------------------------


class TestEntityEdges:
    def test_ref_fact_creates_edge(self, client: object) -> None:
        from fastapi.testclient import TestClient

        c: TestClient = client  # type: ignore[assignment]
        r = c.post(
            "/v1/facts",
            json={
                "entity": "user:alice",
                "relation": "org:member-of",
                "value": {"type": "ref", "v": "stigmem://org/acme"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        fact_id = r.json()["id"]

        # Verify edge was written to DB
        import stigmem_node.db as db_mod

        with db_mod.db() as conn:
            edge = conn.execute("SELECT * FROM entity_edges WHERE id=?", (fact_id,)).fetchone()

        assert edge is not None
        assert edge["subject"] == "user:alice"
        assert edge["object"] == "stigmem://org/acme"
        assert edge["relation"] == "org:member-of"
        assert edge["confidence"] == pytest.approx(1.0)

    def test_non_ref_fact_no_edge(self, client: object) -> None:
        from fastapi.testclient import TestClient

        c: TestClient = client  # type: ignore[assignment]
        r = c.post(
            "/v1/facts",
            json={
                "entity": "user:alice",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        fact_id = r.json()["id"]

        import stigmem_node.db as db_mod

        with db_mod.db() as conn:
            edge = conn.execute("SELECT * FROM entity_edges WHERE id=?", (fact_id,)).fetchone()

        assert edge is None

    def test_ref_with_non_uri_value_no_edge(self, client: object) -> None:
        """A ref value that is not a valid URI must not create an entity_edges row."""
        from fastapi.testclient import TestClient

        c: TestClient = client  # type: ignore[assignment]
        r = c.post(
            "/v1/facts",
            json={
                "entity": "user:alice",
                "relation": "org:link",
                "value": {"type": "ref", "v": "not-a-uri"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        fact_id = r.json()["id"]

        import stigmem_node.db as db_mod

        with db_mod.db() as conn:
            edge = conn.execute("SELECT * FROM entity_edges WHERE id=?", (fact_id,)).fetchone()

        assert edge is None
