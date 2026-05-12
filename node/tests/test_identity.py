"""Integration tests for Track C — Per-Principal Identity Hardening.

C1: per-agent keypair registration + source attestation enforcement
C2: OIDC principal linked identity surface (/v1/me with oidc_sub)
C3: end-to-end audit log joining principal, attested-source, fact-id
"""

from __future__ import annotations

import base64
from collections.abc import Generator
from typing import Any

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
import stigmem_node.routes.agent_keys as agent_keys_mod
import stigmem_node.routes.facts as facts_mod
import stigmem_node.settings as settings_module
from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations
from stigmem_node.main import create_app
from stigmem_node.settings import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[Ed25519PrivateKey, str, str]:
    """Return (private_key_obj, pub_b64url, priv_b64url)."""
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
    return priv, pub_b64, priv_b64


def _encode_v(vtype: str, v: Any) -> str:
    if vtype == "null":
        return "null"
    if vtype == "boolean":
        return "true" if v else "false"
    return str(v)


def _sign_assertion(
    priv: Ed25519PrivateKey,
    entity: str,
    relation: str,
    value_type: str,
    value_v: Any,
    source: str,
) -> str:
    """Produce a base64url Ed25519 signature over the canonical assertion message."""
    encoded_v = _encode_v(value_type, value_v)
    msg = f"{entity}\n{relation}\n{value_type}\n{encoded_v}\n{source}".encode()
    return base64.urlsafe_b64encode(priv.sign(msg)).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def attest_client(tmp_path: Any) -> Generator[tuple[TestClient, str], None, None]:
    """Client with auth enabled; yields (client, raw_api_key)."""
    db_file = str(tmp_path) + "/identity_test.db"
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(db_path=db_file, auth_required=True, node_url="http://testnode")

    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    if hasattr(facts_mod, "settings"):
        facts_mod.settings = test_settings  # type: ignore[assignment]
    if hasattr(agent_keys_mod, "settings"):
        agent_keys_mod.settings = test_settings  # type: ignore[assignment]

    raw_key = create_api_key("agent:tester", ["read", "write"], oidc_sub=None)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, raw_key

    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    if hasattr(facts_mod, "settings"):
        facts_mod.settings = original  # type: ignore[assignment]
    if hasattr(agent_keys_mod, "settings"):
        agent_keys_mod.settings = original  # type: ignore[assignment]


@pytest.fixture()
def attest_required_client(tmp_path: Any) -> Generator[tuple[TestClient, str], None, None]:
    """Client with both auth AND attestation_required enabled."""
    db_file = str(tmp_path) + "/attest_required_test.db"
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file, auth_required=True, attestation_required=True, node_url="http://testnode"
    )

    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    if hasattr(facts_mod, "settings"):
        facts_mod.settings = test_settings  # type: ignore[assignment]
    if hasattr(agent_keys_mod, "settings"):
        agent_keys_mod.settings = test_settings  # type: ignore[assignment]

    raw_key = create_api_key("agent:tester", ["read", "write"], oidc_sub=None)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, raw_key

    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    if hasattr(facts_mod, "settings"):
        facts_mod.settings = original  # type: ignore[assignment]
    if hasattr(agent_keys_mod, "settings"):
        agent_keys_mod.settings = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# C1: agent key registration
# ---------------------------------------------------------------------------


def test_c1_register_agent_key(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    priv, pub_b64, _ = _gen_keypair()

    r = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64, "description": "my test key"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["entity_uri"] == "agent:tester"
    assert body["public_key"] == pub_b64
    assert body["status"] == "active"
    assert body["description"] == "my test key"
    assert "id" in body


def test_c1_register_invalid_key(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    r = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": "not-a-valid-key!!"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 400


def test_c1_list_agent_keys(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    _, pub_b64, _ = _gen_keypair()
    client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )

    r = client.get("/v1/auth/agent-keys", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["entity_uri"] == "agent:tester"


def test_c1_revoke_agent_key(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    _, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    key_id = reg.json()["id"]

    r = client.delete(f"/v1/auth/agent-keys/{key_id}", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 204

    # Revoking twice is a conflict
    r2 = client.delete(f"/v1/auth/agent-keys/{key_id}", headers={"Authorization": f"Bearer {key}"})
    assert r2.status_code == 409


def test_c1_revoke_other_entity_key_forbidden(attest_client: tuple[TestClient, str]) -> None:
    client, _ = attest_client

    # Register a second entity
    other_key = create_api_key("agent:other", ["read", "write"])
    priv, pub_b64, _ = _gen_keypair()
    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {other_key}"},
    )
    key_id = reg.json()["id"]

    tester_key = create_api_key("agent:tester", ["read", "write"])
    r = client.delete(
        f"/v1/auth/agent-keys/{key_id}", headers={"Authorization": f"Bearer {tester_key}"}
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# C1: fact assertion with attestation
# ---------------------------------------------------------------------------


def test_c1_assert_with_valid_attestation(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    priv, pub_b64, _ = _gen_keypair()

    # Register the agent key
    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]

    entity = "agent:tester"
    relation = "test:role"
    value = {"type": "string", "v": "developer"}
    source = "agent:tester"
    sig = _sign_assertion(priv, entity, relation, value["type"], value["v"], source)

    r = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": relation,
            "value": value,
            "source": source,
            "attestation": {"key_id": agent_key_id, "signature": sig},
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["attested_key_id"] == agent_key_id


def test_c1_assert_with_invalid_signature_rejected(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    _, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]

    r = client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "test:role",
            "value": {"type": "string", "v": "developer"},
            "source": "agent:tester",
            "attestation": {
                "key_id": agent_key_id,
                "signature": base64.urlsafe_b64encode(b"bad_signature_bytes_xxx").decode(),
            },
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 400
    assert "signature" in r.json()["detail"].lower()


def test_c1_assert_with_revoked_key_rejected(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    priv, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]
    client.delete(f"/v1/auth/agent-keys/{agent_key_id}", headers={"Authorization": f"Bearer {key}"})

    sig = _sign_assertion(priv, "agent:tester", "test:role", "string", "v", "agent:tester")
    r = client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "test:role",
            "value": {"type": "string", "v": "v"},
            "source": "agent:tester",
            "attestation": {"key_id": agent_key_id, "signature": sig},
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 400
    assert "revoked" in r.json()["detail"].lower()


def test_c1_attestation_required_mode_rejects_unattested(
    attest_required_client: tuple[TestClient, str],
) -> None:
    client, key = attest_required_client
    r = client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "test:role",
            "value": {"type": "string", "v": "dev"},
            "source": "agent:tester",
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 400
    assert "attestation required" in r.json()["detail"].lower()


def test_c1_attestation_required_mode_accepts_attested(
    attest_required_client: tuple[TestClient, str],
) -> None:
    client, key = attest_required_client
    priv, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]

    entity = "agent:tester"
    relation = "test:role"
    value = {"type": "string", "v": "dev"}
    source = "agent:tester"
    sig = _sign_assertion(priv, entity, relation, value["type"], value["v"], source)

    r = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": relation,
            "value": value,
            "source": source,
            "attestation": {"key_id": agent_key_id, "signature": sig},
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# C2: OIDC principal linked identity surface
# ---------------------------------------------------------------------------


def test_c2_whoami_shows_oidc_sub(attest_client: tuple[TestClient, str]) -> None:
    client, _ = attest_client
    oidc_key = create_api_key("oidc:user-sub-123", ["read", "write"], oidc_sub="user-sub-123")

    r = client.get("/v1/me", headers={"Authorization": f"Bearer {oidc_key}"})
    assert r.status_code == 200
    body = r.json()
    assert body["entity_uri"] == "oidc:user-sub-123"
    assert body["oidc_sub"] == "user-sub-123"


def test_c2_whoami_non_oidc_has_null_oidc_sub(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    r = client.get("/v1/me", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    assert r.json()["oidc_sub"] is None


# ---------------------------------------------------------------------------
# C3: audit log surface
# ---------------------------------------------------------------------------


def test_c3_assert_creates_audit_entry(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client

    r = client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "x:y",
            "value": {"type": "string", "v": "z"},
            "source": "agent:tester",
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    fact_id = r.json()["id"]

    audit = client.get(f"/v1/audit/facts/{fact_id}", headers={"Authorization": f"Bearer {key}"})
    assert audit.status_code == 200
    entries = audit.json()
    assert len(entries) == 1
    e = entries[0]
    assert e["fact_id"] == fact_id
    assert e["event_type"] == "fact_write"
    assert e["entity_uri"] == "agent:tester"
    assert e["oidc_sub"] is None
    assert e["attested_key_id"] is None


def test_c3_audit_records_oidc_sub(attest_client: tuple[TestClient, str]) -> None:
    client, _ = attest_client
    oidc_key = create_api_key("oidc:human-42", ["read", "write"], oidc_sub="human-42")

    r = client.post(
        "/v1/facts",
        json={
            "entity": "oidc:human-42",
            "relation": "x:y",
            "value": {"type": "string", "v": "z"},
            "source": "oidc:human-42",
        },
        headers={"Authorization": f"Bearer {oidc_key}"},
    )
    fact_id = r.json()["id"]

    audit = client.get(
        f"/v1/audit/facts/{fact_id}", headers={"Authorization": f"Bearer {oidc_key}"}
    )
    e = audit.json()[0]
    assert e["entity_uri"] == "oidc:human-42"
    assert e["oidc_sub"] == "human-42"


def test_c3_audit_records_attested_key_id(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    priv, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]

    entity = "agent:tester"
    relation = "c3:check"
    value = {"type": "string", "v": "ok"}
    source = "agent:tester"
    sig = _sign_assertion(priv, entity, relation, value["type"], value["v"], source)

    r = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": relation,
            "value": value,
            "source": source,
            "attestation": {"key_id": agent_key_id, "signature": sig},
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    fact_id = r.json()["id"]

    audit = client.get(f"/v1/audit/facts/{fact_id}", headers={"Authorization": f"Bearer {key}"})
    e = audit.json()[0]
    assert e["attested_key_id"] == agent_key_id
    assert e["entity_uri"] == "agent:tester"


def test_c3_audit_query_by_entity(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client

    # Assert two facts from different entities
    client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "x:a",
            "value": {"type": "string", "v": "1"},
            "source": "agent:tester",
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    other_key = create_api_key("agent:other", ["read", "write"])
    client.post(
        "/v1/facts",
        json={
            "entity": "agent:other",
            "relation": "x:b",
            "value": {"type": "string", "v": "2"},
            "source": "agent:other",
        },
        headers={"Authorization": f"Bearer {other_key}"},
    )

    r = client.get(
        "/v1/audit",
        params={"entity_uri": "agent:tester"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert all(e["entity_uri"] == "agent:tester" for e in entries)


def test_c3_audit_query_attested_filter(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    priv, pub_b64, _ = _gen_keypair()

    reg = client.post(
        "/v1/auth/agent-keys",
        json={"public_key": pub_b64},
        headers={"Authorization": f"Bearer {key}"},
    )
    agent_key_id = reg.json()["id"]

    # Unattested fact
    client.post(
        "/v1/facts",
        json={
            "entity": "agent:tester",
            "relation": "x:unattested",
            "value": {"type": "string", "v": "u"},
            "source": "agent:tester",
        },
        headers={"Authorization": f"Bearer {key}"},
    )

    # Attested fact
    entity, relation, value, source = (
        "agent:tester",
        "x:attested",
        {"type": "string", "v": "a"},
        "agent:tester",
    )
    sig = _sign_assertion(priv, entity, relation, value["type"], value["v"], source)
    client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": relation,
            "value": value,
            "source": source,
            "attestation": {"key_id": agent_key_id, "signature": sig},
        },
        headers={"Authorization": f"Bearer {key}"},
    )

    r = client.get(
        "/v1/audit", params={"attested": "true"}, headers={"Authorization": f"Bearer {key}"}
    )
    attested_entries = r.json()["entries"]
    assert all(e["attested_key_id"] is not None for e in attested_entries)

    r2 = client.get(
        "/v1/audit", params={"attested": "false"}, headers={"Authorization": f"Bearer {key}"}
    )
    unattested_entries = r2.json()["entries"]
    assert all(e["attested_key_id"] is None for e in unattested_entries)


def test_c3_audit_unknown_fact_returns_404(attest_client: tuple[TestClient, str]) -> None:
    client, key = attest_client
    r = client.get(
        "/v1/audit/facts/nonexistent-fact-id", headers={"Authorization": f"Bearer {key}"}
    )
    assert r.status_code == 404
