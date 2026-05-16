"""Inert hook handlers for the PR 4a plugin scaffold.

The scaffold deliberately registers the final hook boundary without moving route
behavior yet. Issue #291 owns the extraction of active lazy-instruction
behavior into these handlers.
"""

from __future__ import annotations

from typing import Any, TypeVar

from stigmem_node.plugins import Allow, Migration, PluginContext, PluginHealth, PluginHealthStatus

T = TypeVar("T")


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
    """Return unchanged migrations until plugin-owned schema moves in issue #291."""

    return value


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for operator plugin inspection."""

    return PluginHealth(
        status=PluginHealthStatus.DEGRADED,
        message="lazy instruction discovery scaffold registered; behavior extraction pending",
    )
