"""Tests for per-API-key sliding-window rate limiting middleware."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.rate_limit as rl_mod
import stigmem_node.settings as settings_module
from stigmem_node.auth import create_api_key
from stigmem_node.main import create_app
from stigmem_node.settings import Settings

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
    return original


def _restore(original: Settings) -> None:
    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original
    rl_mod.settings = original


@pytest.fixture()
def rl_write_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """Authenticated client with write limit=10."""
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        rate_limit_write_per_hour=10,
        rate_limit_read_per_hour=5000,
    )
    original = _patch(test_settings)
    raw_key = create_api_key("agent:test", ["read", "write"])
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore(original)


@pytest.fixture()
def rl_read_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """Authenticated client with read limit=5."""
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        rate_limit_write_per_hour=1000,
        rate_limit_read_per_hour=5,
    )
    original = _patch(test_settings)
    raw_key = create_api_key("agent:test", ["read", "write"])
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore(original)


class TestWriteRateLimit:
    def test_blocks_on_limit_exceeded(self, rl_write_client: tuple[TestClient, str]) -> None:
        client, key = rl_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(10):
            assert client.post("/v1/facts", json=FACT, headers=h).status_code == 201
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 429

    def test_retry_after_header_present(self, rl_write_client: tuple[TestClient, str]) -> None:
        client, key = rl_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(10):
            client.post("/v1/facts", json=FACT, headers=h)
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 429
        retry_after = int(r.headers["Retry-After"])
        assert 0 < retry_after <= 3601

    def test_reads_unaffected_by_write_quota(self, rl_write_client: tuple[TestClient, str]) -> None:
        client, key = rl_write_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(10):
            client.post("/v1/facts", json=FACT, headers=h)
        r = client.get("/v1/facts?entity=user:alice", headers=h)
        assert r.status_code == 200

    def test_different_keys_have_independent_quotas(self, tmp_db: str) -> None:
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
            # Exhaust key_a's quota
            for _ in range(2):
                client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_a}"})
            assert client.post(
                "/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_a}"}
            ).status_code == 429
            # key_b is unaffected
            assert client.post(
                "/v1/facts", json=FACT, headers={"Authorization": f"Bearer {key_b}"}
            ).status_code == 201
        _restore(original)


class TestReadRateLimit:
    def test_blocks_on_limit_exceeded(self, rl_read_client: tuple[TestClient, str]) -> None:
        client, key = rl_read_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            assert client.get("/v1/facts?entity=user:alice", headers=h).status_code == 200
        r = client.get("/v1/facts?entity=user:alice", headers=h)
        assert r.status_code == 429

    def test_writes_unaffected_by_read_quota(self, rl_read_client: tuple[TestClient, str]) -> None:
        client, key = rl_read_client
        h = {"Authorization": f"Bearer {key}"}
        for _ in range(5):
            client.get("/v1/facts?entity=user:alice", headers=h)
        r = client.post("/v1/facts", json=FACT, headers=h)
        assert r.status_code == 201


class TestRateLimitExemptions:
    def test_no_bearer_not_limited(self, tmp_db: str) -> None:
        """Unauthenticated requests without a Bearer token bypass rate limiting."""
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

    def test_zero_write_limit_disables(self, tmp_db: str) -> None:
        """rate_limit_write_per_hour=0 disables write rate limiting."""
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
                r = client.post("/v1/facts", json=FACT, headers=h)
                assert r.status_code == 201
        _restore(original)

    def test_federation_endpoints_exempt(self, tmp_db: str) -> None:
        """Requests to /v1/federation/ are never rate limited."""
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
            # Exhaust write quota on regular endpoint
            client.post("/v1/facts", json=FACT, headers=h)
            assert client.post("/v1/facts", json=FACT, headers=h).status_code == 429
            # Federation endpoint must not return 429 (may return 422 for bad payload)
            r = client.post("/v1/federation/peers", json={}, headers=h)
            assert r.status_code != 429
        _restore(original)
