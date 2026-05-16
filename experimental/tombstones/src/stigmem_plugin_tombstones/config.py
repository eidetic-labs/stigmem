"""Configuration schema for the RTBF tombstone plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, Field, field_validator


class TombstoneConfig(BaseModel):
    """Operator-controlled gates for experimental tombstone behavior."""

    enabled: bool = False
    allow_admin_routes: bool = False
    allow_federation_routes: bool = False
    allow_recall_filter: bool = False
    propagate_to_peers: bool = False
    require_signed_inbound: bool = True
    cache_ttl_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("propagate_to_peers")
    @classmethod
    def _propagation_requires_federation_routes(cls, propagate: bool, info: object) -> bool:
        data = getattr(info, "data", {})
        if propagate and not data.get("allow_federation_routes", False):
            raise ValueError("propagate_to_peers requires allow_federation_routes")
        return propagate


def load_config_from_env(environ: Mapping[str, str] | None = None) -> TombstoneConfig:
    """Load tombstone plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_TOMBSTONES_"
    return TombstoneConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        allow_admin_routes=_env_bool(env, f"{prefix}ALLOW_ADMIN_ROUTES"),
        allow_federation_routes=_env_bool(env, f"{prefix}ALLOW_FEDERATION_ROUTES"),
        allow_recall_filter=_env_bool(env, f"{prefix}ALLOW_RECALL_FILTER"),
        propagate_to_peers=_env_bool(env, f"{prefix}PROPAGATE_TO_PEERS"),
        require_signed_inbound=_env_bool(env, f"{prefix}REQUIRE_SIGNED_INBOUND", default=True),
        cache_ttl_seconds=int(env.get(f"{prefix}CACHE_TTL_SECONDS", "60")),
    )


def _env_bool(env: Mapping[str, str], name: str, *, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
