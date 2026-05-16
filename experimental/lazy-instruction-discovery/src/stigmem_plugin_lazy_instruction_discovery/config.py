"""Configuration schema for the lazy instruction discovery plugin."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LazyInstructionDiscoveryConfig(BaseModel):
    """Operator-controlled gates for experimental instruction discovery."""

    enabled: bool = False
    allow_manifest_publish: bool = False
    allow_instruction_recall: bool = False
    allow_file_path_entries: bool = False
    max_manifest_tokens: int = Field(default=1000, ge=1, le=100_000)
    max_boot_stub_tokens: int = Field(default=500, ge=1, le=100_000)
    max_guaranteed_units: int = Field(default=5, ge=0, le=100)
    audit_token_ttl_seconds: int = Field(default=86_400, ge=60, le=2_592_000)
    adapter_profiles: tuple[str, ...] = (
        "paperclip-claude-code",
        "openai-assistants",
        "generic",
    )

    @field_validator("adapter_profiles")
    @classmethod
    def _validate_adapter_profiles(cls, profiles: tuple[str, ...]) -> tuple[str, ...]:
        if not profiles:
            raise ValueError("at least one adapter profile is required")
        normalized = tuple(profile.strip() for profile in profiles)
        if any(not profile for profile in normalized):
            raise ValueError("adapter profile names must be non-empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("adapter profile names must be unique")
        return normalized
