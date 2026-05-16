"""Configuration schema for the lazy instruction discovery plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

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


def load_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> LazyInstructionDiscoveryConfig:
    """Load experimental plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_LAZY_INSTRUCTION_DISCOVERY_"
    adapter_profiles_raw = env.get(f"{prefix}ADAPTER_PROFILES")
    adapter_profiles = (
        tuple(part.strip() for part in adapter_profiles_raw.split(","))
        if adapter_profiles_raw
        else LazyInstructionDiscoveryConfig().adapter_profiles
    )
    return LazyInstructionDiscoveryConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        allow_manifest_publish=_env_bool(env, f"{prefix}ALLOW_MANIFEST_PUBLISH"),
        allow_instruction_recall=_env_bool(env, f"{prefix}ALLOW_INSTRUCTION_RECALL"),
        allow_file_path_entries=_env_bool(env, f"{prefix}ALLOW_FILE_PATH_ENTRIES"),
        adapter_profiles=adapter_profiles,
    )


def _env_bool(env: Mapping[str, str], name: str) -> bool:
    raw = env.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}
