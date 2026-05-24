"""Hook handlers for the lazy instruction discovery plugin."""

from __future__ import annotations

from importlib import resources
from typing import Any, TypeVar

from stigmem_node.plugins import Allow, Migration, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")
PLUGIN_NAME = "stigmem-plugin-lazy-instruction-discovery"
PLUGIN_VERSION = "0.1.0"


def pre_recall_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Allow by default until issue #291 moves instruction-specific checks here."""

    return Allow()


def pre_recall_rewrite(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Preserve recall payloads until issue #291 adds instruction query shaping."""

    return value


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Preserve recall results until issue #291 adds instruction eligibility filters."""

    return value


def post_recall_audit(_ctx: PluginContext, **_: Any) -> None:
    """Audit hook placeholder; discovery audit writes move here in issue #291."""


def migration_register(_ctx: PluginContext, value: list[Migration], **_: Any) -> list[Migration]:
    """Declare the plugin-owned instruction-discovery schema migration."""

    sql = resources.files(__package__).joinpath(
        "migrations/001_instruction_discovery.sql"
    ).read_text(encoding="utf-8")
    return [
        *value,
        Migration(
            plugin_name=PLUGIN_NAME,
            plugin_version=PLUGIN_VERSION,
            migration_id=1,
            backend="sqlite",
            sql=sql,
            description="lazy instruction discovery schema",
        ),
    ]


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report plugin health for operator plugin inspection."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="lazy instruction discovery plugin registered",
    )
