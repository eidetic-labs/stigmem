from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from conftest import (
    _make_enc_settings,
    _patch_settings,
    _restore_settings,
    _time_travel_plugin_manifest,
    _tombstone_plugin_manifest,
)
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.settings as settings_module
from stigmem_node.db import db
from stigmem_node.main import create_app
from stigmem_node.plugins import Allow, Deny, PluginContext, PluginManifest
from stigmem_node.plugins.testing import stigmem_plugins


@pytest.fixture()
def authed_time_travel_client(
    tmp_db: str,
    backend: str,
    encrypt: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, str, str], None, None]:
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF", "true")
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF", "true")
    original = settings_module.settings
    test_settings = _make_enc_settings(
        tmp_db,
        backend,
        encrypt,
        auth_required=True,
        node_url="http://testnode",
    )
    extra = _patch_settings(test_settings)
    admin_key = auth_mod.create_api_key("agent:admin", ["read", "write", "admin"])
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, tmp_db, admin_key
    _restore_settings(original, extra)


def _deny_admin_manifest() -> PluginManifest:
    def capability_check(_ctx: PluginContext, **kwargs: object) -> Deny | Allow:
        if kwargs["capability"] == "admin":
            return Deny("admin disabled")
        return Allow()

    return PluginManifest(
        name="admin-deny",
        version="1.0.0",
        hooks={"capability_check": capability_check},
    )


def _plugin_manifests(*, deny_admin: bool) -> list[PluginManifest]:
    manifests = [_time_travel_plugin_manifest(), _tombstone_plugin_manifest()]
    if deny_admin:
        manifests.append(_deny_admin_manifest())
    return manifests


def _seed_legal_hold_fact() -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, timestamp,
                confidence, scope, tenant_id)
               VALUES (?, 'user:legal-hold', 'profile:status', 'string',
                       'sensitive active', 'agent:test',
                       '2026-05-01T00:00:00+00:00', 1.0, 'local', 'default')""",
            (str(uuid.uuid4()),),
        )
        conn.execute(
            """INSERT INTO tombstones
               (id, entity_uri, scope, reason, signed_by, signature,
                created_at, legal_hold, tenant_id)
               VALUES (?, 'user:legal-hold', '*', 'test', 'agent:admin',
                       'sig', ?, 1, 'default')""",
            (str(uuid.uuid4()), datetime.now(UTC).isoformat()),
        )


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _assert_admin_visible(client: TestClient, api_key: str) -> None:
    facts = client.get(
        "/v1/facts",
        params={
            "entity": "user:legal-hold",
            "scope": "local",
            "as_of": "2026-05-02T00:00:00+00:00",
        },
        headers=_headers(api_key),
    )
    assert facts.status_code == 200, facts.text
    assert len(facts.json()["facts"]) == 1

    recall = client.post(
        "/v1/recall",
        json={
            "query": "sensitive active",
            "scope": "local",
            "as_of": "2026-05-02T00:00:00+00:00",
        },
        headers=_headers(api_key),
    )
    assert recall.status_code == 200, recall.text
    assert len(recall.json()["facts"]) == 1


def _assert_admin_denied_by_voter_is_suppressed(client: TestClient, api_key: str) -> None:
    facts = client.get(
        "/v1/facts",
        params={
            "entity": "user:legal-hold",
            "scope": "local",
            "as_of": "2026-05-02T00:00:00+00:00",
        },
        headers=_headers(api_key),
    )
    assert facts.status_code == 200, facts.text
    facts_body = facts.json()
    assert facts_body["facts"] == []
    assert facts_body["total"] is None
    assert "x-total-count" not in facts.headers

    recall = client.post(
        "/v1/recall",
        json={
            "query": "sensitive active",
            "scope": "local",
            "as_of": "2026-05-02T00:00:00+00:00",
        },
        headers=_headers(api_key),
    )
    assert recall.status_code == 200, recall.text
    recall_body = recall.json()
    assert recall_body["facts"] == []
    assert recall_body["total_scored"] is None
    assert "x-total-count" not in recall.headers


def test_admin_capability_voting_applies_to_both_as_of_paths(
    authed_time_travel_client: tuple[TestClient, str, str],
) -> None:
    client, _db_path, admin_key = authed_time_travel_client
    _seed_legal_hold_fact()

    with stigmem_plugins(_plugin_manifests(deny_admin=False)):
        _assert_admin_visible(client, admin_key)

    with stigmem_plugins(_plugin_manifests(deny_admin=True)):
        _assert_admin_denied_by_voter_is_suppressed(client, admin_key)
