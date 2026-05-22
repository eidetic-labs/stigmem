"""Configuration schema for the time-travel query plugin."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel


class TimeTravelConfig(BaseModel):
    """Operator-controlled gates for experimental historical queries."""

    enabled: bool = False
    allow_fact_query_as_of: bool = False
    allow_recall_as_of: bool = False


def load_config_from_env(environ: Mapping[str, str] | None = None) -> TimeTravelConfig:
    """Load time-travel plugin gates from environment variables."""

    env = environ if environ is not None else os.environ
    prefix = "STIGMEM_TIME_TRAVEL_"
    return TimeTravelConfig(
        enabled=_env_bool(env, f"{prefix}ENABLED"),
        allow_fact_query_as_of=_env_bool(env, f"{prefix}ALLOW_FACT_QUERY_AS_OF"),
        allow_recall_as_of=_env_bool(env, f"{prefix}ALLOW_RECALL_AS_OF"),
    )


def _env_bool(env: Mapping[str, str], name: str) -> bool:
    raw = env.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}
