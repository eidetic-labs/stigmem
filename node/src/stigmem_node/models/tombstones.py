"""RTBF tombstone models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TombstoneNotice(BaseModel):
    """Tombstone metadata surfaced to admin callers on time-travel queries.

    Covered by Spec-X3-Time-Travel-Queries.
    """

    entity_uri: str
    tombstone_id: str
    legal_hold: bool
    tombstone_created_at: str


# ---------------------------------------------------------------------------
# RTBF Tombstones (Spec-X2-RTBF-Tombstones)
# ---------------------------------------------------------------------------


class TombstoneRecord(BaseModel):
    """Durable record directing every node to suppress facts about entity_uri.

    Covered by Spec-X2-RTBF-Tombstones.
    """

    id: str
    entity_uri: str
    scope: str
    reason: str | None = None
    signed_by: str
    key_id: str = ""
    signature: str
    created_at: str
    legal_hold: bool = False


class TombstoneRevocationRecord(BaseModel):
    """Record reinstating a tombstoned entity (Spec-X2-RTBF-Tombstones)."""

    id: str
    tombstone_id: str
    reason: str
    signed_by: str
    key_id: str = ""
    signature: str
    created_at: str


class TombstoneCreateRequest(BaseModel):
    entity_uri: str = Field(..., min_length=1)
    scope: str = Field("*")
    reason: str | None = None
    legal_hold: bool = False


class TombstoneRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class TombstoneStatusResponse(BaseModel):
    tombstoned: bool
    tombstones: list[TombstoneRecord]
    revocations: list[TombstoneRevocationRecord]


class FederationTombstonesResponse(BaseModel):
    tombstones: list[TombstoneRecord]
    revocations: list[TombstoneRevocationRecord]
    cursor: str | None

