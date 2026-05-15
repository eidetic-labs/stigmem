from __future__ import annotations

import time

import pytest

import stigmem_node.plugins.registry as registry_module
from stigmem_node.plugins import (
    Allow,
    AuditEvent,
    CapabilityError,
    Deny,
    HookName,
    HookRegistry,
    ManifestError,
    PluginContext,
    PluginExecutionError,
    PluginHealth,
    PluginHealthStatus,
    PluginManifest,
    RegistryFrozenError,
    get_registry,
    handler_timeout,
)
from stigmem_node.plugins.hooks import HOOK_SPECS
from stigmem_node.plugins.testing import stigmem_plugins


class _MetricRecorder:
    def __init__(self) -> None:
        self.increments: list[dict[str, str]] = []
        self.observations: list[tuple[dict[str, str], float]] = []
        self.values: list[tuple[dict[str, str], int]] = []
        self._labels: dict[str, str] = {}

    def labels(self, **labels: str) -> _MetricRecorder:
        child = _MetricRecorder()
        child.increments = self.increments
        child.observations = self.observations
        child.values = self.values
        child._labels = labels
        return child

    def inc(self) -> None:
        self.increments.append(self._labels)

    def observe(self, value: float) -> None:
        self.observations.append((self._labels, value))

    def set(self, value: int) -> None:
        self.values.append((self._labels, value))


def _manifest(
    name: str,
    hooks: dict[str, object],
    *,
    capabilities: frozenset[str] = frozenset(),
    requires_stigmem: str = ">=0.9.0a1",
    health_check: object | None = None,
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        requires_stigmem=requires_stigmem,
        capabilities=capabilities,
        async_safe=True,
        hooks=hooks,
        health_check=health_check,
    )


def test_voting_first_deny_stops_dispatch() -> None:
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

    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": allow}))
    registry.register_plugin(_manifest("bbb", {"pre_assert_authorize": deny}))
    registry.register_plugin(_manifest("ccc", {"pre_assert_authorize": never}))

    result = registry.fire_voting("pre_assert_authorize")

    assert result == Deny("blocked")
    assert calls == ["allow", "deny"]


def test_stable_hook_surface_is_22_hooks() -> None:
    assert len(HOOK_SPECS) == 22
    assert {hook.value for hook in HookName} == set(HOOK_SPECS)
    assert "health_check" not in HOOK_SPECS
    assert "decay_sweep_filter" not in HOOK_SPECS


def test_empty_voting_allows() -> None:
    assert isinstance(HookRegistry().fire_voting("pre_assert_authorize"), Allow)


def test_empty_protocol_defaults_are_explicit() -> None:
    registry = HookRegistry()

    assert registry.fire_filter_chain("recall_filter", ["fact"]) == ["fact"]
    assert registry.fire_score_delta("recall_rank", [{"id": "fact"}]) == {}
    registry.fire_fire_and_forget("post_assert_persist")


def test_filter_chain_threads_value_in_order() -> None:
    registry = HookRegistry()

    def add_a(_ctx: PluginContext, value: str, **_: object) -> str:
        return value + "a"

    def add_b(_ctx: PluginContext, value: str, **_: object) -> str:
        return value + "b"

    registry.register_plugin(_manifest("bbb", {"recall_filter": add_b}))
    registry.register_plugin(_manifest("aaa", {"recall_filter": add_a}))

    assert registry.fire_filter_chain("recall_filter", "") == "ab"


def test_score_delta_sums_handler_results() -> None:
    registry = HookRegistry()

    def rank_one(
        _ctx: PluginContext, _scored_results: list[object], **_: object
    ) -> dict[str, float]:
        return {"fact-1": 1.25}

    def rank_two(
        _ctx: PluginContext, _scored_results: list[object], **_: object
    ) -> dict[str, float]:
        return {"fact-1": 0.75, "fact-2": -1.0}

    registry.register_plugin(_manifest("aaa", {"recall_rank": rank_one}))
    registry.register_plugin(_manifest("bbb", {"recall_rank": rank_two}))

    assert registry.fire_score_delta("recall_rank", []) == {"fact-1": 2.0, "fact-2": -1.0}


def test_fire_and_forget_logs_non_audit_errors(caplog: pytest.LogCaptureFixture) -> None:
    registry = HookRegistry()

    def explode(_ctx: PluginContext, **_: object) -> None:
        raise RuntimeError("boom")

    registry.register_plugin(_manifest("aaa", {"post_assert_persist": explode}))

    registry.fire_fire_and_forget("post_assert_persist")

    assert "failed for hook" in caplog.text


def test_fire_and_forget_escalates_strict_audit_errors() -> None:
    registry = HookRegistry()

    def explode(_ctx: PluginContext, **_: object) -> None:
        raise RuntimeError("boom")

    registry.register_plugin(_manifest("aaa", {"audit_emit": explode}))

    with pytest.raises(PluginExecutionError, match="audit hook"):
        registry.fire_fire_and_forget("audit_emit")


def test_core_first_and_plugins_first_ordering() -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def core(_ctx: PluginContext, value: str | None = None, **_: object) -> str | None:
        calls.append("core")
        return value

    def plugin(_ctx: PluginContext, value: str | None = None, **_: object) -> str | None:
        calls.append("plugin")
        return value

    registry.register_plugin(_manifest("aaa", {"identity_resolve": plugin}))
    registry.register_core_handler("identity_resolve", core, name="core.001.identity")
    registry.fire_filter_chain("identity_resolve", "creds")
    assert calls == ["core", "plugin"]

    calls.clear()
    registry = HookRegistry()
    registry.register_plugin(_manifest("aaa", {"pre_assert_transform": plugin}))
    registry.register_core_handler("pre_assert_transform", core, name="core.001.cid")
    registry.fire_filter_chain("pre_assert_transform", "fact")
    assert calls == ["plugin", "core"]


def test_core_only_default_and_plugin_only_ordering() -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def core(_ctx: PluginContext, **_: object) -> None:
        calls.append("core")

    def plugin(_ctx: PluginContext, **_: object) -> None:
        calls.append("plugin")

    registry.register_plugin(_manifest("aaa", {"post_assert_audit": plugin}))
    registry.register_core_handler("post_assert_audit", core, name="core.001.audit")
    registry.fire_fire_and_forget("post_assert_audit")
    assert calls == ["core", "plugin"]

    calls.clear()
    registry = HookRegistry()
    registry.register_core_handler("post_assert_persist", core, name="core.001.persist")
    registry.register_plugin(_manifest("aaa", {"post_assert_persist": plugin}))
    registry.fire_fire_and_forget("post_assert_persist")
    assert calls == ["plugin", "core"]


def test_manifest_rejects_unknown_hook_and_capability() -> None:
    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    with pytest.raises(ValueError, match="unknown plugin hooks"):
        _manifest("aaa", {"recal_filter": handler})

    with pytest.raises(ValueError, match="unknown plugin capabilities"):
        _manifest("aaa", {}, capabilities=frozenset({"facts.teleport"}))


def test_register_plugin_rejects_incompatible_stigmem_version() -> None:
    registry = HookRegistry()

    with pytest.raises(ManifestError, match="requires stigmem"):
        registry.register_plugin(_manifest("aaa", {}, requires_stigmem=">=999.0.0"))


def test_register_plugin_rejects_invalid_version_specifier() -> None:
    registry = HookRegistry()

    with pytest.raises(ManifestError, match="invalid requires_stigmem"):
        registry.register_plugin(_manifest("aaa", {}, requires_stigmem="not-a-specifier"))


def test_register_plugin_rejects_wrong_handler_shape() -> None:
    registry = HookRegistry()

    def bad_filter(*, value: str) -> str:
        return value

    with pytest.raises(ManifestError, match="must accept at least 2 positional arguments"):
        registry.register_plugin(_manifest("aaa", {"recall_filter": bad_filter}))


def test_duplicate_plugin_name_rejected() -> None:
    registry = HookRegistry()
    registry.register_plugin(_manifest("aaa", {}))

    with pytest.raises(ManifestError, match="already registered"):
        registry.register_plugin(_manifest("aaa", {}))


def test_plugin_health_check_reports_healthy() -> None:
    registry = HookRegistry()

    def health(ctx: PluginContext) -> PluginHealth:
        assert ctx.plugin_name == "aaa"
        return PluginHealth(PluginHealthStatus.HEALTHY, "ready")

    registry.register_plugin(_manifest("aaa", {}, health_check=health))

    reports = registry.poll_plugin_health()

    assert len(reports) == 1
    assert reports[0].plugin_name == "aaa"
    assert reports[0].plugin_version == "1.0.0"
    assert reports[0].status == PluginHealthStatus.HEALTHY
    assert reports[0].message == "ready"
    assert reports[0].error_summary is None
    assert registry.plugin_health_reports() == reports


def test_plugin_health_check_reports_degraded_and_unhealthy() -> None:
    registry = HookRegistry()

    def degraded(_ctx: PluginContext) -> PluginHealth:
        return PluginHealth(PluginHealthStatus.DEGRADED, "remote dependency slow")

    def unhealthy(_ctx: PluginContext) -> PluginHealth:
        return PluginHealth(PluginHealthStatus.UNHEALTHY, "remote dependency down")

    registry.register_plugin(_manifest("aaa", {}, health_check=degraded))
    registry.register_plugin(_manifest("bbb", {}, health_check=unhealthy))

    reports = {report.plugin_name: report for report in registry.poll_plugin_health()}

    assert reports["aaa"].status == PluginHealthStatus.DEGRADED
    assert reports["aaa"].message == "remote dependency slow"
    assert reports["bbb"].status == PluginHealthStatus.UNHEALTHY
    assert reports["bbb"].message == "remote dependency down"


def test_plugin_health_check_exception_reports_unhealthy_without_disabling() -> None:
    registry = HookRegistry()
    calls: list[str] = []

    def health(_ctx: PluginContext) -> PluginHealth:
        raise RuntimeError("boom")

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        calls.append("handler")
        return Allow()

    registry.register_plugin(
        _manifest("aaa", {"pre_assert_authorize": handler}, health_check=health)
    )

    reports = registry.poll_plugin_health()

    assert reports[0].status == PluginHealthStatus.UNHEALTHY
    assert reports[0].message == "boom"
    assert reports[0].error_summary == "RuntimeError: boom"
    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)
    assert calls == ["handler"]


def test_plugin_without_health_check_reports_unknown() -> None:
    registry = HookRegistry()
    registry.register_plugin(_manifest("aaa", {}))

    reports = registry.poll_plugin_health()

    assert reports[0].status == PluginHealthStatus.UNKNOWN
    assert reports[0].message == "no health check registered"


def test_config_validate_core_handler_can_reject_registration() -> None:
    registry = HookRegistry()

    def reject(_ctx: PluginContext, **_: object) -> Deny:
        return Deny("bad config")

    registry.register_core_handler("config_validate", reject, name="core.001.config")

    with pytest.raises(ManifestError, match="bad config"):
        registry.register_plugin(_manifest("aaa", {}))


def test_plugin_config_validate_handler_can_reject_its_own_registration() -> None:
    registry = HookRegistry()

    def reject(_ctx: PluginContext, **_: object) -> Deny:
        return Deny("plugin config invalid")

    with pytest.raises(ManifestError, match="plugin config invalid"):
        registry.register_plugin(_manifest("aaa", {"config_validate": reject}))


def test_registry_freeze_rejects_late_registration() -> None:
    registry = HookRegistry()

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))
    registry.freeze()

    with pytest.raises(RegistryFrozenError, match="registry is frozen"):
        registry.register_plugin(_manifest("bbb", {"pre_assert_authorize": handler}))

    with pytest.raises(RegistryFrozenError, match="registry is frozen"):
        registry.register_core_handler("pre_assert_authorize", handler, name="core.001.authz")


def test_handlers_are_tuple_backed_after_freeze() -> None:
    registry = HookRegistry()

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))
    registry.freeze()

    assert isinstance(registry.handlers_for("pre_assert_authorize"), tuple)


def test_capability_accessor_requires_manifest_declaration() -> None:
    registry = HookRegistry()
    captured: list[object] = []

    def handler(ctx: PluginContext, **_: object) -> None:
        captured.append(ctx)

    registry.register_plugin(
        _manifest("aaa", {"post_assert_persist": handler}, capabilities=frozenset({"audit.emit"}))
    )
    registry.fire_fire_and_forget("post_assert_persist")
    ctx = captured[0]
    assert isinstance(ctx, PluginContext)

    with pytest.raises(CapabilityError, match="facts.read"):
        ctx.get_facts_reader()

    ctx.get_audit_emitter()


def test_stigmem_plugins_context_restores_registry() -> None:
    original = get_registry()

    with stigmem_plugins([_manifest("aaa", {})]) as registry:
        assert get_registry() is registry
        assert registry.registered_plugins() == frozenset({"aaa"})

    assert get_registry() is original


def test_registry_emits_registration_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    registration = _MetricRecorder()
    registered_count = _MetricRecorder()
    handlers_per_hook = _MetricRecorder()
    monkeypatch.setattr(registry_module, "PLUGIN_REGISTRATION", registration)
    monkeypatch.setattr(registry_module, "PLUGIN_REGISTERED_COUNT", registered_count)
    monkeypatch.setattr(registry_module, "PLUGIN_HANDLERS_PER_HOOK", handlers_per_hook)

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry = HookRegistry(emit_metrics=True)
    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))

    assert {"outcome": "success", "reason": ""} in registration.increments
    assert ({}, 1) in registered_count.values
    assert ({"hook": "pre_assert_authorize"}, 1) in handlers_per_hook.values


def test_registry_emits_dispatch_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    hook_fire = _MetricRecorder()
    handler_invocation = _MetricRecorder()
    handler_duration = _MetricRecorder()
    hook_duration = _MetricRecorder()
    voting_decision = _MetricRecorder()
    monkeypatch.setattr(registry_module, "PLUGIN_HOOK_FIRE", hook_fire)
    monkeypatch.setattr(registry_module, "PLUGIN_HANDLER_INVOCATION", handler_invocation)
    monkeypatch.setattr(registry_module, "PLUGIN_HANDLER_DURATION", handler_duration)
    monkeypatch.setattr(registry_module, "PLUGIN_HOOK_DURATION", hook_duration)
    monkeypatch.setattr(registry_module, "PLUGIN_VOTING_DECISION", voting_decision)

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry = HookRegistry(emit_metrics=True)
    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))

    assert isinstance(registry.fire_voting("pre_assert_authorize"), Allow)

    assert {"hook": "pre_assert_authorize"} in hook_fire.increments
    assert {"hook": "pre_assert_authorize", "plugin": "aaa"} in handler_invocation.increments
    assert {"hook": "pre_assert_authorize", "decision": "allow"} in voting_decision.increments
    assert handler_duration.observations
    assert hook_duration.observations


def test_registry_emits_plugin_registered_audit_event() -> None:
    registry = HookRegistry()
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))

    assert [event.event_type for event in events] == ["plugin.registered"]
    assert events[0].actor_uri == "system:plugin-registry"
    assert events[0].target_uri == "plugin:aaa"
    assert events[0].metadata["plugin_name"] == "aaa"
    assert events[0].metadata["hooks"] == ["pre_assert_authorize"]
    assert events[0].metadata["signed_by"] == "unsigned"
    assert events[0].metadata["discovery_source"] == {"type": "manual"}


def test_registry_emits_plugin_registration_failed_audit_event() -> None:
    registry = HookRegistry()
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))
    events.clear()

    with pytest.raises(ManifestError, match="already registered"):
        registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": handler}))

    assert [event.event_type for event in events] == ["plugin.registration_failed"]
    assert events[0].target_uri == "plugin:aaa"
    assert events[0].metadata["reason"] == "duplicate"


def test_registry_emits_handler_denied_and_error_audit_events() -> None:
    registry = HookRegistry()
    events: list[AuditEvent] = []

    def capture(_ctx: PluginContext, *, event: AuditEvent) -> None:
        events.append(event)

    def deny(_ctx: PluginContext, **_: object) -> Deny:
        return Deny("blocked")

    def explode(_ctx: PluginContext, **_: object) -> None:
        raise RuntimeError("boom")

    registry.register_core_handler("audit_emit", capture, name="core.001.audit")
    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": deny}))
    registry.register_plugin(_manifest("bbb", {"post_assert_persist": explode}))
    events.clear()

    assert registry.fire_voting("pre_assert_authorize") == Deny("blocked")
    registry.fire_fire_and_forget("post_assert_persist")

    assert [event.event_type for event in events] == [
        "plugin.handler_denied",
        "plugin.handler_error",
    ]
    assert events[0].metadata["plugin_name"] == "aaa"
    assert events[0].metadata["reason"] == "blocked"
    assert events[1].metadata["plugin_name"] == "bbb"
    assert events[1].metadata["error_type"] == "RuntimeError"


def test_handler_timeout_decorator_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        handler_timeout(0)

    with pytest.raises(ValueError, match="30 seconds"):
        handler_timeout(31)


def test_handler_timeout_decorator_fails_closed() -> None:
    registry = HookRegistry()

    @handler_timeout(0.001)
    def slow(_ctx: PluginContext, **_: object) -> Allow:
        time.sleep(0.05)
        return Allow()

    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": slow}))

    with pytest.raises(PluginExecutionError, match="timed out|failed for hook"):
        registry.fire_voting("pre_assert_authorize")


def test_registry_default_handler_timeout_fails_closed() -> None:
    registry = HookRegistry(handler_timeout_seconds=0.001)

    def slow(_ctx: PluginContext, value: str, **_: object) -> str:
        time.sleep(0.05)
        return value

    registry.register_plugin(_manifest("aaa", {"recall_filter": slow}))

    with pytest.raises(PluginExecutionError, match="timed out|failed for hook"):
        registry.fire_filter_chain("recall_filter", "value")


def test_invalid_handler_results_fail_closed() -> None:
    registry = HookRegistry()

    def bad_vote(_ctx: PluginContext, **_: object) -> str:
        return "allow"

    registry.register_plugin(_manifest("aaa", {"pre_assert_authorize": bad_vote}))
    with pytest.raises(PluginExecutionError, match="expected Allow or Deny"):
        registry.fire_voting("pre_assert_authorize")

    registry = HookRegistry()

    def bad_filter(_ctx: PluginContext, value: str, **_: object) -> None:
        return None

    registry.register_plugin(_manifest("aaa", {"recall_filter": bad_filter}))
    with pytest.raises(PluginExecutionError, match="returned None"):
        registry.fire_filter_chain("recall_filter", "value")

    registry = HookRegistry()

    def bad_score(_ctx: PluginContext, _results: list[object], **_: object) -> list[str]:
        return ["fact"]

    registry.register_plugin(_manifest("aaa", {"recall_rank": bad_score}))
    with pytest.raises(PluginExecutionError, match="expected dict"):
        registry.fire_score_delta("recall_rank", [])
