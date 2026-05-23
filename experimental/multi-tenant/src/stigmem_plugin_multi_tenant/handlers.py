"""Hook handlers for the multi-tenant plugin."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import ValidationError
from stigmem_node.plugins import (
    Allow,
    Deny,
    PluginContext,
    PluginHealth,
    PluginHealthStatus,
    TenantContext,
)

from .config import load_config_from_env

T = TypeVar("T")


def config_validate(_ctx: PluginContext, **_: Any) -> Allow | Deny:
    """Validate operator gates before the plugin is registered."""

    try:
        load_config_from_env()
    except ValidationError as exc:
        return Deny(f"invalid multi-tenant plugin config: {exc}")
    return Allow()


def tenant_resolve(_ctx: PluginContext, value: TenantContext, **kwargs: Any) -> TenantContext:
    """Resolve non-default tenants only when the plugin is explicitly enabled."""

    config = load_config_from_env()
    if not config.enabled:
        return value

    identity = kwargs.get("identity")
    tenant_id = getattr(identity, "tenant_id", None)
    if not tenant_id:
        tenant_id = value.metadata.get("source_tenant_id")
    if not tenant_id:
        return value
    return TenantContext(
        tenant_id=str(tenant_id),
        metadata={**value.metadata, "resolved_by": "stigmem-plugin-multi-tenant"},
    )


def pre_assert_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Return Allow() because tenant write authorization is enforced by core."""

    return Allow()


def pre_recall_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Return Allow() because tenant recall authorization is enforced by core."""

    return Allow()


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return recall/query results unchanged after core tenant filtering."""

    return value


def federation_outbound_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return outbound federation batches unchanged after core tenant filtering."""

    return value


def migration_register(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return core/plugin migrations unchanged.

    Tenant columns remain part of the core storage compatibility schema so
    existing single-tenant data keeps the `default` partition. The plugin owns
    non-default tenant resolution and validation, not the storage columns.
    """

    return value


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for registry lifecycle tests."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="multi-tenant plugin scaffold registered",
    )
