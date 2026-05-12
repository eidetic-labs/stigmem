"""Billing hook emission tests — fact_written and garden_created events."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.billing as billing_mod
import stigmem_node.db as db_mod
import stigmem_node.settings as settings_module
from stigmem_node.main import create_app

create_api_key = auth_mod.create_api_key
apply_migrations = db_mod.apply_migrations
Settings = settings_module.Settings

# ---------------------------------------------------------------------------
# Fixture: client with CaptureBus injected
# ---------------------------------------------------------------------------


@pytest.fixture()
def hooked_client(tmp_db: str) -> Generator[tuple[TestClient, billing_mod.CaptureBus], None, None]:
    """TestClient with auth disabled and a CaptureBus wired for assertions."""
    original_settings = settings_module.settings
    test_settings = Settings(db_path=tmp_db, auth_required=False, node_url="http://testnode")
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings

    original_bus = billing_mod._bus
    bus = billing_mod.CaptureBus()
    billing_mod.set_hook_bus(bus)

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, bus

    billing_mod.set_hook_bus(original_bus)
    settings_module.settings = original_settings
    auth_mod.settings = original_settings
    db_mod.settings = original_settings


# ---------------------------------------------------------------------------
# fact_written
# ---------------------------------------------------------------------------


def test_fact_written_event_emitted(hooked_client: tuple) -> None:
    """Asserting a fact emits exactly one fact_written billing event."""
    client, bus = hooked_client

    resp = client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/e1",
            "relation": "test:x",
            "value": {"type": "string", "v": "hello"},
            "source": "agent:test",
        },
    )
    assert resp.status_code == 201
    fact_id = resp.json()["id"]

    assert len(bus.events) == 1
    evt = bus.events[0]
    assert evt.event_type == "fact_written"
    assert evt.fact_id == fact_id
    assert evt.tenant_id == "default"
    assert isinstance(evt.ts, str) and len(evt.ts) > 0


def test_fact_written_captures_tenant_id(tmp_path: object) -> None:
    """fact_written event carries the correct tenant_id from the API key."""
    db_file = str(tmp_path) + "/billing_tenant.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)

    original = settings_module.settings
    test_settings = Settings(db_path=db_file, auth_required=True, node_url="http://testnode")
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings

    original_bus = billing_mod._bus
    bus = billing_mod.CaptureBus()
    billing_mod.set_hook_bus(bus)

    key = create_api_key("agent:tester", ["read", "write"], tenant_id="acme-corp")

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.post(
            "/v1/facts",
            json={
                "entity": "stigmem://test/e2",
                "relation": "test:y",
                "value": {"type": "number", "v": 7},
                "source": "agent:tester",
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 201

    assert len(bus.events) == 1
    assert bus.events[0].tenant_id == "acme-corp"

    billing_mod.set_hook_bus(original_bus)
    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original


def test_multiple_facts_emit_multiple_events(hooked_client: tuple) -> None:
    """Each successful fact assertion emits its own event."""
    client, bus = hooked_client

    for i in range(3):
        client.post(
            "/v1/facts",
            json={
                "entity": f"stigmem://test/e{i}",
                "relation": "test:seq",
                "value": {"type": "number", "v": i},
                "source": "agent:test",
            },
        )

    assert len(bus.events) == 3
    assert all(e.event_type == "fact_written" for e in bus.events)
    fact_ids = {e.fact_id for e in bus.events}
    assert len(fact_ids) == 3  # all distinct


# ---------------------------------------------------------------------------
# garden_created
# ---------------------------------------------------------------------------


def test_garden_created_event_emitted(hooked_client: tuple) -> None:
    """Creating a garden emits exactly one garden_created billing event."""
    client, bus = hooked_client

    resp = client.post(
        "/v1/gardens",
        json={"slug": "billing-test-garden", "name": "Billing Test", "scope": "company"},
    )
    assert resp.status_code == 201

    garden_events = [e for e in bus.events if e.event_type == "garden_created"]
    assert len(garden_events) == 1
    evt = garden_events[0]
    assert evt.tenant_id == "default"
    assert "billing-test-garden" in (evt.garden_id or "")


def test_fact_and_garden_events_independent(hooked_client: tuple) -> None:
    """fact_written and garden_created events are tracked independently."""
    client, bus = hooked_client

    client.post(
        "/v1/gardens",
        json={"slug": "my-garden", "name": "My Garden", "scope": "company"},
    )
    client.post(
        "/v1/facts",
        json={
            "entity": "stigmem://test/g",
            "relation": "test:z",
            "value": {"type": "string", "v": "x"},
            "source": "agent:test",
        },
    )

    event_types = [e.event_type for e in bus.events]
    assert "garden_created" in event_types
    assert "fact_written" in event_types
