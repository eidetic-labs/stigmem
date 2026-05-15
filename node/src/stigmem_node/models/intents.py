"""Intent envelope models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import VALID_SCOPES
from .facts import FactValue

VALID_ESCALATION_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_ESCALATION_CHANNELS = {"stigmem", "email", "slack"}


class Constraint(BaseModel):
    """Hard limit on an intent (Spec-X8-Intent-Envelope)."""

    kind: str = Field(..., min_length=1)
    limit: FactValue
    unit: str | None = None


class Preference(BaseModel):
    """Soft preference on an intent (Spec-X8-Intent-Envelope)."""

    kind: str = Field(..., min_length=1)
    value: FactValue
    weight: float = Field(1.0, ge=0.0, le=1.0)


class DeferenceRule(BaseModel):
    """When to defer to another entity before proceeding (Spec-X8-Intent-Envelope)."""

    condition: str = Field(..., min_length=1)
    defer_to: str = Field(..., min_length=1)
    timeout_s: int | None = Field(None, ge=0)


class EscalationPolicy(BaseModel):
    """Who to notify and how when escalation is required (Spec-X8-Intent-Envelope)."""

    escalate_to: str = Field(..., min_length=1)
    channel: str = Field("stigmem")
    priority: str = Field("medium")
    include_context: bool = True

    @field_validator("priority")
    @classmethod
    def check_priority(cls, p: str) -> str:
        if p not in VALID_ESCALATION_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_ESCALATION_PRIORITIES}")
        return p

    @field_validator("channel")
    @classmethod
    def check_channel(cls, c: str) -> str:
        if c not in VALID_ESCALATION_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_ESCALATION_CHANNELS}")
        return c


class HandoffArtifact(BaseModel):
    """Named artifact reference passed along with a handoff (Spec-X8-Intent-Envelope)."""

    name: str = Field(..., min_length=1)
    ref: str = Field(..., min_length=1, description="URI of the artifact fact")


class HandoffPayload(BaseModel):
    """Structured context transfer for agent handoffs (Spec-X8-Intent-Envelope).

    fact_refs MUST include any facts the receiver needs to reconstitute context.
    """

    summary: str = Field(..., min_length=1)
    fact_refs: list[str] = Field(default_factory=list)
    continuation: str | None = None
    artifacts: list[HandoffArtifact] = Field(default_factory=list)


class IntentEnvelopeRequest(BaseModel):
    """POST /v1/intents request body (Spec-X8-Intent-Envelope).

    The ``from`` field is aliased as ``from_uri`` in Python to avoid the keyword clash.
    Clients MUST send the JSON key ``"from"``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(
        None,
        description="Optional client-generated intent ID (UUID). Auto-assigned when omitted.",
    )
    from_uri: str = Field(..., alias="from", min_length=1, description="Sender entity URI")
    to: list[str] = Field(
        ..., min_length=1, description="Target entity URIs (at least one required)"
    )
    goal: str = Field(..., min_length=1, max_length=2048)
    scope: str = Field("company")
    expires_at: str | None = Field(None, description="ISO 8601 UTC expiry; null = non-expiring")
    constraint: list[Constraint] = Field(default_factory=list)
    preference: list[Preference] = Field(default_factory=list)
    deference: list[DeferenceRule] = Field(default_factory=list)
    escalation: EscalationPolicy | None = None
    handoff: HandoffPayload | None = None

    @field_validator("scope")
    @classmethod
    def check_scope(cls, s: str) -> str:
        if s not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return s

    @field_validator("to")
    @classmethod
    def check_to_non_empty(cls, to: list[str]) -> list[str]:
        if not to:
            raise ValueError("to must contain at least one target URI")
        if any(not t for t in to):
            raise ValueError("to entries must be non-empty strings")
        return to


class IntentEnvelopeRecord(BaseModel):
    """Response for POST /v1/intents and GET /v1/intents/:id (Spec-X8-Intent-Envelope)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_uri: str = Field(..., alias="from", description="Sender entity URI")
    to: list[str]
    goal: str
    scope: str
    created_at: str
    expires_at: str | None
    constraint: list[Constraint]
    preference: list[Preference]
    deference: list[DeferenceRule]
    escalation: EscalationPolicy | None
    handoff: HandoffPayload | None
    fact_ids: list[str] = Field(
        description="IDs of all facts written into the fabric for this envelope"
    )

