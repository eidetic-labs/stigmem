"""Configuration schema for the source-attestation plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, model_validator


class SourceAttestationConfig(BaseModel):
    """Operator-controlled gates for experimental source attestation."""

    enabled: bool = False
    enforce_assert_validation: bool = False
    apply_recall_rank: bool = False
    enforce_federation_inbound: bool = False
    warn_only: bool = True

    @model_validator(mode="after")
    def _validate_warn_only_boundary(self) -> SourceAttestationConfig:
        enforcing = self.enforce_assert_validation or self.enforce_federation_inbound
        if enforcing and self.warn_only:
            raise ValueError("warn_only must be false when enforcement gates are enabled")
        return self


def load_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> SourceAttestationConfig:
    """Load source-attestation plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_SOURCE_ATTESTATION_"
    return SourceAttestationConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        enforce_assert_validation=_env_bool(env, f"{prefix}ENFORCE_ASSERT_VALIDATION"),
        apply_recall_rank=_env_bool(env, f"{prefix}APPLY_RECALL_RANK"),
        enforce_federation_inbound=_env_bool(env, f"{prefix}ENFORCE_FEDERATION_INBOUND"),
        warn_only=_env_bool(env, f"{prefix}WARN_ONLY", default=True),
    )


def _env_bool(env: Mapping[str, str], name: str, *, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
