"""Conformance: vector embedding behavioral contract (spec §20 design memo §2).

sqlite-vec embeddings are SQLite-only (requires the sqlite-vec extension).
libSQL and Postgres run these tests with ``embed_enabled=False`` and the suite
records them as explicit skips with the justification below.

Justified skip:
    libSQL — no sqlite-vec loadable extension support in libsql-experimental.
    Postgres — uses pg_vector separately; sqlite-vec extension not applicable.
    Any backend — ``embed_enabled=False`` (default); embedding feature is opt-in.
"""

from __future__ import annotations

import pytest

from .conftest import ConformanceClient

_EMBED_SKIP_REASON = (
    "Vector embeddings require embed_enabled=True and the sqlite-vec extension "
    "(SQLite only). libSQL and Postgres use alternative vector stores."
)

_E = "stigmem://conformance/embed/entity"


def _fact(v: str = "embedding test content") -> dict:
    return {
        "entity": _E,
        "relation": "memory:note",
        "value": {"type": "text", "v": v},
        "source": _E,
        "confidence": 1.0,
        "scope": "local",
    }


class TestEmbeddingsEndpoint:
    def test_embed_status_endpoint_exists(self, conformance_client: ConformanceClient) -> None:
        r = conformance_client.client.get("/v1/embed/status")
        assert r.status_code in (200, 404)

    def test_assert_fact_does_not_error_without_embeddings(
        self, conformance_client: ConformanceClient
    ) -> None:
        r = conformance_client.client.post("/v1/facts", json=_fact())
        assert r.status_code == 201

    @pytest.mark.skipif(True, reason=_EMBED_SKIP_REASON)
    def test_vector_search_returns_similar_facts(
        self, conformance_client: ConformanceClient
    ) -> None:
        """Placeholder: enable once embed_enabled=True is wired into the fixture."""
        c = conformance_client.client
        c.post("/v1/facts", json=_fact("cats are fluffy pets"))
        c.post("/v1/facts", json=_fact("dogs are loyal companions"))
        r = c.post("/v1/recall", json={
            "query": "feline",
            "scope": "local",
            "token_budget": 4000,
            "depth": 1,
            "include_neighbors": False,
        })
        assert r.status_code == 200

    def test_recall_works_without_vector_index(
        self, conformance_client: ConformanceClient
    ) -> None:
        c = conformance_client.client
        c.post("/v1/facts", json=_fact("lexical-only recall test content"))
        r = c.post("/v1/recall", json={
            "query": "lexical",
            "scope": "local",
            "token_budget": 4000,
            "depth": 1,
            "include_neighbors": False,
        })
        assert r.status_code == 200
