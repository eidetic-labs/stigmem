"""Authentication route wire-format models."""

from __future__ import annotations

from pydantic import BaseModel, Field

STATIC_KEY_MIN_RAW_LENGTH = 32  # matches bootstrap's `openssl rand -hex 32`


class ExchangeRequest(BaseModel):
    id_token: str
    permissions: list[str] = Field(default=["read", "write"])


class ExchangeResponse(BaseModel):
    api_key: str
    entity_uri: str
    permissions: list[str]
    expires_at: str


class KeyInfo(BaseModel):
    id: str
    entity_uri: str
    permissions: list[str]
    description: str | None
    created_at: str
    expires_at: str | None
    oidc_sub: str | None


class RegisterKeyRequest(BaseModel):
    raw_key: str = Field(
        ...,
        min_length=STATIC_KEY_MIN_RAW_LENGTH,
        description=(
            "Caller-generated raw key material (e.g. `openssl rand -hex 32`). "
            "The node hashes it and never stores or echoes the raw value."
        ),
    )
    entity_uri: str = Field(..., min_length=1)
    permissions: list[str] = Field(default_factory=lambda: ["read", "write"])
    description: str | None = None
    expires_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp; omit for no expiry.",
    )
    tenant_id: str | None = Field(
        default=None,
        description="Target tenant; defaults to the caller's tenant.",
    )


class RegisterKeyResponse(BaseModel):
    id: str
    entity_uri: str
    permissions: list[str]
    description: str | None
    created_at: str
    expires_at: str | None
    tenant_id: str
