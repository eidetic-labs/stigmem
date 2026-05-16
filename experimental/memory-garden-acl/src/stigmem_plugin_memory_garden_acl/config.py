"""Configuration schema for the Memory Garden advanced ACL plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel


class MemoryGardenAclConfig(BaseModel):
    """Operator-controlled gates for experimental advanced garden ACL behavior."""

    enabled: bool = False
    enforce_assert_authorize: bool = False
    enforce_recall_authorize: bool = False
    apply_recall_filter: bool = False
    enable_oidc_permission_ceiling: bool = False


def load_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> MemoryGardenAclConfig:
    """Load advanced garden ACL plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_MEMORY_GARDEN_ACL_"
    return MemoryGardenAclConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        enforce_assert_authorize=_env_bool(env, f"{prefix}ENFORCE_ASSERT_AUTHORIZE"),
        enforce_recall_authorize=_env_bool(env, f"{prefix}ENFORCE_RECALL_AUTHORIZE"),
        apply_recall_filter=_env_bool(env, f"{prefix}APPLY_RECALL_FILTER"),
        enable_oidc_permission_ceiling=_env_bool(
            env,
            f"{prefix}ENABLE_OIDC_PERMISSION_CEILING",
        ),
    )


def _env_bool(env: Mapping[str, str], name: str, *, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
