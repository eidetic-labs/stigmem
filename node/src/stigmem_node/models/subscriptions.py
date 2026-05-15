"""Subscription models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

VALID_ON_CHANGE = {"webhook", "wake"}


class SubscriptionCreateRequest(BaseModel):
    target: str = Field(
        ...,
        min_length=1,
        description="Scope name (e.g. 'local') or entity URI to watch",
    )
    on_change: str = Field(..., description="'webhook' or 'wake'")
    delivery_address: str = Field(
        ...,
        min_length=1,
        description="Webhook URL (on_change=webhook) or identity URI (on_change=wake)",
    )
    idempotency_key: str | None = Field(None, description="Optional client idempotency key")

    @field_validator("on_change")
    @classmethod
    def check_on_change(cls, v: str) -> str:
        if v not in VALID_ON_CHANGE:
            raise ValueError(f"on_change must be one of {VALID_ON_CHANGE}")
        return v


class SubscriptionRecord(BaseModel):
    id: str
    subscriber_identity: str
    target: str
    target_kind: str
    on_change: str
    delivery_address: str
    idempotency_key: str | None
    created_at: str
    last_delivered_at: str | None
    circuit_open: bool
    consecutive_failures: int


class SubscriptionEventRecord(BaseModel):
    id: str
    subscription_id: str
    event_type: str
    entity_uri: str | None
    fact_id: str | None
    payload: dict[str, Any]
    created_at: str
    delivered_at: str | None
    delivery_status: str
    delivery_attempts: int


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionRecord]
    total: int


class SubscriptionEventsResponse(BaseModel):
    events: list[SubscriptionEventRecord]
    total: int
    cursor: str | None

