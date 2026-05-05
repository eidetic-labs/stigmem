---
id: billing-hooks
title: Billing Hooks
sidebar_label: Billing Hooks
---

# Billing Hooks

**Audience:** Node operators who need to meter or bill per-tenant usage, and developers writing integration tests that verify billing events fire correctly.

The Stigmem reference node ships a thin, swappable **billing hook bus** (`stigmem_node.billing`). It emits a `BillingEvent` after every write operation so you can forward usage data to your billing backend without touching the core write paths.

---

## BillingEvent schema

```python
@dataclass
class BillingEvent:
    event_type: str        # "fact_written" | "garden_created"
    tenant_id:  str        # tenant that owns the write
    entity_uri: str        # caller's entity_uri (from the API key)
    fact_id:    str | None # set only for "fact_written" events
    garden_id:  str | None # set only for "garden_created" events
    ts:         str        # ISO 8601 UTC timestamp (auto-populated)
```

| Field | Populated by | Notes |
|-------|-------------|-------|
| `event_type` | write route | `"fact_written"` or `"garden_created"` |
| `tenant_id` | resolved `Identity` | always matches the API key's `tenant_id` |
| `entity_uri` | resolved `Identity` | caller identity (e.g. `agent:my-service`) |
| `fact_id` | facts route | UUID of the newly written fact; `None` for garden events |
| `garden_id` | gardens route | UUID of the newly created garden; `None` for fact events |
| `ts` | `billing.py` | defaults to `datetime.now(UTC).isoformat()` |

---

## HookBus protocol

`HookBus` is a `runtime_checkable` Python `Protocol` with a single method:

```python
class HookBus(Protocol):
    def emit(self, event: BillingEvent) -> None: ...
```

Any class that implements `emit(event: BillingEvent) -> None` satisfies the protocol. You can wire in a Kafka producer, a Stripe meter client, or any other sink without subclassing.

---

## Built-in implementations

### LogHookBus (default)

The default bus writes structured JSON to `stderr`:

```python
class LogHookBus:
    def emit(self, event: BillingEvent) -> None:
        print(json.dumps({"billing": asdict(event)}), file=sys.stderr)
```

Sample output:

```json
{"billing": {"event_type": "fact_written", "tenant_id": "acme", "entity_uri": "agent:my-service", "fact_id": "d3b8e1a2-...", "garden_id": null, "ts": "2026-05-03T14:01:00.123456+00:00"}}
```

This is suitable for log-based billing pipelines (CloudWatch Logs Insights, Datadog, etc.).

### CaptureBus (testing)

`CaptureBus` collects all emitted events in memory so tests can make assertions without touching external systems:

```python
class CaptureBus:
    def __init__(self) -> None:
        self.events: list[BillingEvent] = []

    def emit(self, event: BillingEvent) -> None:
        self.events.append(event)
```

---

## Swapping the bus at startup

Replace the global bus before the ASGI server starts accepting requests:

```python
from stigmem_node.billing import BillingEvent, set_hook_bus
from dataclasses import asdict

class MyQueueBus:
    def emit(self, event: BillingEvent) -> None:
        my_queue.publish("billing", asdict(event))

set_hook_bus(MyQueueBus())
```

Retrieve the current bus at any time with `get_hook_bus()`.

:::caution Thread safety
`set_hook_bus()` replaces the module-level `_bus` reference without a lock. Call it once at startup before any requests are served.
:::

---

## Using CaptureBus in tests

Inject via a pytest fixture that wraps the test client:

```python
import pytest
from fastapi.testclient import TestClient
from stigmem_node.app import app
from stigmem_node.billing import CaptureBus, set_hook_bus

@pytest.fixture()
def hooked_client():
    bus = CaptureBus()
    set_hook_bus(bus)
    with TestClient(app) as client:
        yield client, bus

def test_fact_written_event(hooked_client):
    client, bus = hooked_client

    resp = client.post(
        "/v1/facts",
        json={
            "entity": "user:alice",
            "relation": "memory:prefers",
            "value": {"type": "string", "v": "dark mode"},
            "source": "agent:test",
            "confidence": 1.0,
        },
        headers={"Authorization": f"Bearer {TENANT_KEY}"},
    )
    assert resp.status_code == 201

    assert len(bus.events) == 1
    ev = bus.events[0]
    assert ev.event_type == "fact_written"
    assert ev.tenant_id == "acme"
    assert ev.fact_id == resp.json()["id"]
    assert ev.garden_id is None
```

### Asserting tenant_id on billing events

```python
def test_billing_events_carry_tenant_id(hooked_client):
    client, bus = hooked_client

    client.post("/v1/facts", json={...}, headers={"Authorization": f"Bearer {KEY_A}"})
    client.post("/v1/facts", json={...}, headers={"Authorization": f"Bearer {KEY_B}"})

    assert [ev.tenant_id for ev in bus.events] == ["tenant-a", "tenant-b"]
```

The `tenant_id` on each event comes from the resolving API key, never from the request body — tenants cannot spoof each other's billing records.

---

## Custom bus example: Stripe usage metering

```python
import stripe
from stigmem_node.billing import BillingEvent, set_hook_bus

class StripeMeterBus:
    def emit(self, event: BillingEvent) -> None:
        stripe.billing.MeterEvent.create(
            event_name=(
                "stigmem_fact_written"
                if event.event_type == "fact_written"
                else "stigmem_garden_created"
            ),
            payload={
                "stripe_customer_id": _tenant_to_customer(event.tenant_id),
                "value": "1",
            },
        )

set_hook_bus(StripeMeterBus())
```

---

## See also

- [Multi-Tenant Scoping](./multi-tenant) — how `tenant_id` is stamped on API keys and flows to writes
- [Authentication](./authentication) — API key creation and `tenant_id` parameter
- [Asserting Facts](./asserting-facts) — the write endpoint that triggers `"fact_written"` events
- [Memory Gardens](./memory-gardens) — the create-garden endpoint that triggers `"garden_created"` events
