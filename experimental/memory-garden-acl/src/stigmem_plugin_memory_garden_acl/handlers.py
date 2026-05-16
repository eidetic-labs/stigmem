"""Hook handlers for the Memory Garden advanced ACL plugin scaffold."""

from __future__ import annotations

from typing import Any, TypeVar

from stigmem_node.plugins import Allow, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")
PLUGIN_NAME = "stigmem-plugin-memory-garden-acl"


def pre_assert_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow assertions until advanced garden ACL policy is configured."""

    return Allow()


def pre_recall_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow recall until advanced garden ACL policy is configured."""

    return Allow()


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Preserve recall results until advanced garden filtering is configured."""

    return value


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for registry lifecycle tests."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="memory garden ACL plugin scaffold registered",
    )
