from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node import audit_event
from stigmem_node.plugins import AuditEvent, PluginContext, PluginManifest
from stigmem_node.plugins.testing import stigmem_plugins


def test_audit_emit_hook_fires_after_audit_write(client: TestClient) -> None:
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    manifest = PluginManifest(
        name="audit-capture",
        version="1.0.0",
        hooks={"audit_emit": capture},
    )

    with stigmem_plugins([manifest]):
        events.clear()
        audit_event.emit(
            "admin_action",
            entity_uri="agent:test",
            tenant_id="default",
            source="agent:test",
            detail={"action": "plugin-audit-test"},
        )

    assert len(events) == 1
    assert events[0].event_type == "admin_action"
    assert events[0].actor_uri == "agent:test"
    assert events[0].metadata["detail"] == {"action": "plugin-audit-test"}
