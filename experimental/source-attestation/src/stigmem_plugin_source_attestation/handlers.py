"""Hook handlers for the source-attestation plugin scaffold."""

from __future__ import annotations

from typing import Any

from stigmem_node.plugins import Allow, PluginContext, PluginHealth, PluginHealthStatus


def pre_assert_validate(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow assertions until attestation enforcement is configured."""

    return Allow()


def recall_rank(_ctx: PluginContext, _scored_results: list[Any], **_: Any) -> dict[str, float]:
    """Return no score deltas until source-trust ranking is configured."""

    return {}


def federation_inbound_validate(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow inbound federation until attestation enforcement is configured."""

    return Allow()


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for registry lifecycle tests."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="source attestation plugin scaffold registered",
    )
