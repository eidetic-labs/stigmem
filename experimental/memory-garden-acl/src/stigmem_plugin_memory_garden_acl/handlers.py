"""Hook handlers for the Memory Garden advanced ACL plugin scaffold."""

from __future__ import annotations

from typing import Any, TypeVar

from stigmem_node.plugins import Allow, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")
PLUGIN_NAME = "stigmem-plugin-memory-garden-acl"


def pre_assert_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Stub: scaffold returns Allow().

    A future implementation is expected to enforce write-side garden membership
    for advanced ACL policy. If this scaffold handler raises, returns ``None``,
    or the plugin fails to load, the core hook path remains fail-open. Core fallback:
    direct ``garden_id`` writes are still governed by the
    ``require_garden_write`` guard. Operators relying on advanced write-side
    enforcement must verify the plugin is registered, healthy, and configured
    for their deployment.
    """

    return Allow()


def pre_recall_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Stub: scaffold returns Allow().

    A future implementation is expected to authorize advanced recall access
    before ranking or traversal. If this scaffold handler raises, returns
    ``None``, or the plugin fails to load, the hook path remains fail-open and
    core fallback behavior applies: direct garden reads are guarded, while
    tenant-wide recall authorization is not narrowed by this plugin.
    """

    return Allow()


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Stub: scaffold preserves the incoming recall value.

    A future implementation is expected to remove facts and graph edges the
    caller cannot see through advanced garden membership. If this scaffold
    handler raises, returns ``None``, or the plugin fails to load, filtering
    remains fail-open. Core fallback behavior still protects explicit
    ``garden_id`` reads, but tenant-wide queries, recall ranking, subscription
    delivery, and graph traversal are not filtered by advanced ACL policy.
    """

    return value


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for registry lifecycle tests."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="memory garden ACL plugin scaffold registered",
    )
