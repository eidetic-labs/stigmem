"""Agent key registration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


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

