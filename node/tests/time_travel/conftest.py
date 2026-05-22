from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def enable_time_travel_plugin_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Time-travel semantic tests exercise explicitly enabled plugin behavior."""

    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF", "true")
    monkeypatch.setenv("STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF", "true")
