"""Tests for Track C / C1 — per-agent keypair registration and attestation enforcement."""

from __future__ import annotations

import base64
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.routes.facts as facts_mod
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
from stigmem_node.main import create_app

create_api_key = auth_mod.create_api_key
apply_migrations = db_mod.apply_migrations
Settings = settings_module.Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(
            priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        )
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return pub_b64, priv_b64


def _sign_fact(
    priv_b64: str, entity: str, relation: str, value_type: str, value_v: str, source: str
) -> str:
    raw = base64.urlsafe_b64decode(priv_b64 + "=" * (-len(priv_b64) % 4))
    privkey = Ed25519PrivateKey.from_private_bytes(raw)
    msg = f"{entity}\n{relation}\n{value_type}\n{value_v}\n{source}".encode()
    return base64.urlsafe_b64encode(privkey.sign(msg)).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def authed_db(tmp_path: object) -> str:
    db_file = str(tmp_path) + "/test_ak.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)
    return db_file


def _patch(s):
    settings_module.settings = s  # type: ignore[assignment]
    auth_mod.settings = s  # type: ignore[assignment]
    db_mod.settings = s  # type: ignore[assignment]
    facts_mod.settings = s  # type: ignore[assignment]
    wk_mod.settings = s  # type: ignore[assignment]


@pytest.fixture()
def authed_client_entity(authed_db: str):
    """Client with auth enabled; yields (client, entity_uri, raw_key)."""
    original = settings_module.settings
    test_settings = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
    _patch(test_settings)

    entity = "stigmem://company.test/agent/cto"
    raw_key = create_api_key(entity, ["read", "write"])
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, entity, raw_key

    _patch(original)


@pytest.fixture()
def attest_required_client(authed_db: str):
    """Client with auth + attestation_required=True; yields (client, entity_uri, raw_key)."""
    original = settings_module.settings
    test_settings = Settings(
        db_path=authed_db, auth_required=True, attestation_required=True, node_url="http://testnode"
    )
    _patch(test_settings)

    entity = "stigmem://company.test/agent/cto"
    raw_key = create_api_key(entity, ["read", "write"])
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, entity, raw_key

    _patch(original)


# ---------------------------------------------------------------------------
# Key registration
# ---------------------------------------------------------------------------


class TestAgentKeyRegistration:
    def test_register_returns_201(self, authed_client_entity) -> None:
        client, entity, raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        r = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub, "description": "CTO key"},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["id"]
        assert body["entity_uri"] == entity
        assert body["public_key"] == pub
        assert body["status"] == "active"
        assert body["description"] == "CTO key"

    def test_register_without_description(self, authed_client_entity) -> None:
        client, entity, raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        r = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 201
        assert r.json()["description"] is None

    def test_register_bad_key_returns_400(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        r = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": "notavalidkey"},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 400

    def test_register_requires_auth(self, authed_client_entity) -> None:
        client, _entity, _raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        r = client.post("/v1/auth/agent-keys", json={"public_key": pub})
        assert r.status_code == 401

    def test_list_keys_empty(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        r = client.get("/v1/auth/agent-keys", headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 200
        assert r.json() == []

    def test_list_keys_after_register(self, authed_client_entity) -> None:
        client, entity, raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        r = client.get("/v1/auth/agent-keys", headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 200
        keys = r.json()
        assert len(keys) == 1
        assert keys[0]["entity_uri"] == entity
        assert keys[0]["public_key"] == pub


class TestAgentKeyRevocation:
    def test_revoke_own_key(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        key_id = reg.json()["id"]

        r = client.delete(
            f"/v1/auth/agent-keys/{key_id}",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 204

        # key still appears in list but as revoked
        listing = client.get("/v1/auth/agent-keys", headers={"Authorization": f"Bearer {raw_key}"})
        assert listing.json()[0]["status"] == "revoked"

    def test_revoke_already_revoked_returns_409(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        pub, _ = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        key_id = reg.json()["id"]
        client.delete(
            f"/v1/auth/agent-keys/{key_id}", headers={"Authorization": f"Bearer {raw_key}"}
        )
        r = client.delete(
            f"/v1/auth/agent-keys/{key_id}", headers={"Authorization": f"Bearer {raw_key}"}
        )
        assert r.status_code == 409

    def test_revoke_other_entity_key_returns_403(self, authed_db) -> None:
        original = settings_module.settings
        test_settings = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
        _patch(test_settings)

        key_a = create_api_key("stigmem://company.test/agent/alice", ["read", "write"])
        key_b = create_api_key("stigmem://company.test/agent/bob", ["read", "write"])
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            pub, _ = _gen_keypair()
            reg = c.post(
                "/v1/auth/agent-keys",
                json={"public_key": pub},
                headers={"Authorization": f"Bearer {key_a}"},
            )
            alice_key_id = reg.json()["id"]

            r = c.delete(
                f"/v1/auth/agent-keys/{alice_key_id}",
                headers={"Authorization": f"Bearer {key_b}"},
            )
            assert r.status_code == 403

        _patch(original)

    def test_revoke_unknown_key_returns_404(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        r = client.delete(
            f"/v1/auth/agent-keys/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Attestation enforcement on fact assertion
# ---------------------------------------------------------------------------


_FACT = {
    "entity": "stigmem://company.test/user/alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "stigmem://company.test/agent/cto",
    "confidence": 1.0,
    "scope": "company",
}


class TestAttestationOnAssert:
    def test_assert_without_attestation_no_requirement(self, authed_client_entity) -> None:
        """Without attestation_required, unsigned facts are accepted; attested_key_id is null."""
        client, _entity, raw_key = authed_client_entity
        r = client.post(
            "/v1/facts",
            json=_FACT,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 201
        assert r.json()["attested_key_id"] is None

    def test_assert_with_valid_attestation(self, authed_client_entity) -> None:
        """Valid attestation token → attested_key_id populated in response and fact."""
        client, _entity, raw_key = authed_client_entity
        pub, priv = _gen_keypair()

        # Register the key
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]

        # Sign the fact
        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact_with_attest = {**_FACT, "attestation": {"key_id": agent_key_id, "signature": sig}}
        r = client.post(
            "/v1/facts",
            json=fact_with_attest,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["attested_key_id"] == agent_key_id

    def test_assert_with_wrong_signature_returns_400(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]

        # Sign a DIFFERENT message
        _, other_priv = _gen_keypair()
        bad_sig = _sign_fact(
            other_priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact_with_attest = {**_FACT, "attestation": {"key_id": agent_key_id, "signature": bad_sig}}
        r = client.post(
            "/v1/facts",
            json=fact_with_attest,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 400
        assert "signature" in r.json()["detail"].lower()

    def test_assert_with_revoked_key_returns_400(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]
        # Revoke it
        client.delete(
            f"/v1/auth/agent-keys/{agent_key_id}", headers={"Authorization": f"Bearer {raw_key}"}
        )

        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact_with_attest = {**_FACT, "attestation": {"key_id": agent_key_id, "signature": sig}}
        r = client.post(
            "/v1/facts",
            json=fact_with_attest,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 400
        assert "revoked" in r.json()["detail"].lower()

    def test_assert_with_wrong_entity_key_returns_403(self, authed_db) -> None:
        """Key registered to entity A cannot be used as attestation by entity B."""
        original = settings_module.settings
        test_settings = Settings(db_path=authed_db, auth_required=True, node_url="http://testnode")
        _patch(test_settings)

        key_a = create_api_key("stigmem://company.test/agent/alice", ["read", "write"])
        key_b = create_api_key("stigmem://company.test/agent/bob", ["read", "write"])
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            pub, priv = _gen_keypair()
            # Alice registers the key
            reg = c.post(
                "/v1/auth/agent-keys",
                json={"public_key": pub},
                headers={"Authorization": f"Bearer {key_a}"},
            )
            alice_agent_key_id = reg.json()["id"]

            # Bob tries to use Alice's key_id for attestation on his fact write
            sig = _sign_fact(
                priv,
                _FACT["entity"],
                _FACT["relation"],
                _FACT["value"]["type"],
                _FACT["value"]["v"],
                _FACT["source"],
            )
            fact_with_attest = {
                **_FACT,
                "attestation": {"key_id": alice_agent_key_id, "signature": sig},
            }
            r = c.post(
                "/v1/facts", json=fact_with_attest, headers={"Authorization": f"Bearer {key_b}"}
            )
            assert r.status_code == 403

        _patch(original)

    def test_assert_with_unknown_key_id_returns_400(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        _, priv = _gen_keypair()
        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact_with_attest = {**_FACT, "attestation": {"key_id": str(uuid.uuid4()), "signature": sig}}
        r = client.post(
            "/v1/facts", json=fact_with_attest, headers={"Authorization": f"Bearer {raw_key}"}
        )
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower()


class TestAttestationRequired:
    def test_required_mode_rejects_unsigned_fact(self, attest_required_client) -> None:
        client, _entity, raw_key = attest_required_client
        r = client.post(
            "/v1/facts",
            json=_FACT,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 400
        assert "attestation required" in r.json()["detail"].lower()

    def test_required_mode_accepts_signed_fact(self, attest_required_client) -> None:
        client, _entity, raw_key = attest_required_client
        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]

        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact_with_attest = {**_FACT, "attestation": {"key_id": agent_key_id, "signature": sig}}
        r = client.post(
            "/v1/facts",
            json=fact_with_attest,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert r.status_code == 201
        assert r.json()["attested_key_id"] == agent_key_id


# ---------------------------------------------------------------------------
# Audit log populated by attested assertion
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_attested_fact_appears_in_audit(self, authed_client_entity) -> None:
        client, entity, raw_key = authed_client_entity
        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]

        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        fact = client.post(
            "/v1/facts",
            json={**_FACT, "attestation": {"key_id": agent_key_id, "signature": sig}},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        fact_id = fact.json()["id"]

        # Audit entry should reference the agent key
        r = client.get(f"/v1/audit/facts/{fact_id}", headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 200
        entries = r.json()
        assert len(entries) == 1
        e = entries[0]
        assert e["fact_id"] == fact_id
        assert e["entity_uri"] == entity
        assert e["attested_key_id"] == agent_key_id

    def test_unattested_fact_audit_has_null_key(self, authed_client_entity) -> None:
        client, entity, raw_key = authed_client_entity
        fact = client.post(
            "/v1/facts",
            json=_FACT,
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        fact_id = fact.json()["id"]

        r = client.get(f"/v1/audit/facts/{fact_id}", headers={"Authorization": f"Bearer {raw_key}"})
        assert r.status_code == 200
        assert r.json()[0]["attested_key_id"] is None

    def test_audit_query_filter_attested(self, authed_client_entity) -> None:
        client, _entity, raw_key = authed_client_entity
        pub, priv = _gen_keypair()
        reg = client.post(
            "/v1/auth/agent-keys",
            json={"public_key": pub},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        agent_key_id = reg.json()["id"]

        # Write one attested + one unattested fact
        sig = _sign_fact(
            priv,
            _FACT["entity"],
            _FACT["relation"],
            _FACT["value"]["type"],
            _FACT["value"]["v"],
            _FACT["source"],
        )
        client.post(
            "/v1/facts",
            json={**_FACT, "attestation": {"key_id": agent_key_id, "signature": sig}},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        client.post(
            "/v1/facts",
            json={**_FACT, "relation": "memory:other-role"},
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        attested_r = client.get(
            "/v1/audit?attested=true", headers={"Authorization": f"Bearer {raw_key}"}
        )
        unattested_r = client.get(
            "/v1/audit?attested=false", headers={"Authorization": f"Bearer {raw_key}"}
        )

        assert all(e["attested_key_id"] is not None for e in attested_r.json()["entries"])
        assert all(e["attested_key_id"] is None for e in unattested_r.json()["entries"])
