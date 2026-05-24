"""Hook handlers for the RTBF tombstone plugin scaffold."""

from __future__ import annotations

from importlib import resources
from typing import Any, TypeVar

from stigmem_node.plugins import Allow, Migration, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")
PLUGIN_NAME = "stigmem-plugin-tombstones"
PLUGIN_VERSION = "0.1.0"


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Preserve recall results unless plugin-loaded legacy filtering is configured."""

    return value


def federation_inbound_validate(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow inbound federation unless plugin-loaded signature validation is configured."""

    return Allow()


def post_assert_propagate(_ctx: PluginContext, **_: Any) -> None:
    """Propagation placeholder for tombstone and revocation peer fan-out."""


def migration_register(_ctx: PluginContext, value: list[Migration], **_: Any) -> list[Migration]:
    """Declare the plugin-owned tombstone schema migration."""

    sql = resources.files(__package__).joinpath("migrations/001_tombstones.sql").read_text(
        encoding="utf-8"
    )
    return [
        *value,
        Migration(
            plugin_name=PLUGIN_NAME,
            plugin_version=PLUGIN_VERSION,
            migration_id=1,
            backend="sqlite",
            sql=sql,
            description="RTBF tombstone schema",
        ),
    ]


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report plugin health for operator plugin inspection."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="tombstone plugin scaffold registered",
    )
