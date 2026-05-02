"""Test fixtures for the Stigmem reference node."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations
from stigmem_node.main import create_app
from stigmem_node.settings import Settings


def _patch_settings(test_settings: Settings) -> None:
    """Propagate a test Settings instance into all modules that imported it."""
    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    wk_mod.settings = test_settings  # type: ignore[assignment]


def _restore_settings(original: Settings) -> None:
    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    wk_mod.settings = original  # type: ignore[assignment]


@pytest.fixture()
def tmp_db(tmp_path: object) -> str:
    db_file = str(tmp_path) + "/test.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)
    return db_file


@pytest.fixture()
def client(tmp_db: str) -> Generator[TestClient, None, None]:
    """TestClient with auth disabled and a fresh in-process DB."""
    original = settings_module.settings
    test_settings = Settings(db_path=tmp_db, auth_required=False, node_url="http://testnode")
    _patch_settings(test_settings)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    _restore_settings(original)


@pytest.fixture()
def authed_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """TestClient with auth enabled; yields (client, raw_key)."""
    original = settings_module.settings
    test_settings = Settings(db_path=tmp_db, auth_required=True, node_url="http://testnode")
    _patch_settings(test_settings)

    # Migrations already applied by tmp_db; create the API key with the test db path active
    raw_key = create_api_key("agent:test", ["read", "write"])

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore_settings(original)
