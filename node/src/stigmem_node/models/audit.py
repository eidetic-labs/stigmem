"""Fact audit log models."""

from __future__ import annotations

from pydantic import BaseModel


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

