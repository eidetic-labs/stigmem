"""Pydantic models for the Stigmem fact model (v0.9 — gardens; v1.0 — identity)."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel, Field, field_validator

VALID_VALUE_TYPES = {"string", "text", "number", "boolean", "datetime", "ref", "null"}
VALID_SCOPES = {"local", "team", "company", "public"}
VALID_GARDEN_ROLES = {"admin", "writer", "reader"}


class FactValue(BaseModel):
    type: str
    v: Any = None

    @field_validator("type")
    @classmethod
    def check_type(cls, t: str) -> str:
        if t not in VALID_VALUE_TYPES:
            raise ValueError(f"type must be one of {VALID_VALUE_TYPES}")
        return t


class AttestationToken(BaseModel):
    """Ed25519 attestation proving the caller owns the registered agent key.

    The signature covers the canonical UTF-8 message:
        "{entity}\\n{relation}\\n{value.type}\\n{encoded_v}\\n{source}"
    where encoded_v is the same string the node derives via _encode_v().
    """

    key_id: str = Field(..., min_length=1)
    signature: str = Field(..., min_length=1, description="base64url-encoded Ed25519 signature")


class AssertRequest(BaseModel):
    entity: str = Field(..., min_length=1)
    relation: str = Field(..., min_length=1)
    value: FactValue
    source: str = Field(..., min_length=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    scope: str = Field("local")
    valid_until: str | None = Field(None, description="ISO 8601 UTC expiry; null = non-expiring")
    attestation: AttestationToken | None = Field(
        None,
        description="Optional Ed25519 attestation; required when STIGMEM_ATTESTATION_REQUIRED=true",
    )

    @field_validator("scope")
    @classmethod
    def check_scope(cls, s: str) -> str:
        if s not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return s


class FactRecord(BaseModel):
    id: str
    entity: str
    relation: str
    value: FactValue
    source: str
    timestamp: str
    hlc: str | None = None          # v0.5: HLC timestamp; null for pre-migration facts
    received_from: str | None = None  # v0.5: originating node_id if federated
    valid_until: str | None = None
    confidence: float
    scope: str
    attested_key_id: str | None = None  # v1.0: agent key that attested this assertion
    contradicted: bool = False
    warnings: list[str] = Field(default_factory=list)  # write-time convention warnings (assert only)


class QueryResponse(BaseModel):
    facts: list[FactRecord]
    total: int
    cursor: str | None


# ---------------------------------------------------------------------------
# Federation models (v0.5)
# ---------------------------------------------------------------------------

class PeerRegisterRequest(BaseModel):
    node_url: str = Field(..., min_length=1)
    node_id: str = Field(..., min_length=1)
    federation_pubkey: str = Field(..., min_length=1)
    allowed_scopes: list[str]
    declaration_sig: str = Field(..., min_length=1)
    signed_at: str = Field(..., min_length=1)

    @field_validator("allowed_scopes")
    @classmethod
    def check_scopes(cls, scopes: list[str]) -> list[str]:
        invalid = set(scopes) - VALID_SCOPES
        if invalid:
            raise ValueError(f"invalid scopes: {invalid}")
        return scopes


class PeerRecord(BaseModel):
    peer_id: str
    node_id: str
    node_url: str
    status: str
    allowed_scopes: list[str]
    established_at: str | None


class PeerRegisterResponse(BaseModel):
    peer_id: str
    status: str
    verified_at: str | None


class FederationFactsResponse(BaseModel):
    facts: list[FactRecord]
    cursor: str | None
    has_more: bool


class AuditEntry(BaseModel):
    id: str
    peer_id: str
    event_type: str
    detail: str | None
    ts: str


class ConflictResolveRequest(BaseModel):
    """Request body for POST /v1/conflicts/:id/resolve (spec §5.10)."""

    winning_fact_id: str | None = None
    resolution_note: str = ""
    new_value: FactValue | None = None


# ---------------------------------------------------------------------------
# Memory Garden models (spec §17 — v0.9)
# ---------------------------------------------------------------------------

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


class GardenCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1)
    scope: str = Field("company")
    description: str | None = None

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


def row_to_record(
    row: sqlite3.Row,
    contradicted: bool = False,
    warnings: list[str] | None = None,
) -> FactRecord:
    keys = row.keys()
    return FactRecord(
        id=row["id"],
        entity=row["entity"],
        relation=row["relation"],
        value=FactValue(type=row["value_type"], v=_parse_v(row["value_type"], row["value_v"])),
        source=row["source"],
        timestamp=row["timestamp"],
        hlc=row["hlc"] if "hlc" in keys else None,
        received_from=row["received_from"] if "received_from" in keys else None,
        valid_until=row["valid_until"],
        confidence=row["confidence"],
        scope=row["scope"],
        attested_key_id=row["attested_key_id"] if "attested_key_id" in keys else None,
        contradicted=contradicted,
        warnings=warnings or [],
    )


def _parse_v(vtype: str, raw: str) -> Any:
    if vtype == "number":
        return float(raw)
    if vtype == "boolean":
        return raw == "true"
    if vtype == "null":
        return None
    return raw  # string, text, datetime, ref


# ---------------------------------------------------------------------------
# Agent key models (spec §C1 — per-agent keypair registration)
# ---------------------------------------------------------------------------

class AgentKeyRegisterRequest(BaseModel):
    public_key: str = Field(..., min_length=1, description="base64url-encoded Ed25519 raw public key")
    description: str | None = None


class AgentKeyRecord(BaseModel):
    id: str
    entity_uri: str
    public_key: str
    description: str | None
    registered_at: str
    status: str


# ---------------------------------------------------------------------------
# Fact audit models (spec §C3 — end-to-end audit log)
# ---------------------------------------------------------------------------

class AuditLogEntry(BaseModel):
    id: str
    fact_id: str
    event_type: str
    entity_uri: str | None
    oidc_sub: str | None
    source: str
    attested_key_id: str | None
    ts: str
    # C3 enriched join fields (None when not attested or fact/key deleted)
    attested_key_entity_uri: str | None = None
    attested_key_description: str | None = None
    fact_entity: str | None = None
    fact_relation: str | None = None
    fact_value_type: str | None = None
    fact_value_v: str | None = None
    fact_scope: str | None = None


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int
    cursor: str | None
