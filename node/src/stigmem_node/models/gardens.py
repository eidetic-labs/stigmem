"""Memory garden and quarantine models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .constants import VALID_GARDEN_ROLES, VALID_SCOPES


class GardenMemberRecord(BaseModel):
    entity_uri: str
    role: str
    added_by: str
    added_at: str


class GardenRecord(BaseModel):
    id: str
    garden_id: str
    slug: str
    name: str
    scope: str
    description: str | None = None
    created_by: str
    created_at: str
    members: list[GardenMemberRecord] = Field(default_factory=list)
    quarantine: bool = False  # v1.1: True for quarantine gardens (§19.5)


class GardenCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1)
    scope: str = Field("company")
    description: str | None = None
    quarantine: bool = Field(
        False,
        description="Create as a quarantine garden (Spec-08-Quarantine-Garden)",
    )

    @field_validator("scope")
    @classmethod
    def check_scope(cls, s: str) -> str:
        if s not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return s


class GardenMemberRequest(BaseModel):
    entity_uri: str = Field(..., min_length=1)
    role: str = Field("reader")

    @field_validator("role")
    @classmethod
    def check_role(cls, r: str) -> str:
        if r not in VALID_GARDEN_ROLES:
            raise ValueError(f"role must be one of {VALID_GARDEN_ROLES}")
        return r


class GardenMemberUpdateRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def check_role(cls, r: str) -> str:
        if r not in VALID_GARDEN_ROLES:
            raise ValueError(f"role must be one of {VALID_GARDEN_ROLES}")
        return r


# ---------------------------------------------------------------------------
# Quarantine garden action models (spec §19.5.5, §5.25)
# ---------------------------------------------------------------------------


class QuarantinePromoteRequest(BaseModel):
    """POST /v1/gardens/:id/promote — move a quarantined fact to a target garden."""

    fact_id: str = Field(..., min_length=1)
    target_garden_id: str | None = Field(
        None,
        description="Target garden UUID or slug. Null = promote to no-garden (main fabric).",
    )
    reason: str = Field("", description="Human-readable reason for promotion.")


class QuarantineRejectRequest(BaseModel):
    """POST /v1/gardens/:id/reject — permanently reject a quarantined fact."""

    fact_id: str = Field(..., min_length=1)
    reason: str = Field("", description="Human-readable reason for rejection.")


class QuarantineRecord(BaseModel):
    """Quarantined fact as returned by GET /v1/quarantine."""

    fact_id: str
    entity: str
    relation: str
    source: str
    quarantine_status: str
    quarantine_garden_id: str | None
    quarantine_reason: str | None
    quarantine_acted_by: str | None
    quarantine_acted_at: str | None
    source_trust: float | None
    received_from: str | None
    timestamp: str


class QuarantineListResponse(BaseModel):
    items: list[QuarantineRecord]
    total: int

