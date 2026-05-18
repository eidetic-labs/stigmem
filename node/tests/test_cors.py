"""CORS regression coverage for browser UI clients."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from httpx import Response

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.main as main_mod
import stigmem_node.rate_limit as rate_limit_mod
import stigmem_node.routes.wellknown as wellknown_mod
import stigmem_node.settings as settings_module

Settings = settings_module.Settings


def test_cors_settings_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STIGMEM_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("STIGMEM_CORS_ALLOWED_ORIGIN_REGEX", raising=False)
    monkeypatch.delenv("STIGMEM_CORS_ALLOW_CREDENTIALS", raising=False)
    monkeypatch.delenv("STIGMEM_CORS_DEV_LOCALHOST", raising=False)

    defaults = Settings(_env_file=None)
    assert defaults.cors_allowed_origins == []
    assert defaults.cors_allowed_origin_regex is None
    assert defaults.cors_allow_credentials is True
    assert defaults.cors_dev_localhost is False

    monkeypatch.setenv("STIGMEM_CORS_DEV_LOCALHOST", "1")
    assert Settings(_env_file=None).cors_dev_localhost is True

    monkeypatch.setenv(
        "STIGMEM_CORS_ALLOWED_ORIGINS",
        "https://a.example.com,https://b.example.com",
    )
    assert Settings(_env_file=None).cors_allowed_origins == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_no_cors_config_does_not_register_middleware(tmp_db: str) -> None:
    test_settings = Settings(db_path=tmp_db, auth_required=False, node_url="http://testnode")
    with _patched_settings(test_settings):
        app = main_mod.create_app()

    middleware_classes = [cast("Any", item).cls for item in app.user_middleware]
    assert CORSMiddleware not in middleware_classes


def test_dev_localhost_options_allows_localhost_origin(tmp_db: str) -> None:
    with _client(tmp_db, cors_dev_localhost=True) as client:
        response = _preflight(client, "http://localhost:18765")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:18765"
    assert "GET" in response.headers["access-control-allow-methods"]
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
    assert response.headers["access-control-max-age"] == "600"


def test_dev_localhost_logs_startup_warning(
    tmp_db: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING", logger="stigmem")
    with _client(tmp_db, cors_dev_localhost=True):
        pass

    assert "STIGMEM_CORS_DEV_LOCALHOST=1" in caplog.text


def test_dev_localhost_options_allows_loopback_origin(tmp_db: str) -> None:
    with _client(tmp_db, cors_dev_localhost=True) as client:
        response = _preflight(client, "http://127.0.0.1:54321")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:54321"


def test_dev_localhost_options_rejects_non_localhost_origin(tmp_db: str) -> None:
    with _client(tmp_db, cors_dev_localhost=True) as client:
        response = _preflight(client, "https://evil.example.com")

    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_explicit_origin_allows_prod_and_rejects_localhost(tmp_db: str) -> None:
    with _client(
        tmp_db,
        cors_allowed_origins=["https://prod.example.com"],
        cors_dev_localhost=False,
    ) as client:
        prod = _preflight(client, "https://prod.example.com")
        local = _preflight(client, "http://localhost:18765")

    assert prod.status_code == 200
    assert prod.headers["access-control-allow-origin"] == "https://prod.example.com"
    assert local.headers.get("access-control-allow-origin") != "http://localhost:18765"


def test_wellknown_advertises_cors_posture(tmp_db: str) -> None:
    with _client(tmp_db, cors_dev_localhost=True) as client:
        response = client.get(
            "/.well-known/stigmem",
            headers={"Origin": "http://localhost:18765"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:18765"
    assert response.json()["cors"] == {"dev_localhost": True, "configured": True}


def test_options_bypasses_rate_limit_and_does_not_consume_quota(tmp_db: str) -> None:
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        cors_dev_localhost=True,
        rate_limit_write_per_hour=1,
        rate_limit_read_per_hour=5000,
    )
    with _patched_settings(test_settings):
        raw_key = auth_mod.create_api_key("agent:cors-quota", ["read", "write"])
        with TestClient(main_mod.create_app(), raise_server_exceptions=True) as client:
            for _ in range(100):
                response = _preflight(client, "http://localhost:18765", path="/v1/facts")
                assert response.status_code == 200
            post = client.post(
                "/v1/facts",
                json={
                    "entity": "user:alice",
                    "relation": "memory:role",
                    "value": {"type": "string", "v": "CEO"},
                    "source": "agent:test",
                    "confidence": 1.0,
                    "scope": "company",
                },
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "Origin": "http://localhost:18765",
                },
            )

    assert post.status_code == 201, post.text


def test_options_bypasses_mtls_plaintext_guard_for_non_federation_paths(tmp_db: str) -> None:
    with _client(
        tmp_db,
        cors_dev_localhost=True,
        tls_cert_path="/tmp/node.crt",
        tls_key_path="/tmp/node.key",
        tls_ca_bundle="/tmp/ca.crt",
    ) as client:
        options = _preflight(client, "http://localhost:18765", path="/v1/facts")
        federation_options = _preflight(
            client, "http://localhost:18765", path="/v1/federation/peers"
        )
        federation_get = client.get(
            "/v1/federation/peers",
            headers={"Origin": "http://localhost:18765"},
        )

    assert options.status_code == 200
    assert options.headers["access-control-allow-origin"] == "http://localhost:18765"
    assert federation_options.status_code == 421
    assert federation_get.status_code == 421


def _preflight(
    client: TestClient,
    origin: str,
    *,
    path: str = "/v1/me",
) -> Response:
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


@contextmanager
def _client(tmp_db: str, **overrides: object) -> Generator[TestClient, None, None]:
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=False,
        node_url="http://127.0.0.1:8765",
        **cast("Any", overrides),
    )
    with _patched_settings(test_settings):
        client_context = TestClient(main_mod.create_app(), raise_server_exceptions=True)
        with client_context as client:
            yield client


class _patched_settings:
    def __init__(self, test_settings: Settings) -> None:
        self.test_settings = test_settings
        self.originals: dict[Any, Settings] = {}

    def __enter__(self) -> None:
        modules: tuple[Any, ...] = (
            settings_module,
            auth_mod,
            db_mod,
            main_mod,
            rate_limit_mod,
            wellknown_mod,
        )
        for module in modules:
            self.originals[module] = module.settings
            module.settings = self.test_settings
        rate_limit_mod._HASH_CACHE.clear()

    def __exit__(self, *_exc: object) -> None:
        for module, original in self.originals.items():
            module.settings = original
        rate_limit_mod._HASH_CACHE.clear()
