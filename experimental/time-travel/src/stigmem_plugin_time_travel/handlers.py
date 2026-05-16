"""Hook handlers for the time-travel query plugin scaffold."""

from __future__ import annotations

from typing import Any, TypeVar

from stigmem_node.plugins import Allow, Deny, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")


def pre_recall_authorize(_ctx: PluginContext, **kwargs: Any) -> Allow | Deny:
    """Fail closed for historical queries until issue #310 wires plugin behavior."""

    query = kwargs.get("query")
    if isinstance(query, dict) and query.get("as_of") is not None:
        return Deny("time_travel_plugin_not_enabled")
    return Allow()


def pre_recall_rewrite(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Preserve recall payloads until the implementation issue adds query shaping."""

    return value


def post_recall_audit(_ctx: PluginContext, **_: Any) -> None:
    """Audit hook placeholder for historical query outcomes."""

    return None


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report plugin health for operator plugin inspection."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="time-travel plugin scaffold registered",
    )
