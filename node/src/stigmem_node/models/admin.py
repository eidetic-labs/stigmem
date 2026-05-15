"""Admin route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel


class AdminAuditEntry(BaseModel):
    seq: int | None
    id: str
    event_type: str
    entity_uri: str | None
    oidc_sub: str | None
    fact_id: str | None
    source: str
    attested_key_id: str | None
    ts: str
    tenant_id: str | None
    detail: str | None


class AdminAuditResponse(BaseModel):
    entries: list[AdminAuditEntry]
    total: int
    next_cursor: int | None


class CidBackfillStatus(BaseModel):
    total_facts: int
    backfilled_facts: int
    pending_facts: int
    backfill_complete: bool
