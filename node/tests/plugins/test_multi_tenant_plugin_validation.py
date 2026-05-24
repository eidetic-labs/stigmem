from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from stigmem_node.auth import Identity
from stigmem_node.plugins import HookRegistry, TenantContext

_FEATURE_DIR = Path(__file__).resolve().parents[3] / "experimental" / "multi-tenant"
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_multi_tenant")
plugin_manifest = _PLUGIN.plugin_manifest


def test_validation_companion_covers_capability_surface() -> None:
    manifest = plugin_manifest()

    assert manifest.capabilities == frozenset(
        {
            "facts.read",
            "facts.write",
            "recall.read",
            "federation.read",
            "federation.write",
            "identity.read",
            "tenant.read",
            "tenant.write",
            "audit.emit",
            "config.read",
        }
    )


def test_gate_disabled_invariance_preserves_inbound_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STIGMEM_MULTI_TENANT_ENABLED", raising=False)
    registry = HookRegistry()
    registry.register_plugin(plugin_manifest())
    inbound = TenantContext(
        tenant_id="default",
        metadata={
            "source_tenant_id": "tenant-a",
            "tenant_context_source": "hook",
        },
    )
    identity = Identity("agent:alice", ["read"], tenant_id="tenant-a")

    tenant = registry.fire_filter_chain("tenant_resolve", inbound, identity=identity)

    assert tenant is inbound


def test_env_gate_malformed_values_resolve_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "not-a-bool")
    registry = HookRegistry()
    registry.register_plugin(plugin_manifest())
    inbound = TenantContext(
        tenant_id="default",
        metadata={
            "source_tenant_id": "tenant-a",
            "tenant_context_source": "hook",
        },
    )

    tenant = registry.fire_filter_chain("tenant_resolve", inbound, identity=object())

    assert tenant is inbound


def test_enabled_gate_normalizes_tenant_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STIGMEM_MULTI_TENANT_ENABLED", "true")
    registry = HookRegistry()
    registry.register_plugin(plugin_manifest())
    identity = Identity("agent:alice", ["read"], tenant_id=" Customer-A ")

    tenant = registry.fire_filter_chain(
        "tenant_resolve",
        TenantContext(
            tenant_id="default",
            metadata={
                "source_tenant_id": "default",
                "tenant_context_source": "hook",
            },
        ),
        identity=identity,
    )

    assert tenant.tenant_id == "customer-a"
    assert tenant.metadata["tenant_context_source"] == "resolved"
