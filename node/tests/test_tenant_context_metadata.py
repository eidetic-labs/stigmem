from __future__ import annotations

from stigmem_node.plugins import SYSTEM_TENANT, TenantContext


def test_system_tenant_declares_context_source() -> None:
    assert SYSTEM_TENANT.metadata["tenant_context_source"] == "system"


def test_tenant_context_accepts_explicit_hook_source() -> None:
    tenant = TenantContext(
        tenant_id="default",
        metadata={"tenant_context_source": "hook"},
    )

    assert tenant.metadata["tenant_context_source"] == "hook"
