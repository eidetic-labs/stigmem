"""Compatibility exports for Stigmem Pydantic models.

The model definitions live in domain modules under ``stigmem_node.models``.
This package re-exports the historical ``stigmem_node.models`` surface so
existing imports keep working while internal imports migrate to explicit
domain modules.
"""

from __future__ import annotations

from .audit import AuditLogEntry, AuditLogResponse
from .constants import (
    QUARANTINE_PENDING,
    QUARANTINE_PROMOTED,
    QUARANTINE_REJECTED,
    VALID_GARDEN_ROLES,
    VALID_SCOPES,
    VALID_VALUE_TYPES,
)
from .facts import (
    AssertRequest,
    AttestationToken,
    FactRecord,
    FactValue,
    QueryResponse,
    row_to_record,
)
from .federation import (
    AuditEntry,
    ConflictResolveRequest,
    FederationFactsResponse,
    PeerRecord,
    PeerRegisterRequest,
    PeerRegisterResponse,
)
from .gardens import (
    GardenCreateRequest,
    GardenMemberRecord,
    GardenMemberRequest,
    GardenMemberUpdateRequest,
    GardenRecord,
    QuarantineListResponse,
    QuarantinePromoteRequest,
    QuarantineRecord,
    QuarantineRejectRequest,
)
from .identity import AgentKeyRecord, AgentKeyRegisterRequest
from .intents import (
    VALID_ESCALATION_CHANNELS,
    VALID_ESCALATION_PRIORITIES,
    Constraint,
    DeferenceRule,
    EscalationPolicy,
    HandoffArtifact,
    HandoffPayload,
    IntentEnvelopeRecord,
    IntentEnvelopeRequest,
    Preference,
)
from .provenance import ProvenanceEntry, ProvenanceResponse
from .subscriptions import (
    VALID_ON_CHANGE,
    SubscriptionCreateRequest,
    SubscriptionEventRecord,
    SubscriptionEventsResponse,
    SubscriptionListResponse,
    SubscriptionRecord,
)
from .tombstones import (
    FederationTombstonesResponse,
    TombstoneCreateRequest,
    TombstoneNotice,
    TombstoneRecord,
    TombstoneRevocationRecord,
    TombstoneRevokeRequest,
    TombstoneStatusResponse,
)

__all__ = [
    "AgentKeyRecord",
    "AgentKeyRegisterRequest",
    "AssertRequest",
    "AttestationToken",
    "AuditEntry",
    "AuditLogEntry",
    "AuditLogResponse",
    "ConflictResolveRequest",
    "Constraint",
    "DeferenceRule",
    "EscalationPolicy",
    "FactRecord",
    "FactValue",
    "FederationFactsResponse",
    "FederationTombstonesResponse",
    "GardenCreateRequest",
    "GardenMemberRecord",
    "GardenMemberRequest",
    "GardenMemberUpdateRequest",
    "GardenRecord",
    "HandoffArtifact",
    "HandoffPayload",
    "IntentEnvelopeRecord",
    "IntentEnvelopeRequest",
    "PeerRecord",
    "PeerRegisterRequest",
    "PeerRegisterResponse",
    "Preference",
    "ProvenanceEntry",
    "ProvenanceResponse",
    "QUARANTINE_PENDING",
    "QUARANTINE_PROMOTED",
    "QUARANTINE_REJECTED",
    "QueryResponse",
    "QuarantineListResponse",
    "QuarantinePromoteRequest",
    "QuarantineRecord",
    "QuarantineRejectRequest",
    "SubscriptionCreateRequest",
    "SubscriptionEventRecord",
    "SubscriptionEventsResponse",
    "SubscriptionListResponse",
    "SubscriptionRecord",
    "TombstoneCreateRequest",
    "TombstoneNotice",
    "TombstoneRecord",
    "TombstoneRevokeRequest",
    "TombstoneRevocationRecord",
    "TombstoneStatusResponse",
    "VALID_ESCALATION_CHANNELS",
    "VALID_ESCALATION_PRIORITIES",
    "VALID_GARDEN_ROLES",
    "VALID_ON_CHANGE",
    "VALID_SCOPES",
    "VALID_VALUE_TYPES",
    "row_to_record",
]
