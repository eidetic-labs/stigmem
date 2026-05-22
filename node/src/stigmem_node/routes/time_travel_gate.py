"""Shared fail-closed gate for experimental time-travel requests."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Literal

from fastapi import HTTPException, status

TIME_TRAVEL_PLUGIN_NAME = "stigmem-plugin-time-travel"

TimeTravelSurface = Literal["fact_query", "recall"]


def require_time_travel_enabled(registry: Any, *, surface: TimeTravelSurface) -> None:
    """Require the time-travel plugin and its explicit operator gate."""

    if TIME_TRAVEL_PLUGIN_NAME not in registry.registered_plugins():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "time_travel_plugin_not_loaded",
                "message": "time-travel queries require stigmem-plugin-time-travel",
            },
        )

    config = _load_time_travel_config()
    surface_gate = {
        "fact_query": "allow_fact_query_as_of",
        "recall": "allow_recall_as_of",
    }[surface]
    if not bool(getattr(config, "enabled", False)) or not bool(
        getattr(config, surface_gate, False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "time_travel_plugin_disabled",
                "message": (
                    "time-travel queries require explicit operator enablement "
                    f"for {surface.replace('_', ' ')}"
                ),
            },
        )


def _load_time_travel_config() -> Any:
    try:
        config_module = import_module("stigmem_plugin_time_travel.config")
        return config_module.load_config_from_env()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "time_travel_plugin_not_loaded",
                "message": "time-travel plugin configuration is unavailable",
            },
        ) from exc
