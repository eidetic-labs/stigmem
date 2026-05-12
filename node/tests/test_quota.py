"""Tests for per-principal token-bucket quota middleware — spec §22.4."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.rate_limit as rl_mod
import stigmem_node.settings as settings_module
from stigmem_node.main import create_app

create_api_key = auth_mod.create_api_key
Settings = settings_module.Settings

FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "company",
}


def _patch(test_settings: Settings) -> Settings:
    original = settings_module.settings
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings
    rl_mod.settings = test_settings
    # Clear the principal lookup cache between tests.
    rl_mod._HASH_CACHE.clear()
    return original


def _restore(original: Settings) -> None:
    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original
    rl_mod.settings = original
    rl_mod._HASH_CACHE.clear()


@pytest.fixture()
def quota_write_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """Authed client with fact_write burst=5."""
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        rate_limit_write_per_hour=5,
        rate_limit_read_per_hour=5000,
    )
    original = _patch(test_settings)
    raw_key = create_api_key("agent:quota-test", ["read", "write"])
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore(original)


@pytest.fixture()
def quota_read_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """Authed client with fact_read burst=3."""
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        rate_limit_write_per_hour=5000,
        rate_limit_read_per_hour=3,
    )
    original = _patch(test_settings)
    raw_key = create_api_key("agent:quota-test", ["read", "write"])
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore(original)


class TestTokenBucketWrite:
    def test_burst_allowed_then_blocked(self, quota_write_client: tuple[TestClient, str]) -> None:
        """First N writes allowed; N+1 returns 429."""
        client, key = quota_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            r = client.post("/v1/facts", json=FACT, headers=h)
            assert r.status_code == 201, r.text
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 429

    def test_429_shape(self, quota_write_client: tuple[TestClient, str]) -> None:
        """429 body must include error, dimension, principal, retry_after."""
        client, key = quota_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            client.post("/v1/facts", json=FACT, headers=h)
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 429
        body = r.json()
        assert body["error"] == "quota_exceeded"
        assert body["dimension"] == "fact_write"
        assert body["principal"] == "agent:quota-test"
        assert isinstance(body["retry_after"], float)
        assert body["retry_after"] > 0

    def test_retry_after_header(self, quota_write_client: tuple[TestClient, str]) -> None:
        """Retry-After header must be present and a positive integer."""
        client, key = quota_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            client.post("/v1/facts", json=FACT, headers=h)
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 429
        assert int(r.headers["Retry-After"]) >= 1

    def test_reads_unaffected_by_write_quota(
        self, quota_write_client: tuple[TestClient, str]
    ) -> None:
        """Exhausting write quota must not block reads."""
        client, key = quota_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            client.post("/v1/facts", json=FACT, headers=h)
        assert client.post("/v1/facts", json=FACT, headers=h).status_code == 429
        r = client.get("/v1/facts?entity=user:alice", headers=h)
        assert r.status_code == 200

    def test_independent_principals(self, tmp_db: str) -> None:
        """Two principals have independent token buckets."""
        test_settings = Settings(
            db_path=tmp_db,
            auth_required=True,
            node_url="http://testnode",
            rate_limit_write_per_hour=2,
            rate_limit_read_per_hour=5000,
        )
        original = _patch(test_settings)
        key_a = create_api_key("agent:a", ["read", "write"])
        key_b = create_api_key("agent:b", ["read", "write"])
        with TestClient(create_app(), raise_server_exceptions=True) as client:
            for _ in range(2):
                client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_a}"})
            assert (
                client.post(
                    "/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_a}"}
                ).status_code
                == 429
            )
            assert (
                client.post(
                    "/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_b}"}
                ).status_code
                == 201
            )
        _restore(original)


class TestTokenBucketRead:
    def test_burst_allowed_then_blocked(self, quota_read_client: tuple[TestClient, str]) -> None:
        """First N reads allowed; N+1 returns 429."""
        client, key = quota_read_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(3):
            assert client.get("/v1/facts?entity=user:alice", headers=h).status_code == 200
        r = client.get("/v1/facts?entity=user:alice", headers=h)
        assert r.status_code == 429
        assert r.json()["dimension"] == "fact_read"

    def test_writes_unaffected_by_read_quota(
        self, quota_read_client: tuple[TestClient, str]
    ) -> None:
        """Exhausting read quota must not block writes."""
        client, key = quota_read_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(3):
            client.get("/v1/facts?entity=user:alice", headers=h)
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 201


class TestQuotaExemptions:
    def test_no_bearer_not_limited(self, tmp_db: str) -> None:
        """Unauthenticated requests bypass quota."""
        test_settings = Settings(
            db_path=tmp_db,
            auth_required=False,
            node_url="http://testnode",
            rate_limit_write_per_hour=1,
            rate_limit_read_per_hour=1,
        )
        original = _patch(test_settings)
        with TestClient(create_app(), raise_server_exceptions=True) as client:
            for _ in range(5):
                r = client.post("/v1/facts", json=FACT)
                assert r.status_code == 201
        _restore(original)

    def test_zero_limits_disable_enforcement(self, tmp_db: str) -> None:
        """Both limits=0 disables enforcement entirely."""
        test_settings = Settings(
            db_path=tmp_db,
            auth_required=True,
            node_url="http://testnode",
            rate_limit_write_per_hour=0,
            rate_limit_read_per_hour=0,
        )
        original = _patch(test_settings)
        raw_key = create_api_key("agent:test", ["read", "write"])
        with TestClient(create_app(), raise_server_exceptions=True) as client:
            h = {"Authorization": f"Bearer {raw_key}"}
            for _ in range(20):
                assert client.post("/v1/facts", json=FACT, headers=h).status_code == 201
        _restore(original)

    def test_federation_endpoints_exempt(self, tmp_db: str) -> None:
        """Requests to /v1/federation/ are never quota-checked."""
        test_settings = Settings(
            db_path=tmp_db,
            auth_required=True,
            node_url="http://testnode",
            rate_limit_write_per_hour=1,
            rate_limit_read_per_hour=1,
        )
        original = _patch(test_settings)
        raw_key = create_api_key("agent:test", ["read", "write"])
        with TestClient(create_app(), raise_server_exceptions=True) as client:
            h = {"Authorization": f"Bearer {raw_key}"}
            client.post("/v1/facts", json=FACT, headers=h)
            assert client.post("/v1/facts", json=FACT, headers=h).status_code == 429
            r = client.post("/v1/federation/peers", json={}, headers=h)
            assert r.status_code != 429
        _restore(original)


class TestQuotaBreachAuditEvent:
    def test_quota_breach_event_written(self, tmp_db: str) -> None:
        """A quota_breach audit event must be emitted on every 429."""
        import sqlite3

        test_settings = Settings(
            db_path=tmp_db,
            auth_required=True,
            node_url="http://testnode",
            rate_limit_write_per_hour=2,
            rate_limit_read_per_hour=5000,
        )
        original = _patch(test_settings)
        raw_key = create_api_key("agent:breach-test", ["read", "write"])
        with TestClient(create_app(), raise_server_exceptions=True) as client:
            h = {"Authorization": f"Bearer {raw_key}"}
            for _ in range(2):
                client.post("/v1/facts", json=FACT, headers=h)
            r = client.post("/v1/facts", json=FACT, headers=h)
            assert r.status_code == 429

        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM fact_audit_log WHERE event_type='quota_breach'"
        ).fetchall()
        conn.close()
        assert len(rows) >= 1
        assert rows[0]["entity_uri"] == "agent:breach-test"

        _restore(original)
