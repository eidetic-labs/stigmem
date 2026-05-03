"""Tests for the fuzzy entity resolver — spec §2.6 Phase 6.

Covers:
  - fuzzy_resolver.register_alias and resolve_entity (unit, via tmp_db)
  - POST /v1/aliases  — create user-defined alias
  - GET  /v1/aliases  — list aliases (kind / canonical_uri filter)
  - DELETE /v1/aliases/:raw_uri — remove user alias, protect migration alias
  - Ingest path: fact stored with canonical URI after alias resolution
  - Query path: alias-written fact discoverable under the canonical entity
  - entity_resolver.resolve_entity Layer 2 picks up registered alias (integration)
  - GET /v1/entities/resolve Layer 2 hit
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from stigmem_node.db import apply_migrations
from stigmem_node.fuzzy_resolver import register_alias, resolve_entity


# ---------------------------------------------------------------------------
# Unit tests — fuzzy_resolver module
# ---------------------------------------------------------------------------


class TestRegisterAlias:
    def test_basic_register(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        result = register_alias(conn, "user:alice", "user:a.smith")
        conn.commit()
        conn.close()

        assert result["raw_uri"] == "user:alice"
        assert result["canonical_uri"] == "user:a.smith"
        assert result["kind"] == "user"

    def test_normalises_both_uris_before_storage(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        result = register_alias(conn, "user:Alice", "user:A.Smith")
        conn.commit()
        conn.close()

        assert result["raw_uri"] == "user:alice"
        assert result["canonical_uri"] == "user:a.smith"

    def test_formal_uri_alias(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        result = register_alias(
            conn,
            "stigmem://company.example/user/ALICE",
            "stigmem://company.example/user/a.smith",
        )
        conn.commit()
        conn.close()

        assert result["raw_uri"] == "stigmem://company.example/user/alice"
        assert result["canonical_uri"] == "stigmem://company.example/user/a.smith"

    def test_rejects_identical_after_normalisation(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        with pytest.raises(ValueError, match="must differ"):
            register_alias(conn, "user:alice", "user:Alice")
        conn.close()

    def test_rejects_empty_raw_uri(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        with pytest.raises(ValueError):
            register_alias(conn, "   ", "user:a.smith")
        conn.close()

    def test_replace_on_conflict(self, tmp_db: str) -> None:
        """INSERT OR REPLACE lets a second call update the canonical target."""
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        register_alias(conn, "user:alice", "user:a.smith")
        register_alias(conn, "user:alice", "user:alice.smith")
        conn.commit()
        row = conn.execute(
            "SELECT canonical_uri FROM entity_aliases WHERE raw_uri = ?", ("user:alice",)
        ).fetchone()
        conn.close()
        assert row["canonical_uri"] == "user:alice.smith"


class TestResolveEntity:
    def test_resolves_registered_alias(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        register_alias(conn, "user:alice", "user:a.smith")
        conn.commit()

        result = resolve_entity(conn, "user:alice")
        conn.close()
        assert result == "user:a.smith"

    def test_passthrough_when_no_alias(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        result = resolve_entity(conn, "user:unknown")
        conn.close()
        assert result == "user:unknown"

    def test_layer1_then_layer2(self, tmp_db: str) -> None:
        """Input is not yet normalised; caller normalises first, then resolves."""
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        register_alias(conn, "user:alice", "user:a.smith")
        conn.commit()

        from stigmem_node.entity_normalizer import normalize_entity_uri
        normalised = normalize_entity_uri("user:Alice")  # Layer 1
        result = resolve_entity(conn, normalised)         # Layer 2
        conn.close()
        assert result == "user:a.smith"


# ---------------------------------------------------------------------------
# Integration tests — /v1/aliases API
# ---------------------------------------------------------------------------


class TestPostAlias:
    def test_creates_alias(self, client: TestClient) -> None:
        r = client.post(
            "/v1/aliases",
            json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["raw_uri"] == "user:alice"
        assert body["canonical_uri"] == "user:a.smith"
        assert body["kind"] == "user"

    def test_normalises_uris_before_store(self, client: TestClient) -> None:
        r = client.post(
            "/v1/aliases",
            json={"raw_uri": "user:Alice", "canonical_uri": "user:A.Smith"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["raw_uri"] == "user:alice"
        assert body["canonical_uri"] == "user:a.smith"

    def test_rejects_identical_uris(self, client: TestClient) -> None:
        r = client.post(
            "/v1/aliases",
            json={"raw_uri": "user:alice", "canonical_uri": "user:alice"},
        )
        assert r.status_code == 400

    def test_idempotent_on_repeat(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        r2 = client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        assert r2.status_code == 201


class TestGetAliases:
    def test_lists_all_aliases(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        client.post("/v1/aliases", json={"raw_uri": "user:bob", "canonical_uri": "user:b.jones"})
        r = client.get("/v1/aliases")
        assert r.status_code == 200
        aliases = {a["raw_uri"] for a in r.json()}
        assert "user:alice" in aliases
        assert "user:bob" in aliases

    def test_filter_by_kind(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        r = client.get("/v1/aliases", params={"kind": "user"})
        assert r.status_code == 200
        assert all(a["kind"] == "user" for a in r.json())

    def test_filter_by_canonical_uri(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        client.post("/v1/aliases", json={"raw_uri": "user:ali", "canonical_uri": "user:a.smith"})
        client.post("/v1/aliases", json={"raw_uri": "user:bob", "canonical_uri": "user:b.jones"})
        r = client.get("/v1/aliases", params={"canonical_uri": "user:a.smith"})
        assert r.status_code == 200
        raws = {a["raw_uri"] for a in r.json()}
        assert raws == {"user:alice", "user:ali"}

    def test_invalid_kind_returns_400(self, client: TestClient) -> None:
        r = client.get("/v1/aliases", params={"kind": "bogus"})
        assert r.status_code == 400


class TestDeleteAlias:
    def test_deletes_user_alias(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        r = client.delete("/v1/aliases/user:alice")
        assert r.status_code == 204
        # Confirm gone
        r2 = client.get("/v1/aliases", params={"kind": "user"})
        assert not any(a["raw_uri"] == "user:alice" for a in r2.json())

    def test_404_on_missing_alias(self, client: TestClient) -> None:
        r = client.delete("/v1/aliases/user:nonexistent")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Ingest-path integration tests
# ---------------------------------------------------------------------------


_FACT_BASE = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "engineer"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "company",
}


class TestIngestAliasResolution:
    def test_fact_stored_as_canonical_after_alias(self, client: TestClient) -> None:
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        r = client.post("/v1/facts", json=_FACT_BASE)
        assert r.status_code == 201
        assert r.json()["entity"] == "user:a.smith"

    def test_fact_stored_as_normalized_when_no_alias(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={**_FACT_BASE, "entity": "user:Bob"},
        )
        assert r.status_code == 201
        assert r.json()["entity"] == "user:bob"

    def test_query_canonical_finds_aliased_fact(self, client: TestClient) -> None:
        """Fact written via alias stored as canonical; querying canonical finds it."""
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        client.post("/v1/facts", json=_FACT_BASE)

        r = client.get("/v1/facts", params={"entity": "user:a.smith"})
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert any(f["entity"] == "user:a.smith" for f in facts)

    def test_alias_registered_after_write_still_queryable(self, client: TestClient) -> None:
        """Pre-alias fact stored under raw URI; alias registered afterwards.
        Query path JOIN on entity_aliases covers this case (backward compat)."""
        client.post("/v1/facts", json=_FACT_BASE)  # stored as user:alice (no alias yet)
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})

        # Query for canonical finds the pre-alias fact via the JOIN
        r = client.get("/v1/facts", params={"entity": "user:a.smith"})
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert any(f["entity"] == "user:alice" for f in facts)

    def test_alias_resolution_on_source_field(self, client: TestClient) -> None:
        """Alias resolution applies to source as well as entity on ingest."""
        client.post("/v1/aliases", json={"raw_uri": "agent:assistant", "canonical_uri": "agent:bot"})
        r = client.post("/v1/facts", json=_FACT_BASE)
        assert r.status_code == 201
        assert r.json()["source"] == "agent:bot"

    def test_uppercase_input_normalised_then_alias_resolved(self, client: TestClient) -> None:
        """3-layer end-to-end: Layer 1 collapses case, Layer 2 resolves alias."""
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})
        r = client.post("/v1/facts", json={**_FACT_BASE, "entity": "user:Alice"})
        assert r.status_code == 201
        assert r.json()["entity"] == "user:a.smith"


# ---------------------------------------------------------------------------
# entity_resolver Layer 2 integration tests
# ---------------------------------------------------------------------------


class TestResolverEndpointLayer2:
    def test_layer2_hit_on_resolve_endpoint(self, client: TestClient) -> None:
        """GET /v1/entities/resolve returns layer2_match when alias is registered."""
        # Seed a fact so user:a.smith exists in the graph (Layer 1 match possible)
        client.post(
            "/v1/facts",
            json={
                "entity": "user:a.smith",
                "relation": "memory:role",
                "value": {"type": "string", "v": "engineer"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        client.post("/v1/aliases", json={"raw_uri": "user:alice", "canonical_uri": "user:a.smith"})

        r = client.get("/v1/entities/resolve", params={"uri": "user:alice"})
        assert r.status_code == 200
        body = r.json()
        # Alias lookup wins (layer2_match present and best == canonical target)
        assert body["layer2_match"] == "user:a.smith"
        assert body["best"] == "user:a.smith"
        assert body["resolution_layer"] == 2
