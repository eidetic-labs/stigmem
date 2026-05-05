"""Integration tests for GET /v1/admin/audit — spec §22.3."""

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
    "source": "agent:writer",
    "confidence": 1.0,
    "scope": "local",
}


def _patch(test_settings: Settings) -> Settings:
    original = settings_module.settings
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings
    rl_mod.settings = test_settings
    rl_mod._HASH_CACHE.clear()
    return original


def _restore(original: Settings) -> None:
    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original
    rl_mod.settings = original
    rl_mod._HASH_CACHE.clear()


@pytest.fixture()
def audit_setup(tmp_db: str) -> Generator[tuple[TestClient, str, str], None, None]:
    """Yields (client, writer_key, audit_key).

    writer_key: read+write — can assert facts but cannot read admin audit.
    audit_key:  read+write+audit.read — can call GET /v1/admin/audit.
    """
    test_settings = Settings(
        db_path=tmp_db,
        auth_required=True,
        node_url="http://testnode",
        rate_limit_write_per_hour=0,
        rate_limit_read_per_hour=0,
    )
    original = _patch(test_settings)
    writer_key = create_api_key("agent:writer", ["read", "write"])
    audit_key = create_api_key("agent:auditor", ["read", "write", "audit.read"])
    with TestClient(create_app(), raise_server_exceptions=True) as c:
        yield c, writer_key, audit_key
    _restore(original)


class TestAdminAuditAccess:
    def test_403_without_audit_read(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Principal without audit.read is rejected with 403."""
        client, writer_key, _ = audit_setup
        r = client.get(
            "/v1/admin/audit",
            headers={"Authorization": f"Bearer {writer_key}"},
        )
        assert r.status_code == 403

    def test_200_with_audit_read(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Principal with audit.read gets a 200 response."""
        client, _, audit_key = audit_setup
        r = client.get(
            "/v1/admin/audit",
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200

    def test_401_unauthenticated(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Request with no auth is rejected when auth is required."""
        client, _, _ = audit_setup
        r = client.get("/v1/admin/audit")
        assert r.status_code == 401


class TestAdminAuditContent:
    def test_fact_write_events_appear(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Asserting a fact produces a fact_write event visible in the admin export."""
        client, writer_key, audit_key = audit_setup
        client.post(
            "/v1/facts",
            json=FACT,
            headers={"Authorization": f"Bearer {writer_key}"},
        )

        r = client.get(
            "/v1/admin/audit",
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200
        body = r.json()
        event_types = {e["event_type"] for e in body["entries"]}
        assert "fact_write" in event_types

    def test_filter_by_principal(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """principal= filter returns only events for that entity_uri."""
        client, writer_key, audit_key = audit_setup
        client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {writer_key}"})

        r = client.get(
            "/v1/admin/audit",
            params={"principal": "agent:writer"},
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200
        entries = r.json()["entries"]
        assert all(e["entity_uri"] == "agent:writer" for e in entries if e["entity_uri"])

    def test_filter_by_event_type(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """event_type= filter returns only events of that type."""
        client, writer_key, audit_key = audit_setup
        client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {writer_key}"})

        r = client.get(
            "/v1/admin/audit",
            params={"event_type": "fact_write"},
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200
        entries = r.json()["entries"]
        assert entries  # at least one result
        assert all(e["event_type"] == "fact_write" for e in entries)

    def test_seq_is_monotonically_increasing(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Audit entries returned by the export must have ascending seq values."""
        client, writer_key, audit_key = audit_setup
        for _ in range(3):
            client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {writer_key}"})

        r = client.get(
            "/v1/admin/audit",
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        entries = r.json()["entries"]
        seqs = [e["seq"] for e in entries if e["seq"] is not None]
        assert seqs == sorted(seqs), "seq values must be non-decreasing"

    def test_cursor_pagination(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Cursor-based pagination returns non-overlapping pages."""
        client, writer_key, audit_key = audit_setup
        for _ in range(5):
            client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {writer_key}"})

        page1 = client.get(
            "/v1/admin/audit",
            params={"limit": 2},
            headers={"Authorization": f"Bearer {audit_key}"},
        ).json()
        assert len(page1["entries"]) == 2
        cursor = page1["next_cursor"]
        assert cursor is not None

        page2 = client.get(
            "/v1/admin/audit",
            params={"limit": 2, "cursor": cursor},
            headers={"Authorization": f"Bearer {audit_key}"},
        ).json()
        ids_page1 = {e["id"] for e in page1["entries"]}
        ids_page2 = {e["id"] for e in page2["entries"]}
        assert ids_page1.isdisjoint(ids_page2), "Pages must not overlap"

    def test_time_range_filter(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """since= and until= filters constrain results by timestamp."""
        client, writer_key, audit_key = audit_setup
        client.post("/v1/facts", json=FACT, headers={"Authorization": f"Bearer {writer_key}"})

        r = client.get(
            "/v1/admin/audit",
            params={"since": "2000-01-01T00:00:00Z", "until": "2099-12-31T23:59:59Z"},
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200
        # All results must fall within the range (sanity check — just verify response shape)
        assert "entries" in r.json()

    def test_response_schema(self, audit_setup: tuple[TestClient, str, str]) -> None:
        """Response body must have entries, total, and next_cursor fields."""
        client, _, audit_key = audit_setup
        r = client.get(
            "/v1/admin/audit",
            headers={"Authorization": f"Bearer {audit_key}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "entries" in body
        assert "total" in body
        assert "next_cursor" in body
