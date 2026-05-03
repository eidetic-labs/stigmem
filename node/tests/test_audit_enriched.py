"""Tests for Track C / C3 — end-to-end audit log join (principal → attested-source → fact-id)."""

from __future__ import annotations

import base64
import csv
import io

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi.testclient import TestClient

from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations
from stigmem_node.main import create_app
import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.routes.facts as facts_mod
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
from stigmem_node.settings import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return pub_b64, priv_b64


def _sign_fact(priv_b64: str, entity: str, relation: str, value_type: str, value_v: str, source: str) -> str:
    raw = base64.urlsafe_b64decode(priv_b64 + "=" * (-len(priv_b64) % 4))
    privkey = Ed25519PrivateKey.from_private_bytes(raw)
    msg = f"{entity}\n{relation}\n{value_type}\n{value_v}\n{source}".encode("utf-8")
    return base64.urlsafe_b64encode(privkey.sign(msg)).decode().rstrip("=")


def _patch(s):
    settings_module.settings = s  # type: ignore[assignment]
    auth_mod.settings = s  # type: ignore[assignment]
    db_mod.settings = s  # type: ignore[assignment]
    facts_mod.settings = s  # type: ignore[assignment]
    wk_mod.settings = s  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def authed_db(tmp_path):
    db_file = str(tmp_path) + "/test_c3.db"
    apply_migrations(db_path=db_file)
    return db_file


@pytest.fixture()
def client_entity(authed_db):
    original = settings_module.settings
    s = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
    _patch(s)

    entity = "stigmem://test/agent/alice"
    raw_key = create_api_key(entity, ["read", "write"])
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, entity, raw_key

    _patch(original)


_FACT = {
    "entity": "stigmem://test/user/bob",
    "relation": "memory:role",
    "value": {"type": "string", "v": "engineer"},
    "source": "stigmem://test/agent/alice",
    "confidence": 1.0,
    "scope": "company",
}


# ---------------------------------------------------------------------------
# Enriched single-fact audit trail
# ---------------------------------------------------------------------------


class TestEnrichedSingleFactAudit:
    def test_unattested_fact_has_null_key_join_fields(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        fact_r = client.post("/v1/facts", json=_FACT, headers=hdr)
        fact_id = fact_r.json()["id"]

        r = client.get(f"/v1/audit/facts/{fact_id}", headers=hdr)
        assert r.status_code == 200
        entries = r.json()
        assert len(entries) == 1
        e = entries[0]
        assert e["entity_uri"] == entity
        assert e["attested_key_id"] is None
        assert e["attested_key_entity_uri"] is None
        assert e["attested_key_description"] is None
        # fact join fields present
        assert e["fact_entity"] == _FACT["entity"]
        assert e["fact_relation"] == _FACT["relation"]
        assert e["fact_value_type"] == _FACT["value"]["type"]
        assert e["fact_value_v"] == _FACT["value"]["v"]
        assert e["fact_scope"] == _FACT["scope"]

    def test_attested_fact_includes_key_join_fields(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub, "description": "alice-signing-key"},
            headers=hdr,
        )
        key_id = reg.json()["id"]

        sig = _sign_fact(priv, _FACT["entity"], _FACT["relation"], _FACT["value"]["type"], _FACT["value"]["v"], _FACT["source"])
        fact_r = client.post(
            "/v1/facts",
            json={**_FACT, "attestation": {"key_id": key_id, "signature": sig}},
            headers=hdr,
        )
        fact_id = fact_r.json()["id"]

        r = client.get(f"/v1/audit/facts/{fact_id}", headers=hdr)
        assert r.status_code == 200
        e = r.json()[0]

        # principal
        assert e["entity_uri"] == entity
        # attested key join
        assert e["attested_key_id"] == key_id
        assert e["attested_key_entity_uri"] == entity
        assert e["attested_key_description"] == "alice-signing-key"
        # fact join
        assert e["fact_entity"] == _FACT["entity"]
        assert e["fact_relation"] == _FACT["relation"]
        assert e["fact_scope"] == _FACT["scope"]

    def test_404_for_unknown_fact(self, client_entity) -> None:
        client, _entity, raw_key = client_entity
        r = client.get("/v1/audit/facts/no-such-fact", headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Enriched paginated audit query
# ---------------------------------------------------------------------------


class TestEnrichedAuditQuery:
    def test_returns_enriched_entries(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        fact_r = client.post("/v1/facts", json=_FACT, headers=hdr)
        fact_id = fact_r.json()["id"]

        r = client.get(f"/v1/audit?fact_id={fact_id}", headers=hdr)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        e = data["entries"][0]
        assert e["entity_uri"] == entity
        assert e["fact_entity"] == _FACT["entity"]
        assert e["fact_relation"] == _FACT["relation"]
        assert e["fact_value_type"] == _FACT["value"]["type"]
        assert e["fact_value_v"] == _FACT["value"]["v"]
        assert e["fact_scope"] == _FACT["scope"]

    def test_filter_by_entity_uri(self, authed_db) -> None:
        original = settings_module.settings
        s = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
        _patch(s)

        key_a = create_api_key("stigmem://test/agent/alice", ["read", "write"])
        key_b = create_api_key("stigmem://test/agent/bob", ["read", "write"])
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            c.post("/v1/facts", json={**_FACT, "relation": "a:rel"}, headers={"Authorization": f"Bearer {key_a}"})
            c.post("/v1/facts", json={**_FACT, "relation": "b:rel"}, headers={"Authorization": f"Bearer {key_b}"})

            r = c.get("/v1/audit?entity_uri=stigmem://test/agent/alice", headers={"Authorization": f"Bearer {key_a}"})
            assert r.status_code == 200
            entries = r.json()["entries"]
            assert all(e["entity_uri"] == "stigmem://test/agent/alice" for e in entries)
            assert len(entries) == 1

        _patch(original)

    def test_filter_attested_true(self, client_entity) -> None:
        client, _entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        pub, priv = _gen_keypair()
        reg = client.post("/v1/auth/agent-keys", json={"public_key": pub}, headers=hdr)
        key_id = reg.json()["id"]

        sig = _sign_fact(priv, _FACT["entity"], _FACT["relation"], _FACT["value"]["type"], _FACT["value"]["v"], _FACT["source"])
        client.post("/v1/facts", json={**_FACT, "attestation": {"key_id": key_id, "signature": sig}}, headers=hdr)
        client.post("/v1/facts", json={**_FACT, "relation": "unattested:rel"}, headers=hdr)

        attested = client.get("/v1/audit?attested=true", headers=hdr).json()["entries"]
        unattested = client.get("/v1/audit?attested=false", headers=hdr).json()["entries"]

        assert all(e["attested_key_id"] is not None for e in attested)
        assert all(e["attested_key_id"] is None for e in unattested)
        assert all(e["attested_key_entity_uri"] is not None for e in attested)

    def test_pagination_cursor(self, client_entity) -> None:
        client, _entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        # Write 3 facts
        for i in range(3):
            client.post("/v1/facts", json={**_FACT, "relation": f"p:rel{i}"}, headers=hdr)

        page1 = client.get("/v1/audit?limit=2", headers=hdr).json()
        assert len(page1["entries"]) == 2
        assert page1["cursor"] is not None

        page2 = client.get(f"/v1/audit?limit=2&cursor={page1['cursor']}", headers=hdr).json()
        assert len(page2["entries"]) >= 1

        # no overlap
        ids1 = {e["id"] for e in page1["entries"]}
        ids2 = {e["id"] for e in page2["entries"]}
        assert ids1.isdisjoint(ids2)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestAuditCsvExport:
    def test_export_returns_csv_with_correct_headers(self, client_entity) -> None:
        client, _entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        client.post("/v1/facts", json=_FACT, headers=hdr)

        r = client.get("/v1/audit/export", headers=hdr)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

        reader = csv.DictReader(io.StringIO(r.text))
        expected = {
            "id", "fact_id", "event_type",
            "principal_entity_uri", "principal_oidc_sub",
            "source",
            "attested_key_id", "attested_key_entity_uri", "attested_key_description",
            "fact_entity", "fact_relation", "fact_value_type", "fact_value_v", "fact_scope",
            "ts",
        }
        assert set(reader.fieldnames or []) == expected  # type: ignore[arg-type]

    def test_export_contains_fact_join_data(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        fact_r = client.post("/v1/facts", json=_FACT, headers=hdr)
        fact_id = fact_r.json()["id"]

        r = client.get(f"/v1/audit/export?fact_id={fact_id}", headers=hdr)
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == 1
        row = rows[0]
        assert row["principal_entity_uri"] == entity
        assert row["fact_entity"] == _FACT["entity"]
        assert row["fact_relation"] == _FACT["relation"]
        assert row["fact_scope"] == _FACT["scope"]
        assert row["fact_value_v"] == _FACT["value"]["v"]

    def test_export_attested_fact_includes_key_info(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub, "description": "export-key"},
            headers=hdr,
        )
        key_id = reg.json()["id"]

        sig = _sign_fact(priv, _FACT["entity"], _FACT["relation"], _FACT["value"]["type"], _FACT["value"]["v"], _FACT["source"])
        fact_r = client.post(
            "/v1/facts",
            json={**_FACT, "attestation": {"key_id": key_id, "signature": sig}},
            headers=hdr,
        )
        fact_id = fact_r.json()["id"]

        r = client.get(f"/v1/audit/export?fact_id={fact_id}", headers=hdr)
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == 1
        row = rows[0]
        assert row["attested_key_id"] == key_id
        assert row["attested_key_entity_uri"] == entity
        assert row["attested_key_description"] == "export-key"

    def test_export_requires_auth(self, authed_db) -> None:
        original = settings_module.settings
        s = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
        _patch(s)
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            r = c.get("/v1/audit/export")
            assert r.status_code == 401

        _patch(original)

    def test_export_respects_filter(self, client_entity) -> None:
        client, entity, raw_key = client_entity
        hdr = {"Authorization": f"Bearer {raw_key}"}

        client.post("/v1/facts", json={**_FACT, "source": "src://a"}, headers=hdr)
        client.post("/v1/facts", json={**_FACT, "relation": "other:rel", "source": "src://b"}, headers=hdr)

        r = client.get("/v1/audit/export?source=src://a", headers=hdr)
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert len(rows) == 1
        assert rows[0]["source"] == "src://a"
