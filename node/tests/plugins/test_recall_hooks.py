from __future__ import annotations

from fastapi.testclient import TestClient

from stigmem_node.plugins import Allow, Deny, PluginContext, PluginManifest
from stigmem_node.plugins.testing import stigmem_plugins

FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:assistant",
    "confidence": 1.0,
    "scope": "company",
}


def test_recall_hooks_fire_in_lifecycle_order(client: TestClient) -> None:
    client.post("/v1/facts", json=FACT)
    calls: list[str] = []

    def authorize(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("authorize")
        return Allow()

    def rewrite(_ctx: PluginContext, value: dict[str, object], **_: object) -> dict[str, object]:
        calls.append("rewrite")
        return value

    def filter_results(_ctx: PluginContext, value: list[object], **_: object) -> list[object]:
        calls.append("filter")
        return value

    def rank(_ctx: PluginContext, _scored_results: list[object], **_: object) -> dict[str, float]:
        calls.append("rank")
        return {}

    def audit(_ctx: PluginContext, **_: object) -> None:
        calls.append("audit")

    manifest = PluginManifest(
        name="recall-tracker",
        version="1.0.0",
        hooks={
            "pre_recall_authorize": authorize,
            "pre_recall_rewrite": rewrite,
            "recall_filter": filter_results,
            "recall_rank": rank,
            "post_recall_audit": audit,
        },
    )

    with stigmem_plugins([manifest]):
        response = client.get("/v1/facts", params={"entity": "user:alice"})

    assert response.status_code == 200
    assert calls == ["authorize", "rewrite", "filter", "rank", "audit"]


def test_recall_authorize_deny_aborts_before_rewrite(client: TestClient) -> None:
    calls: list[str] = []

    def authorize(_ctx: PluginContext, **_: object) -> Deny:
        calls.append("authorize")
        return Deny("recall blocked")

    def rewrite(_ctx: PluginContext, value: dict[str, object], **_: object) -> dict[str, object]:
        calls.append("rewrite")
        return value

    manifest = PluginManifest(
        name="recall-deny",
        version="1.0.0",
        hooks={
            "pre_recall_authorize": authorize,
            "pre_recall_rewrite": rewrite,
        },
    )

    with stigmem_plugins([manifest]):
        response = client.get("/v1/facts")

    assert response.status_code == 403
    assert response.json()["detail"] == "recall blocked"
    assert calls == ["authorize"]
