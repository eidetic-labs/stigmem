"""Multi-tenant isolation tests — Tenant A cannot read/write Tenant B data."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.settings as settings_module
from stigmem_node.main import create_app
from stigmem_node.plugins.testing import stigmem_plugins

_PLUGIN_SRC = Path(__file__).resolve().parents[2] / "experimental" / "multi-tenant" / "src"
if str(_PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_SRC))

_PLUGIN = importlib.import_module("stigmem_plugin_multi_tenant")

create_api_key = auth_mod.create_api_key
apply_migrations = db_mod.apply_migrations
Settings = settings_module.Settings
plugin_manifest = _PLUGIN.plugin_manifest

# ---------------------------------------------------------------------------
# Fixture: two authenticated tenants sharing one DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_two_tenants(tmp_path: object) -> Generator[tuple[TestClient, str, str], None, None]:
    """Single DB with two non-default keys and no multi-tenant plugin."""
    db_file = str(tmp_path) + "/mt.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(db_path=db_file, auth_required=True, node_url="http://testnode")
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings

    key_a = create_api_key("agent:alice", ["read", "write"], tenant_id="tenant-a")
    key_b = create_api_key("agent:bob", ["read", "write"], tenant_id="tenant-b")

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, key_a, key_b

    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original


@pytest.fixture()
def two_tenants(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, str, str], None, None]:
    """Single DB, two tenant keys, and the multi-tenant plugin enabled."""
    db_file = str(tmp_path) + "/mt.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(db_path=db_file, auth_required=True, node_url="http://testnode")
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings

    key_a = create_api_key("agent:alice", ["read", "write"], tenant_id="tenant-a")
    key_b = create_api_key("agent:bob", ["read", "write"], tenant_id="tenant-b")

    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    with stigmem_plugins([plugin_manifest()]):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, key_a, key_b

    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original


# ---------------------------------------------------------------------------
# Fact isolation
# ---------------------------------------------------------------------------


def test_default_install_collapses_non_default_tenant_keys(
    default_two_tenants: tuple,
) -> None:
    """Without the plugin, all callers resolve into the default tenant."""
    client, key_a, key_b = default_two_tenants

    resp = client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/agent/alice",
            "relation": "test:color",
            "value": {"type": "string", "v": "red"},
            "source": "agent:alice",
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert resp.status_code == 201
    fact_id = resp.json()["id"]

    me = client.get("/v1/me", headers={"Authorization": f"Bearer {key_a}"})
    assert me.status_code == 200
    assert me.json()["tenant_id"] == "default"

    assert (
        client.get(f"/v1/facts/{fact_id}", headers={"Authorization": f"Bearer {key_b}"}).status_code
        == 200
    )


def test_tenant_a_fact_invisible_to_tenant_b(two_tenants: tuple) -> None:
    """GET /v1/facts/{id} returns 404 for a cross-tenant fact."""
    client, key_a, key_b = two_tenants

    resp = client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/agent/alice",
            "relation": "test:color",
            "value": {"type": "string", "v": "red"},
            "source": "agent:alice",
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert resp.status_code == 201
    fact_id = resp.json()["id"]

    # Tenant A can read its own fact
    assert (
        client.get(f"/v1/facts/{fact_id}", headers={"Authorization": f"Bearer {key_a}"}).status_code
        == 200
    )

    # Tenant B gets 404
    assert (
        client.get(f"/v1/facts/{fact_id}", headers={"Authorization": f"Bearer {key_b}"}).status_code
        == 404
    )


def test_tenant_b_query_returns_empty(two_tenants: tuple) -> None:
    """GET /v1/facts query for Tenant B returns no Tenant A facts."""
    client, key_a, key_b = two_tenants

    # Tenant A writes a fact
    client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/agent/alice",
            "relation": "test:size",
            "value": {"type": "number", "v": 42},
            "source": "agent:alice",
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )

    resp = client.get("/v1/facts", headers={"Authorization": f"Bearer {key_b}"})
    assert resp.status_code == 200
    assert resp.json()["facts"] == []


def test_tenants_see_only_their_own_facts(two_tenants: tuple) -> None:
    """Each tenant's query returns only its own facts, not the other's."""
    client, key_a, key_b = two_tenants

    client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/x",
            "relation": "test:owner",
            "value": {"type": "string", "v": "alice"},
            "source": "agent:alice",
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )
    client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/x",
            "relation": "test:owner",
            "value": {"type": "string", "v": "bob"},
            "source": "agent:bob",
        },
        headers={"Authorization": f"Bearer {key_b}"},
    )

    resp_a = client.get("/v1/facts", headers={"Authorization": f"Bearer {key_a}"})
    resp_b = client.get("/v1/facts", headers={"Authorization": f"Bearer {key_b}"})

    values_a = {f["value"]["v"] for f in resp_a.json()["facts"]}
    values_b = {f["value"]["v"] for f in resp_b.json()["facts"]}

    assert values_a == {"alice"}
    assert values_b == {"bob"}


# ---------------------------------------------------------------------------
# Garden isolation
# ---------------------------------------------------------------------------


def test_garden_invisible_cross_tenant(two_tenants: tuple) -> None:
    """Tenant B cannot see Tenant A's garden by slug or in listing."""
    client, key_a, key_b = two_tenants

    resp = client.post(
        "/v1/gardens",
        json={"slug": "alpha-garden", "name": "Alpha", "scope": "company"},
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert resp.status_code == 201

    # Tenant B listing is empty
    resp_list = client.get("/v1/gardens", headers={"Authorization": f"Bearer {key_b}"})
    assert resp_list.status_code == 200
    assert resp_list.json() == []

    # Tenant B cannot GET by slug
    resp_get = client.get("/v1/gardens/alpha-garden", headers={"Authorization": f"Bearer {key_b}"})
    assert resp_get.status_code == 404


def test_garden_slug_can_be_reused_across_tenants(two_tenants: tuple) -> None:
    """The same slug is usable independently by both tenants."""
    client, key_a, key_b = two_tenants

    r_a = client.post(
        "/v1/gardens",
        json={"slug": "shared-slug", "name": "Tenant A Garden", "scope": "company"},
        headers={"Authorization": f"Bearer {key_a}"},
    )
    r_b = client.post(
        "/v1/gardens",
        json={"slug": "shared-slug", "name": "Tenant B Garden", "scope": "company"},
        headers={"Authorization": f"Bearer {key_b}"},
    )
    assert r_a.status_code == 201
    assert r_b.status_code == 201

    # Each tenant sees only their version
    ga = client.get("/v1/gardens/shared-slug", headers={"Authorization": f"Bearer {key_a}"}).json()
    gb = client.get("/v1/gardens/shared-slug", headers={"Authorization": f"Bearer {key_b}"}).json()
    assert ga["name"] == "Tenant A Garden"
    assert gb["name"] == "Tenant B Garden"


def test_tenant_a_cannot_write_to_tenant_b_garden(two_tenants: tuple) -> None:
    """Tenant A cannot assert a fact into Tenant B's garden URI."""
    client, key_a, key_b = two_tenants

    # Tenant B creates a garden
    r = client.post(
        "/v1/gardens",
        json={"slug": "b-private", "name": "B Private", "scope": "company"},
        headers={"Authorization": f"Bearer {key_b}"},
    )
    assert r.status_code == 201
    garden_id = r.json()["garden_id"]

    # Tenant A tries to write into it — should 404 (garden not visible across tenants)
    resp = client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/e",
            "relation": "test:x",
            "value": {"type": "string", "v": "v"},
            "source": "agent:alice",
            "scope": "company",
            "garden_id": garden_id,
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Audit isolation
# ---------------------------------------------------------------------------


def test_audit_scoped_by_tenant(two_tenants: tuple) -> None:
    """Audit log only returns entries for the caller's tenant."""
    client, key_a, key_b = two_tenants

    # Tenant A writes a fact
    client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/audit-entity",
            "relation": "test:q",
            "value": {"type": "string", "v": "1"},
            "source": "agent:alice",
        },
        headers={"Authorization": f"Bearer {key_a}"},
    )

    resp_a = client.get("/v1/audit", headers={"Authorization": f"Bearer {key_a}"})
    resp_b = client.get("/v1/audit", headers={"Authorization": f"Bearer {key_b}"})

    assert resp_a.status_code == 200
    assert len(resp_a.json()["entries"]) == 1

    assert resp_b.status_code == 200
    assert resp_b.json()["entries"] == []
