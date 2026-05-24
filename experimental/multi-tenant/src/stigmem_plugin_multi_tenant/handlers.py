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
from stigmem_node.tenant import TenantIdError, validate_tenant_id

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
    """Resolve non-default tenants only when the plugin is explicitly enabled.

    When ``STIGMEM_MULTI_TENANT_ENABLED`` is false, this hook returns the
    inbound context unchanged. When enabled, it validates and normalizes the
    candidate tenant ID before promoting the context to ``resolved``.
    """

    config = load_config_from_env()
    if not config.enabled:
        return value

    identity = kwargs.get("identity")
    tenant_id = getattr(identity, "tenant_id", None)
    if not tenant_id:
        tenant_id = value.metadata.get("source_tenant_id")
    if not tenant_id:
        return value
    try:
        normalized_tenant_id = validate_tenant_id(str(tenant_id))
    except TenantIdError:
        return value
    return TenantContext(
        tenant_id=normalized_tenant_id,
        metadata={
            **value.metadata,
            "tenant_context_source": "resolved",
            "resolved_by": "stigmem-plugin-multi-tenant",
        },
    )


def pre_assert_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Acknowledge core-enforced tenant write authorization.

    Behavior is identical regardless of ``STIGMEM_MULTI_TENANT_ENABLED``:
    this hook always returns ``Allow()`` because tenant isolation is enforced by
    core write paths. The plugin contributes tenant resolution, not write
    authorization.
    """

    return Allow()


def pre_recall_authorize(_ctx: PluginContext, **_: Any) -> Allow:
    """Acknowledge core-enforced tenant recall authorization.

    Behavior is identical regardless of ``STIGMEM_MULTI_TENANT_ENABLED``:
    this hook always returns ``Allow()`` because tenant isolation is enforced by
    core recall paths. The plugin contributes tenant resolution, not recall
    authorization.
    """

    return Allow()


def recall_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return recall/query results unchanged after core tenant filtering.

    With the gate disabled or enabled, this hook is a pass-through because core
    recall/query SQL already filters by the resolved request tenant.
    """

    return value


def federation_outbound_filter(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return outbound federation batches unchanged after core tenant filtering.

    With the gate disabled or enabled, this hook is a pass-through because
    v0.9.0a8 node-level federation is pinned to the default tenant by core.
    """

    return value


def migration_register(_ctx: PluginContext, value: T, **_: Any) -> T:
    """Return core/plugin migrations unchanged.

    With the gate disabled or enabled, this hook is a pass-through.
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
