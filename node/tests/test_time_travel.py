"""Tests for §24 time-travel queries: query_facts_as_of and recall_as_of."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from conftest import _tombstone_plugin_manifest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "local",
}


@pytest.fixture()
def client(time_travel_client: TestClient) -> TestClient:
    """Run legacy time-travel behavior tests with the plugin registered."""
    return time_travel_client


def _iso(dt: datetime) -> str:
    """ISO 8601 UTC string with Z suffix (avoids + encoding issues in URLs)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _now() -> str:
    return _iso(datetime.now(UTC))


def _past(seconds: int = 60) -> str:
    return _iso(datetime.now(UTC) - timedelta(seconds=seconds))


def _future(seconds: int = 60) -> str:
    return _iso(datetime.now(UTC) + timedelta(seconds=seconds))


def _insert_retraction(db_path: str, fact_id: str, retracted_at: str) -> None:
    """Directly insert a fact_retractions row, simulating a retraction at a specific time."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO fact_retractions (id, fact_id, retracted_at, retracted_by) VALUES (?,?,?,?)",
        (f"retract_{uuid.uuid4().hex}", fact_id, retracted_at, "test:system"),
    )
    conn.commit()
    conn.close()


def _insert_tombstone(
    db_path: str,
    entity_uri: str,
    scope: str = "*",
    legal_hold: bool = False,
    created_at: str | None = None,
) -> str:
    """Directly insert a tombstones row; return tombstone id.

    scope is stored as a plain ScopePattern value ("*" | scope-name | JSON array),
    consistent with the _check_tombstone helper convention in facts.py.
    """
    tomb_id = f"tomb_{uuid.uuid4().hex}"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO tombstones
           (id, entity_uri, scope, reason, signed_by, signature, created_at, legal_hold)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            tomb_id,
            entity_uri,
            scope,  # plain ScopePattern: "*" | "local" | '["local","team"]'
            "test reason",
            "agent:admin",
            "fake-signature",
            created_at or _past(10),
            1 if legal_hold else 0,
        ),
    )
    conn.commit()
    conn.close()
    return tomb_id


# ---------------------------------------------------------------------------
# §24.4 — query_facts_as_of
# ---------------------------------------------------------------------------


class TestQueryFactsAsOf:
    def test_fact_visible_at_creation_time(self, client: TestClient, tmp_db: str) -> None:
        """A fact is visible at as_of >= its timestamp."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201
        fact = r.json()

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert any(f["id"] == fact["id"] for f in r2.json()["facts"])

    def test_fact_not_visible_before_creation(self, client: TestClient) -> None:
        """A fact is not visible at as_of before its timestamp."""
        before = _past(5)  # 5 seconds ago
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        r2 = client.get("/v1/facts", params={"as_of": before, "entity": "user:alice"})
        assert r2.status_code == 200
        assert r2.json()["facts"] == []

    def test_retraction_at_T_excludes_fact(self, client: TestClient, tmp_db: str) -> None:
        """Fact retracted at T must not appear in as_of=T+1 query (§24.2.1 c.3)."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201
        fact_id = r.json()["id"]

        _insert_retraction(tmp_db, fact_id, _past(30))

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert all(f["id"] != fact_id for f in r2.json()["facts"]), (
            "Retracted fact must not appear in as_of query after retraction"
        )

    def test_retraction_uses_fact_retractions_not_confidence(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """Gating must use fact_retractions table NOT facts.confidence=0.0 (§24.4)."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201
        fact_id = r.json()["id"]

        # Future retraction — not yet effective
        _insert_retraction(tmp_db, fact_id, _future(3600))

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        ids = [f["id"] for f in r2.json()["facts"]]
        assert fact_id in ids, "Fact with future retraction must still be visible at now via as_of"

    def test_expiry_at_T_excludes_fact(self, client: TestClient) -> None:
        """Fact expired before as_of must not appear (§24.2.1 c.2)."""
        expired_at = _past(10)
        r = client.post("/v1/facts", json={**FACT, "valid_until": expired_at})
        assert r.status_code == 201
        fact_id = r.json()["id"]

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert all(f["id"] != fact_id for f in r2.json()["facts"]), (
            "Expired fact must not appear in as_of query"
        )

    def test_non_expired_fact_visible(self, client: TestClient) -> None:
        """Fact with future valid_until is visible at as_of=now."""
        r = client.post("/v1/facts", json={**FACT, "valid_until": _future(3600)})
        assert r.status_code == 201
        fact_id = r.json()["id"]

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert any(f["id"] == fact_id for f in r2.json()["facts"])

    def test_tombstone_excludes_entity_default(self, client: TestClient, tmp_db: str) -> None:
        """legal_hold=false tombstone retroactively excludes entity facts (§24.3.1)."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        _insert_tombstone(tmp_db, "user:alice", scope="*", legal_hold=False)

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert r2.json()["facts"] == [], "Tombstoned entity must be excluded from as_of results"
        assert r2.json()["tombstone_notices"] == []

    def test_legal_hold_tombstone_excluded_for_non_admin(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """legal_hold=true tombstone silently excludes facts for non-admin caller (§24.3.2 r3)."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        _insert_tombstone(tmp_db, "user:alice", scope="*", legal_hold=True)

        r2 = client.get("/v1/facts", params={"as_of": _now(), "entity": "user:alice"})
        assert r2.status_code == 200
        assert r2.json()["facts"] == [], "legal_hold facts must be silently excluded for non-admin"
        assert r2.json()["tombstone_notices"] == []

    def test_legal_hold_tombstone_visible_with_notice_for_admin(
        self, tmp_db: str, backend: str, encrypt: str
    ) -> None:
        """legal_hold=true tombstone: admin caller sees facts with tombstone_notices (§24.3.3)."""
        from conftest import (
            _make_enc_settings,
            _patch_settings,
            _restore_settings,
            _time_travel_plugin_manifest,
        )

        import stigmem_node.settings as settings_module
        from stigmem_node.auth import create_api_key
        from stigmem_node.main import create_app
        from stigmem_node.plugins.testing import stigmem_plugins

        original = settings_module.settings
        test_settings = _make_enc_settings(
            tmp_db, backend, encrypt, auth_required=True, node_url="http://testnode"
        )
        extra = _patch_settings(test_settings)
        admin_key = create_api_key("agent:admin", ["read", "write", "admin"])

        try:
            with stigmem_plugins([_time_travel_plugin_manifest(), _tombstone_plugin_manifest()]):
                app = create_app()
                with TestClient(app, raise_server_exceptions=True) as c:
                    headers = {"Authorization": f"Bearer {admin_key}"}

                    r = c.post("/v1/facts", json=FACT, headers=headers)
                    assert r.status_code == 201

                    _insert_tombstone(tmp_db, "user:alice", scope="*", legal_hold=True)

                    r2 = c.get(
                        "/v1/facts",
                        params={"as_of": _now(), "entity": "user:alice"},
                        headers=headers,
                    )
                    assert r2.status_code == 200
                    body = r2.json()
                    assert len(body["facts"]) >= 1, "Admin must see legal_hold facts"
                    assert len(body["tombstone_notices"]) >= 1, (
                        "tombstone_notices must be populated"
                    )
                    notice = body["tombstone_notices"][0]
                    assert notice["entity_uri"] == "user:alice"
                    assert notice["legal_hold"] is True
        finally:
            _restore_settings(original, extra)

    def test_as_of_future_rejected(self, client: TestClient) -> None:
        """as_of in the future must return 400 as_of_future (§24.2.2)."""
        r = client.get("/v1/facts", params={"as_of": _future(3600)})
        assert r.status_code == 400
        body = r.json()
        assert body.get("detail", {}).get("code") == "as_of_future"

    def test_as_of_invalid_timestamp_rejected(self, client: TestClient) -> None:
        """Malformed as_of must return 400 as_of_invalid_timestamp (§24.6)."""
        r = client.get("/v1/facts", params={"as_of": "not-a-timestamp"})
        assert r.status_code == 400
        body = r.json()
        assert body.get("detail", {}).get("code") == "as_of_invalid_timestamp"

    def test_tombstone_notices_absent_when_no_legal_hold(self, client: TestClient) -> None:
        """tombstone_notices must be empty list when no legal_hold tombstones apply."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        r2 = client.get("/v1/facts", params={"as_of": _now()})
        assert r2.status_code == 200
        assert r2.json()["tombstone_notices"] == []


# ---------------------------------------------------------------------------
# §24.4 — recall_as_of
# ---------------------------------------------------------------------------


class TestRecallAsOf:
    def test_recall_as_of_returns_facts_visible_at_T(self, client: TestClient) -> None:
        """recall_as_of returns facts that existed at as_of."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        r2 = client.post(
            "/v1/recall",
            json={"query": "CEO role", "scope": "local", "as_of": _now()},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert "facts" in body
        assert "tombstone_notices" in body

    def test_recall_as_of_excludes_retracted_fact(self, client: TestClient, tmp_db: str) -> None:
        """Recall at as_of does not return facts retracted before as_of."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201
        fact_id = r.json()["id"]

        _insert_retraction(tmp_db, fact_id, _past(30))

        r2 = client.post(
            "/v1/recall",
            json={"query": "CEO role", "scope": "local", "as_of": _now()},
        )
        assert r2.status_code == 200
        fact_ids_returned = [sf["fact"]["id"] for sf in r2.json()["facts"]]
        assert fact_id not in fact_ids_returned, "Retracted fact must not appear in recall_as_of"

    def test_recall_as_of_excludes_expired_fact(self, client: TestClient) -> None:
        """Recall at as_of does not return facts expired before as_of."""
        r = client.post("/v1/facts", json={**FACT, "valid_until": _past(10)})
        assert r.status_code == 201
        fact_id = r.json()["id"]

        r2 = client.post(
            "/v1/recall",
            json={"query": "CEO role", "scope": "local", "as_of": _now()},
        )
        assert r2.status_code == 200
        fact_ids_returned = [sf["fact"]["id"] for sf in r2.json()["facts"]]
        assert fact_id not in fact_ids_returned, "Expired fact must not appear in recall_as_of"

    def test_recall_as_of_tombstone_excluded_non_admin(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """legal_hold tombstone: non-admin caller receives no annotated results (§24.3.2)."""
        r = client.post("/v1/facts", json=FACT)
        assert r.status_code == 201

        _insert_tombstone(tmp_db, "user:alice", scope="*", legal_hold=True)

        r2 = client.post(
            "/v1/recall",
            json={"query": "CEO role", "scope": "local", "as_of": _now()},
        )
        assert r2.status_code == 200
        entities = [sf["fact"]["entity"] for sf in r2.json()["facts"]]
        assert "user:alice" not in entities
        assert r2.json()["tombstone_notices"] == []

    def test_recall_as_of_tombstone_notices_for_admin(
        self, tmp_db: str, backend: str, encrypt: str
    ) -> None:
        """Admin caller gets tombstone_notices for legal_hold entities in recall_as_of."""
        from conftest import (
            _make_enc_settings,
            _patch_settings,
            _restore_settings,
            _time_travel_plugin_manifest,
        )

        import stigmem_node.settings as settings_module
        from stigmem_node.auth import create_api_key
        from stigmem_node.main import create_app
        from stigmem_node.plugins.testing import stigmem_plugins

        original = settings_module.settings
        test_settings = _make_enc_settings(
            tmp_db, backend, encrypt, auth_required=True, node_url="http://testnode"
        )
        extra = _patch_settings(test_settings)
        admin_key = create_api_key("agent:admin", ["read", "write", "admin"])

        try:
            with stigmem_plugins([_time_travel_plugin_manifest(), _tombstone_plugin_manifest()]):
                app = create_app()
                with TestClient(app, raise_server_exceptions=True) as c:
                    headers = {"Authorization": f"Bearer {admin_key}"}
                    r = c.post("/v1/facts", json=FACT, headers=headers)
                    assert r.status_code == 201

                    _insert_tombstone(tmp_db, "user:alice", scope="*", legal_hold=True)

                    r2 = c.post(
                        "/v1/recall",
                        json={"query": "CEO role", "scope": "local", "as_of": _now()},
                        headers=headers,
                    )
                    assert r2.status_code == 200
                    body = r2.json()
                    assert any(sf["fact"]["entity"] == "user:alice" for sf in body["facts"]), (
                        "Admin must see legal_hold entity facts in recall_as_of"
                    )
                    assert len(body["tombstone_notices"]) >= 1
                    assert body["tombstone_notices"][0]["legal_hold"] is True
        finally:
            _restore_settings(original, extra)

    def test_recall_as_of_future_rejected(self, client: TestClient) -> None:
        """as_of in the future must return 400."""
        r = client.post(
            "/v1/recall",
            json={"query": "test", "scope": "local", "as_of": _future(3600)},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "as_of_future"

    def test_recall_as_of_invalid_timestamp_rejected(self, client: TestClient) -> None:
        """Malformed as_of must return 400."""
        r = client.post(
            "/v1/recall",
            json={"query": "test", "scope": "local", "as_of": "bad-timestamp"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "as_of_invalid_timestamp"

    def test_recall_response_has_tombstone_notices_field(self, client: TestClient) -> None:
        """Regular recall response must include empty tombstone_notices field."""
        r = client.post("/v1/recall", json={"query": "test", "scope": "local"})
        assert r.status_code == 200
        assert "tombstone_notices" in r.json()
        assert r.json()["tombstone_notices"] == []
