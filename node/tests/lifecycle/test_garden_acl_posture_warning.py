from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

import stigmem_node.db as db_mod
import stigmem_node.main as main_mod
import stigmem_node.rate_limit as rate_limit_mod
import stigmem_node.settings as settings_module
from stigmem_node.plugins.testing import stigmem_plugins

Settings = settings_module.Settings


def test_startup_warns_when_gardens_have_members_and_acl_plugin_is_absent(
    tmp_db: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _insert_garden_member(tmp_db)
    caplog.set_level("WARNING", logger="stigmem")

    with stigmem_plugins([]), _client(tmp_db):
        pass

    assert "Garden ACL filtering is disabled" in caplog.text
    assert "stigmem-plugin-memory-garden-acl not registered" in caplog.text


def test_startup_does_not_warn_when_no_garden_members_exist(
    tmp_db: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING", logger="stigmem")

    with stigmem_plugins([]), _client(tmp_db):
        pass

    assert "Garden ACL filtering is disabled" not in caplog.text


def test_doctor_reports_memory_garden_acl_filtering_state(tmp_db: str) -> None:
    with stigmem_plugins([]), _client(tmp_db) as client:
        response = client.get("/v1/doctor")

    assert response.status_code == 200
    assert response.json()["memory_garden_acl_filtering"] == "disabled"


def _insert_garden_member(db_path: str) -> None:
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO gardens
               (id, slug, name, scope, description, created_by, created_at, tenant_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                "garden-warning",
                "warning-garden",
                "Warning Garden",
                "company",
                None,
                "agent:owner",
                now,
                "default",
            ),
        )
        conn.execute(
            """INSERT INTO garden_members
               (garden_id, entity_uri, role, added_by, added_at)
               VALUES (?,?,?,?,?)""",
            ("garden-warning", "agent:owner", "admin", "agent:owner", now),
        )


@contextmanager
def _client(db_path: str) -> Generator[TestClient, None, None]:
    test_settings = Settings(
        db_path=db_path,
        auth_required=False,
        node_url="http://127.0.0.1:8765",
        subscription_delivery_sweep_s=86400,
    )
    with (
        _patched_settings(test_settings),
        TestClient(main_mod.create_app(), raise_server_exceptions=True) as client,
    ):
        yield client


class _patched_settings:
    def __init__(self, test_settings: Settings) -> None:
        self.test_settings = test_settings
        self.originals: dict[Any, Settings] = {}

    def __enter__(self) -> None:
        for module in (settings_module, db_mod, main_mod, rate_limit_mod):
            self.originals[module] = module.settings
            module.settings = self.test_settings
        rate_limit_mod._HASH_CACHE.clear()

    def __exit__(self, *_exc: object) -> None:
        for module, original in self.originals.items():
            module.settings = original
        rate_limit_mod._HASH_CACHE.clear()
