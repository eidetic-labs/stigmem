"""Hook handlers for the time-travel query plugin scaffold."""

from __future__ import annotations

from typing import Any, TypeVar

from stigmem_node.plugins import Allow, Deny, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")


def pre_recall_authorize(_ctx: PluginContext, **kwargs: Any) -> Allow | Deny:
    """Gate-presence hook for time-travel queries.

    This handler exists to participate in the plugin registry so that
    ``time_travel_gate.require_time_travel_enabled`` resolves to Allow once
    the operator has explicitly enabled the surface. All real authorization
    happens upstream in ``node.routes.time_travel_gate`` (501/403 on missing
    plugin or disabled config) and downstream in ``_recall_as_of_impl`` and
    ``_query_facts_as_of_impl`` (admin/non-admin visibility filtering,
    tombstone, legal-hold, and CID enforcement). This hook MUST NOT duplicate
    those checks or add independent authority, because divergent checks can
    create inconsistent admin determinations across paths.
    """

    return Allow()


def pre_recall_rewrite(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Passthrough hook reserved for future query-shape work.

    Time-travel authorization and visibility enforcement live in the core gate
    and route implementations. This hook MUST NOT rewrite authority-bearing
    fields or duplicate authorization checks; today it only keeps the plugin
    present in the registry for explicitly enabled surfaces.
    """

    return value


def post_recall_audit(_ctx: PluginContext, **_: Any) -> None:
    """Gate-presence audit hook for historical query outcomes.

    Core routes own security audit emission for reads, tombstone/legal-hold
    handling, and federation-integrity rejection. This plugin hook is reserved
    for future plugin-local telemetry and MUST NOT become an alternate audit or
    authorization authority for historical reads.
    """

    return None


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report gate-presence health for operator plugin inspection."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="time-travel plugin scaffold registered",
    )
