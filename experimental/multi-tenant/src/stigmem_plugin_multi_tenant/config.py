"""Configuration schema for the multi-tenant plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel


class MultiTenantConfig(BaseModel):
    """Operator-controlled gate for non-default tenant resolution."""

    enabled: bool = False


def load_config_from_env(environ: Mapping[str, str] | None = None) -> MultiTenantConfig:
    """Load multi-tenant plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    return MultiTenantConfig(
        enabled=_env_bool(env, "STIGMEM_MULTI_TENANT_ENABLED"),
    )


def _env_bool(env: Mapping[str, str], name: str) -> bool:
    raw = env.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}
