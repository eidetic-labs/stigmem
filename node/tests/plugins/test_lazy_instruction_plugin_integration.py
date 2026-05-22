from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, TypeVar

import pytest
from conftest import _make_enc_settings, _patch_settings, _restore_settings
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.plugins.registry as plugin_registry
import stigmem_node.settings as settings_module
from stigmem_node.main import _include_plugin_routers, create_app
from stigmem_node.plugins import Allow, HookRegistry, PluginContext, PluginManifest
from stigmem_node.plugins.discovery import DiscoveredPlugin
from stigmem_node.plugins.testing import stigmem_plugins

_FEATURE_DIR = (
    Path(__file__).resolve().parents[3] / "experimental" / "lazy-instruction-discovery"
)
_SRC_DIR = _FEATURE_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_PLUGIN = importlib.import_module("stigmem_plugin_lazy_instruction_discovery")
PLUGIN_NAME = _PLUGIN.PLUGIN_NAME
plugin_manifest = _PLUGIN.plugin_manifest

T = TypeVar("T")


@pytest.fixture()
def lazy_plugin_client(
    tmp_db: str,
    backend: str,
    encrypt: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    original = settings_module.settings
    test_settings = _make_enc_settings(
        tmp_db,
        backend,
        encrypt,
        auth_required=False,
        node_url="http://testnode",
    )
    extra = _patch_settings(test_settings)
    monkeypatch.setenv("STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ALLOW_MANIFEST_PUBLISH", "true")
    monkeypatch.setenv("STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ALLOW_INSTRUCTION_RECALL", "true")
    monkeypatch.setenv("STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ALLOW_FILE_PATH_ENTRIES", "true")
    monkeypatch.setattr(plugin_registry, "_current_stigmem_version", lambda: "0.9.0a3")

    manifest = plugin_manifest()
    discovered = DiscoveredPlugin(
        manifest=manifest,
        entry_point_name="lazy-instruction-discovery",
        entry_point_value="stigmem_plugin_lazy_instruction_discovery:plugin_manifest",
        distribution=PLUGIN_NAME,
    )
    app = create_app()
    _include_plugin_routers(app, (discovered,))
    admin_key = auth_mod.create_api_key(
        "stigmem://testnode/agent/admin",
        ["read", "write", "federate", "admin"],
    )

    try:
        with stigmem_plugins([manifest]), TestClient(app) as client:
            client.headers.update({"Authorization": f"Bearer {admin_key}"})
            yield client
    finally:
        _restore_settings(original, extra)


def test_default_install_keeps_lazy_instruction_behavior_absent(client: TestClient) -> None:
    fact_response = client.post(
        "/v1/facts",
        json={
            "entity": "agent:default",
            "relation": "memory:status",
            "value": {"type": "string", "v": "ok"},
            "source": "agent:test",
            "confidence": 1.0,
            "scope": "local",
        },
    )
    assert fact_response.status_code == 201

    query_response = client.get("/v1/facts", params={"entity": "agent:default"})
    assert query_response.status_code == 200
    assert query_response.json()["facts"][0]["value"]["v"] == "ok"

    absent_paths = {
        "/v1/agents/default/instruction-manifest",
        "/v1/agents/default/boot-stub",
        "/v1/agents/default/recall-instruction",
        "/v1/agents/default/instruction-manifest/coverage",
        "/v1/instruction/audit",
    }
    for path in absent_paths:
        method = (
            client.post
            if path.endswith("audit") or path.endswith("recall-instruction")
            else client.get
        )
        response = method(path)
        assert response.status_code == 404

    openapi_paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/agents/{agent_id}/instruction-manifest" not in openapi_paths
    assert "/v1/agents/{agent_id}/recall-instruction" not in openapi_paths


def test_plugin_loaded_lazy_instruction_discovery_round_trip(
    lazy_plugin_client: TestClient,
) -> None:
    fact_uri = "instruction:default/shared/checkout/v1"
    seed_response = lazy_plugin_client.post(
        "/v1/facts",
        json={
            "entity": fact_uri,
            "relation": "instruction:body",
            "value": {
                "type": "text",
                "v": "Checkout the issue branch, inspect status, and validate before editing.",
            },
            "source": "agent:test",
            "confidence": 1.0,
            "scope": "local",
        },
    )
    assert seed_response.status_code == 201

    publish_response = lazy_plugin_client.put(
        "/v1/agents/test-agent/instruction-manifest",
        json={
            "version": "v1",
            "entries": [
                {
                    "name": "checkout",
                    "description": "Checkout and validate issue work",
                    "fact_uri": fact_uri,
                    "load_triggers": {
                        "intents": ["checkout issue branch"],
                        "keywords": ["checkout", "branch"],
                    },
                }
            ],
        },
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["fact_uri"].endswith("/manifest/v1")

    manifest_response = lazy_plugin_client.get("/v1/agents/test-agent/instruction-manifest")
    assert manifest_response.status_code == 200
    manifest_body = manifest_response.json()
    assert manifest_body["manifest_version"] == "v1"
    assert manifest_body["entries"][0]["name"] == "checkout"

    stub_response = lazy_plugin_client.get("/v1/agents/test-agent/boot-stub")
    assert stub_response.status_code == 200
    assert "recall_instruction" in stub_response.text
    assert stub_response.headers["X-Manifest-Version"] == "v1"

    recall_response = lazy_plugin_client.post(
        "/v1/agents/test-agent/recall-instruction",
        json={"intent": "checkout the issue branch before editing"},
    )
    assert recall_response.status_code == 200
    recall_body = recall_response.json()
    assert recall_body["chunks"][0]["name"] == "checkout"
    assert "Checkout the issue branch" in recall_body["chunks"][0]["content"]
    assert recall_body["audit_token"].startswith("audi_")

    audit_response = lazy_plugin_client.post(
        "/v1/instruction/audit",
        json={"audit_token": recall_body["audit_token"], "used_chunks": ["checkout"]},
    )
    assert audit_response.status_code == 204

    coverage_response = lazy_plugin_client.get(
        "/v1/agents/test-agent/instruction-manifest/coverage"
    )
    assert coverage_response.status_code == 200
    coverage_body = coverage_response.json()
    assert coverage_body["manifest_version"] == "v1"
    assert coverage_body["units"][0]["name"] == "checkout"
    assert coverage_body["units"][0]["coverage_status"] in {
        "ok",
        "coverage_critical",
        "not_evaluated",
    }


def test_lazy_instruction_plugin_hook_order_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plugin_registry, "_current_stigmem_version", lambda: "0.9.0a3")
    calls: list[str] = []
    manifest = _recording_manifest(calls)
    registry = HookRegistry()

    def core_authorize(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("core:pre_recall_authorize")
        return Allow()

    def core_rewrite(
        _ctx: PluginContext, value: dict[str, object], **_: object
    ) -> dict[str, object]:
        calls.append("core:pre_recall_rewrite")
        return value

    def core_filter(_ctx: PluginContext, value: list[str], **_: object) -> list[str]:
        calls.append("core:recall_filter")
        return value

    def core_migration(_ctx: PluginContext, value: list[object], **_: object) -> list[object]:
        calls.append("core:migration_register")
        return value

    def core_audit(_ctx: PluginContext, **_: object) -> None:
        calls.append("core:post_recall_audit")

    registry.register_core_handler(
        "pre_recall_authorize", core_authorize, name="core.001.authorize"
    )
    registry.register_core_handler("pre_recall_rewrite", core_rewrite, name="core.001.rewrite")
    registry.register_core_handler("recall_filter", core_filter, name="core.001.filter")
    registry.register_core_handler(
        "migration_register", core_migration, name="core.001.migration"
    )
    registry.register_core_handler("post_recall_audit", core_audit, name="core.001.audit")
    registry.register_plugin(manifest)

    assert _handler_names(registry, "pre_recall_authorize") == (
        "core.001.authorize",
        f"{PLUGIN_NAME}.pre_recall_authorize",
    )
    assert _handler_names(registry, "pre_recall_rewrite") == (
        f"{PLUGIN_NAME}.pre_recall_rewrite",
        "core.001.rewrite",
    )
    assert _handler_names(registry, "recall_filter") == (
        f"{PLUGIN_NAME}.recall_filter",
        "core.001.filter",
    )
    assert _handler_names(registry, "migration_register") == (
        "core.001.migration",
        f"{PLUGIN_NAME}.migration_register",
    )
    assert _handler_names(registry, "post_recall_audit") == (
        "core.001.audit",
        f"{PLUGIN_NAME}.post_recall_audit",
    )

    registry.fire_voting("pre_recall_authorize")
    registry.fire_filter_chain("pre_recall_rewrite", {"intent": "checkout"})
    registry.fire_filter_chain("recall_filter", ["fact-1"])
    registry.fire_filter_chain("migration_register", [])
    registry.fire_fire_and_forget("post_recall_audit")

    assert calls == [
        "core:pre_recall_authorize",
        "plugin:pre_recall_authorize",
        "plugin:pre_recall_rewrite",
        "core:pre_recall_rewrite",
        "plugin:recall_filter",
        "core:recall_filter",
        "core:migration_register",
        "plugin:migration_register",
        "core:post_recall_audit",
        "plugin:post_recall_audit",
    ]


def _recording_manifest(calls: list[str]) -> PluginManifest:
    manifest = plugin_manifest()
    hooks: dict[str, Callable[..., Any]] = {}
    for hook_name, handler in manifest.hooks.items():
        hooks[hook_name] = _recording_handler(hook_name, handler, calls)
    return manifest.model_copy(update={"hooks": hooks})


def _recording_handler(
    hook_name: str,
    handler: Callable[..., T],
    calls: list[str],
) -> Callable[..., T]:
    def wrapper(ctx: PluginContext, *args: object, **kwargs: object) -> T:
        calls.append(f"plugin:{hook_name}")
        return handler(ctx, *args, **kwargs)

    wrapper.__name__ = handler.__name__
    return wrapper


def _handler_names(registry: HookRegistry, hook_name: str) -> tuple[str, ...]:
    return tuple(entry.handler_name for entry in registry.handlers_for(hook_name))
