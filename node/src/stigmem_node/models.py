"""Pydantic models for the Stigmem fact model (v0.9 — gardens; v1.0 — identity; v1.1 — trust)."""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_VALUE_TYPES = {"string", "text", "number", "boolean", "datetime", "ref", "null"}
VALID_SCOPES = {"local", "team", "company", "public"}
VALID_GARDEN_ROLES = {"admin", "writer", "reader", "quarantine:moderator"}

# Quarantine statuses written to facts.quarantine_status
QUARANTINE_PENDING = "pending"
QUARANTINE_PROMOTED = "promoted"
QUARANTINE_REJECTED = "rejected"


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
    garden_id: str | None = Field(None, description="v0.9: URI of the garden this fact belongs to")

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
    hlc: str | None = None  # v0.5: HLC timestamp; null for pre-migration facts
    received_from: str | None = None  # v0.5: originating node_id if federated
    valid_until: str | None = None
    confidence: float
    scope: str
    attested_key_id: str | None = None  # v1.0: agent key that attested this assertion
    origin_node_id: str | None = None  # v0.8: original assertor node_id (§6.8.1)
    origin_allowed_scopes: list[str] | None = None  # v0.8: scopes permitted at origin (§6.8.1)
    garden_id: str | None = None  # v0.9: garden URI; null = no garden
    attested: bool | None = None  # v0.9: source attestation result; null = not applicable
    contradicted: bool = False
    # write-time convention warnings (assert only)
    warnings: list[str] = Field(default_factory=list)
    # v1.1: source-trust snapshot (§19.4); recomputed live at recall — stored is audit only
    source_trust: float | None = None
    # v1.1: quarantine metadata (§19.5)
    quarantine_status: str | None = None
    quarantine_garden_id: str | None = None
    # v1.1: recall-time computed fields — not stored; populated by recall pipeline
    effective_confidence: float | None = None
    sanitizer_warnings: list[str] = Field(default_factory=list)
    sanitizer_redacted: bool = False
    # Phase 13: content-addressing (spec §25)
    cid: str | None = None


class QueryResponse(BaseModel):
    facts: list[FactRecord]
    total: int | None = None
    cursor: str | None
    tombstone_notices: list[TombstoneNotice] = Field(default_factory=list)


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
    quarantine: bool = False  # v1.1: True for quarantine gardens (§19.5)


class GardenCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1)
    scope: str = Field("company")
    description: str | None = None
    quarantine: bool = Field(False, description="v1.1: create as quarantine garden (§19.5)")

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


def _optional_col(row: sqlite3.Row, col: str, keys: Any) -> Any:
    """Return row[col] if column is in the result set, else None."""
    return row[col] if col in keys else None


def row_to_record(
    row: sqlite3.Row,
    contradicted: bool = False,
    warnings: list[str] | None = None,
    effective_confidence: float | None = None,
    sanitizer_warnings: list[str] | None = None,
    sanitizer_redacted: bool = False,
) -> FactRecord:
    import json as _json

    keys = row.keys()
    attested_raw = _optional_col(row, "attested", keys)
    attested: bool | None = None if attested_raw is None else bool(attested_raw)
    raw_scopes = _optional_col(row, "origin_allowed_scopes", keys)
    origin_allowed_scopes: list[str] | None = _json.loads(raw_scopes) if raw_scopes else None
    source_trust_raw = _optional_col(row, "source_trust", keys)
    source_trust: float | None = float(source_trust_raw) if source_trust_raw is not None else None
    return FactRecord(
        id=row["id"],
        entity=row["entity"],
        relation=row["relation"],
        value=FactValue(type=row["value_type"], v=_parse_v(row["value_type"], row["value_v"])),
        source=row["source"],
        timestamp=row["timestamp"],
        hlc=_optional_col(row, "hlc", keys),
        received_from=_optional_col(row, "received_from", keys),
        valid_until=row["valid_until"],
        confidence=row["confidence"],
        scope=row["scope"],
        attested_key_id=_optional_col(row, "attested_key_id", keys),
        origin_node_id=_optional_col(row, "origin_node_id", keys),
        origin_allowed_scopes=origin_allowed_scopes,
        garden_id=_optional_col(row, "garden_id", keys),
        attested=attested,
        contradicted=contradicted,
        warnings=warnings or [],
        source_trust=source_trust,
        quarantine_status=_optional_col(row, "quarantine_status", keys),
        quarantine_garden_id=_optional_col(row, "quarantine_garden_id", keys),
        effective_confidence=effective_confidence,
        sanitizer_warnings=sanitizer_warnings or [],
        sanitizer_redacted=sanitizer_redacted,
        cid=_optional_col(row, "cid", keys),
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
    public_key: str = Field(
        ..., min_length=1, description="base64url-encoded Ed25519 raw public key"
    )
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


# ---------------------------------------------------------------------------
# Intent Envelope models (spec §4, §5.14 — v0.8)
# ---------------------------------------------------------------------------

VALID_ESCALATION_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_ESCALATION_CHANNELS = {"stigmem", "email", "slack"}


class Constraint(BaseModel):
    """Hard limit on an intent (spec §4.2)."""

    kind: str = Field(..., min_length=1)
    limit: FactValue
    unit: str | None = None


class Preference(BaseModel):
    """Soft preference on an intent (spec §4.3)."""

    kind: str = Field(..., min_length=1)
    value: FactValue
    weight: float = Field(1.0, ge=0.0, le=1.0)


class DeferenceRule(BaseModel):
    """When to defer to another entity before proceeding (spec §4.4)."""

    condition: str = Field(..., min_length=1)
    defer_to: str = Field(..., min_length=1)
    timeout_s: int | None = Field(None, ge=0)


class EscalationPolicy(BaseModel):
    """Who to notify and how when escalation is required (spec §4.5)."""

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
    """Named artifact reference passed along with a handoff (spec §4.6)."""

    name: str = Field(..., min_length=1)
    ref: str = Field(..., min_length=1, description="URI of the artifact fact")


class HandoffPayload(BaseModel):
    """Structured context transfer for agent handoffs (spec §4.6).

    fact_refs MUST include any facts the receiver needs to reconstitute context.
    """

    summary: str = Field(..., min_length=1)
    fact_refs: list[str] = Field(default_factory=list)
    continuation: str | None = None
    artifacts: list[HandoffArtifact] = Field(default_factory=list)


class IntentEnvelopeRequest(BaseModel):
    """POST /v1/intents request body (spec §4, §5.14).

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
    """Response for POST /v1/intents and GET /v1/intents/:id (spec §5.14)."""

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


# ---------------------------------------------------------------------------
# Subscription models (Phase 9, spec §20)
# ---------------------------------------------------------------------------

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


class TombstoneNotice(BaseModel):
    """Tombstone metadata surfaced to admin callers on time-travel queries (spec §24.3.2)."""

    entity_uri: str
    tombstone_id: str
    legal_hold: bool
    tombstone_created_at: str


# ---------------------------------------------------------------------------
# RTBF Tombstones (spec §23)
# ---------------------------------------------------------------------------


class TombstoneRecord(BaseModel):
    """Durable record directing every node to suppress facts about entity_uri (§23.2)."""

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
    """Record reinstating a tombstoned entity (§23.2.5)."""

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


# ---------------------------------------------------------------------------
# Provenance walk models (spec §23.3.2 r.4, §20.6.2)
# ---------------------------------------------------------------------------


class ProvenanceEntry(BaseModel):
    """One entry in a fact's derived_from chain.

    exists=False means the referenced entity is tombstoned or the fact is otherwise
    inaccessible (§23.3.2 r.4 + §20.6.2). Shape is identical in both cases so
    callers cannot distinguish tombstone from unauthorized.
    """

    hash: str
    fact_id: str | None = None
    entity: str | None = None
    exists: bool


class ProvenanceResponse(BaseModel):
    """Response for GET /v1/facts/:id/provenance."""

    fact_id: str
    cid: str | None = None
    derived_from: list[ProvenanceEntry]
