"""Configuration schema for the time-travel query plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import BaseModel, field_validator


class TimeTravelConfig(BaseModel):
    """Operator-controlled gates for experimental historical queries."""

    enabled: bool = False
    allow_fact_query_as_of: bool = False
    allow_recall_as_of: bool = False
    retention_floor: str | None = None

    @field_validator("retention_floor")
    @classmethod
    def _validate_retention_floor(cls, retention_floor: str | None) -> str | None:
        if retention_floor is None:
            return None
        normalized = retention_floor.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.isoformat()


def load_config_from_env(environ: Mapping[str, str] | None = None) -> TimeTravelConfig:
    """Load time-travel plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_TIME_TRAVEL_"
    return TimeTravelConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        allow_fact_query_as_of=_env_bool(env, f"{prefix}ALLOW_FACT_QUERY_AS_OF"),
        allow_recall_as_of=_env_bool(env, f"{prefix}ALLOW_RECALL_AS_OF"),
        retention_floor=env.get(f"{prefix}RETENTION_FLOOR") or None,
    )


def _env_bool(env: Mapping[str, str], name: str) -> bool:
    raw = env.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}
