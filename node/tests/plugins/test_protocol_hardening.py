from __future__ import annotations

from collections.abc import Callable

import pytest

import stigmem_node.plugins.lifecycle as lifecycle
from stigmem_node.plugins import (
    Allow,
    Deny,
    DiscoveredPlugin,
    HookRegistry,
    PluginContext,
    PluginExecutionError,
    PluginManifest,
)


def _manifest(name: str, hooks: dict[str, Callable[..., object]]) -> PluginManifest:
    return PluginManifest(name=name, version="1.0.0", hooks=hooks)


def _discovered(manifest: PluginManifest) -> DiscoveredPlugin:
    return DiscoveredPlugin(
        manifest=manifest,
        entry_point_name=manifest.name,
        entry_point_value=f"{manifest.name}:plugin_manifest",
        distribution=f"{manifest.name}-dist",
    )


def _register_discovered(
    monkeypatch: pytest.MonkeyPatch,
    registry: HookRegistry,
    *manifests: PluginManifest,
) -> None:
    monkeypatch.setattr(
        lifecycle,
        "discover_plugin_manifests",
        lambda: tuple(_discovered(manifest) for manifest in manifests),
    )
    lifecycle.register_discovered_plugins(
        registry=registry,
        freeze=False,
        signing_required=False,
    )


def test_discovered_voting_hook_stops_on_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def allow(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("allow")
        return Allow()

    def deny(_ctx: PluginContext, **_: object) -> Deny:
        calls.append("deny")
        return Deny("blocked")

    def never(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("never")
        return Allow()

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("aaa-plugin", {"pre_assert_authorize": allow}),
        _manifest("bbb-plugin", {"pre_assert_authorize": deny}),
        _manifest("ccc-plugin", {"pre_assert_authorize": never}),
    )

    assert registry.fire_voting("pre_assert_authorize") == Deny("blocked")
    assert calls == ["allow", "deny"]


def test_discovered_voting_hook_fails_closed_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def explode(_ctx: PluginContext, **_: object) -> Allow:
        raise RuntimeError("boom")

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("bad-plugin", {"pre_assert_authorize": explode}),
    )

    with pytest.raises(PluginExecutionError, match="failed for hook 'pre_assert_authorize'"):
        registry.fire_voting("pre_assert_authorize")


def test_discovered_filter_chain_threads_values(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = HookRegistry()

    def add_a(_ctx: PluginContext, value: str, **_: object) -> str:
        return value + "a"

    def add_b(_ctx: PluginContext, value: str, **_: object) -> str:
        return value + "b"

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("bbb-plugin", {"recall_filter": add_b}),
        _manifest("aaa-plugin", {"recall_filter": add_a}),
    )

    assert registry.fire_filter_chain("recall_filter", "") == "ab"


def test_discovered_filter_chain_fails_closed_on_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def invalid(_ctx: PluginContext, _value: str, **_: object) -> None:
        return None

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("bad-plugin", {"recall_filter": invalid}),
    )

    with pytest.raises(PluginExecutionError, match="returned None"):
        registry.fire_filter_chain("recall_filter", "fact")


def test_discovered_score_delta_combines_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = HookRegistry()

    def rank_one(
        _ctx: PluginContext, _scored_results: list[object], **_: object
    ) -> dict[str, float]:
        return {"fact-1": 1.25}

    def rank_two(
        _ctx: PluginContext, _scored_results: list[object], **_: object
    ) -> dict[str, float]:
        return {"fact-1": 0.75, "fact-2": -1.0}

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("aaa-plugin", {"recall_rank": rank_one}),
        _manifest("bbb-plugin", {"recall_rank": rank_two}),
    )

    assert registry.fire_score_delta("recall_rank", []) == {"fact-1": 2.0, "fact-2": -1.0}


def test_discovered_score_delta_fails_closed_on_invalid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def invalid(_ctx: PluginContext, _scored_results: list[object], **_: object) -> list[str]:
        return ["not-a-delta-map"]

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("bad-plugin", {"recall_rank": invalid}),
    )

    with pytest.raises(PluginExecutionError, match="expected dict"):
        registry.fire_score_delta("recall_rank", [])


def test_discovered_fire_and_forget_invokes_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def persist(_ctx: PluginContext, **_: object) -> None:
        calls.append("persist")

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("persist-plugin", {"post_assert_persist": persist}),
    )

    registry.fire_fire_and_forget("post_assert_persist")

    assert calls == ["persist"]


def test_discovered_strict_audit_fire_and_forget_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = HookRegistry()

    def explode(_ctx: PluginContext, **_: object) -> None:
        raise RuntimeError("boom")

    _register_discovered(
        monkeypatch,
        registry,
        _manifest("audit-plugin", {"audit_emit": explode}),
    )

    with pytest.raises(PluginExecutionError, match="audit hook 'audit_emit'"):
        registry.fire_fire_and_forget("audit_emit")
