"""Typed hook payload and return helper types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, TypeAlias, TypeVar, cast

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Allow:
    """Voting hook allow decision."""


@dataclass(frozen=True, slots=True)
class Deny:
    """Voting hook deny decision."""

    reason: str


VotingDecision: TypeAlias = Allow | Deny
ALLOW_SINGLETON = Allow()


@dataclass(frozen=True, slots=True)
class Success:
    """Audit outcome for successful operations."""


@dataclass(frozen=True, slots=True)
class Failure:
    """Audit outcome for failed operations."""

    reason: str
    exception_type: str | None = None


Outcome: TypeAlias = Success | Failure


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Resolved tenant context passed through hook payloads."""

    tenant_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


SYSTEM_TENANT = TenantContext(tenant_id="system")


@dataclass(frozen=True, slots=True)
class Migration:
    """Schema migration declared by core or a plugin."""

    plugin_name: str
    migration_id: int
    sql: str
    description: str
    plugin_version: str = "0.0.0"
    backend: str = "sqlite"


class PluginHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PluginHealth:
    """Result returned by a plugin lifecycle health check."""

    status: PluginHealthStatus
    message: str = ""


@dataclass(frozen=True, slots=True)
class PluginHealthReport:
    """Last observed lifecycle health state for one plugin."""

    plugin_name: str
    plugin_version: str
    status: PluginHealthStatus
    message: str
    checked_at: datetime
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Normalized plugin audit event payload."""

    event_type: str
    actor_uri: str
    target_uri: str | None
    tenant_id: str
    timestamp: datetime
    outcome: Outcome
    metadata: dict[str, Any] = field(default_factory=dict)


class VotingHandler(Protocol):
    def __call__(self, ctx: object, **kwargs: Any) -> VotingDecision:
        pass


class FilterChainHandler(Protocol[T]):
    def __call__(self, ctx: object, value: T, **kwargs: Any) -> T:
        pass


class ScoreDeltaHandler(Protocol):
    def __call__(self, ctx: object, scored_results: list[Any], **kwargs: Any) -> dict[str, float]:
        pass


class FireAndForgetHandler(Protocol):
    def __call__(self, ctx: object, **kwargs: Any) -> None:
        pass


def handler_timeout(seconds: float) -> Callable[[T], T]:
    """Annotate a handler with a per-invocation timeout in seconds."""
    if seconds <= 0:
        raise ValueError("handler timeout must be positive")
    if seconds > 30:
        raise ValueError("handler timeout cannot exceed 30 seconds")

    def decorate(handler: T) -> T:
        cast(Any, handler).__plugin_timeout__ = float(seconds)
        return handler

    return cast(Callable[[T], T], decorate)
