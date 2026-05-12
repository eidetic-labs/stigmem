"""Billing hook bus — emit usage events on write operations.

Event types:
  fact_written   — emitted after every successful POST /v1/facts
  garden_created — emitted after every successful POST /v1/gardens

The default bus logs structured JSON to stderr.  Replace with a queue-backed
implementation by calling set_hook_bus() at startup (or in tests via a
CaptureBus).  The interface is intentionally narrow so it can be wired to any
message queue without changing call sites.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@dataclass
class BillingEvent:
    event_type: str  # "fact_written" | "garden_created"
    tenant_id: str
    entity_uri: str  # caller's entity_uri
    fact_id: str | None = None
    garden_id: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@runtime_checkable
class HookBus(Protocol):
    def emit(self, event: BillingEvent) -> None: ...


class LogHookBus:
    """Writes billing events as structured JSON to stderr (default implementation)."""

    def emit(self, event: BillingEvent) -> None:
        print(json.dumps({"billing": asdict(event)}), file=sys.stderr)


class CaptureBus:
    """In-memory bus for tests — collects emitted events for assertion."""

    def __init__(self) -> None:
        self.events: list[BillingEvent] = []

    def emit(self, event: BillingEvent) -> None:
        self.events.append(event)


_bus: HookBus = LogHookBus()


def get_hook_bus() -> HookBus:
    return _bus


def set_hook_bus(bus: HookBus) -> None:
    global _bus
    _bus = bus
