---
title: Subscriptions
sidebar_label: Subscriptions
audience: Integrator
---

# Subscriptions

**Audience:** Agent developers and node operators who need to react to fact changes without polling.

Stigmem subscriptions let you register a standing watch on a **scope** or an **entity URI**. When a matching fact is asserted, the node enqueues a delivery event and pushes it to your endpoint (webhook) or streams it to stderr (wake). (Spec §20.3–§20.6.)

## Concepts

### Targets

A subscription targets either a scope name (`local`, `team`, `company`, `public`) or a specific entity URI:

| Target type | Example | Fires when |
|-------------|---------|------------|
| Scope | `local` | Any fact in that scope is asserted |
| Entity URI | `stigmem://company.example/user/alice` | Any fact about that entity is asserted |

### Delivery modes

| `on_change` | Behaviour |
|-------------|-----------|
| `webhook` | `POST` the event payload to `delivery_address` (a URL) with exponential backoff (1 s → 2 s → 4 s … capped at 300 s) |
| `wake` | Emit a JSON object to the node's **stderr** stream; intended for operator-managed platform integrations |

Both modes apply the §17 garden ACL re-check and the §19 content sanitizer at delivery time — not just at subscription creation. Facts the subscriber no longer has access to are silently dropped.

### Circuit breaker

After `STIGMEM_SUBSCRIPTION_CIRCUIT_THRESHOLD` consecutive delivery failures (default `10`), the node opens the circuit breaker on the subscription: `circuit_open = true`. No further delivery is attempted. Inspect and delete the subscription to reset.

A webhook endpoint returning HTTP `410 Gone` immediately cancels the subscription.

### Replay window

The node retains delivery events for `STIGMEM_SUBSCRIPTION_REPLAY_S` seconds (default `86400` — 24 h). Use `GET /v1/subscriptions/{id}/events` to replay missed events within this window.

---

## Capability requirement

Subscription creation requires a capability token (§19.3) with verb `subscribe` on the target scope or entity URI. Without it the node returns `403 Forbidden`.

---

## API reference

### Create subscription — `POST /v1/subscriptions`

```bash
curl -s -X POST http://localhost:8765/v1/subscriptions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-key' \
  -d '{
    "target": "local",
    "on_change": "webhook",
    "delivery_address": "https://hooks.example.com/stigmem",
    "idempotency_key": "my-agent-sub-v1"
  }'
```

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | ✓ | Scope name or entity URI to watch |
| `on_change` | `"webhook"` \| `"wake"` | ✓ | Delivery mode |
| `delivery_address` | string | ✓ | Webhook URL (webhook) or identity URI (wake) |
| `idempotency_key` | string | — | Optional; returns the existing subscription if the key matches any prior call by the same caller |

**Response `201 Created`**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "subscriber_identity": "stigmem://company.example/agent/watcher",
  "target": "local",
  "target_kind": "scope",
  "on_change": "webhook",
  "delivery_address": "https://hooks.example.com/stigmem",
  "idempotency_key": "my-agent-sub-v1",
  "created_at": "2026-05-04T10:00:00Z",
  "last_delivered_at": null,
  "circuit_open": false,
  "consecutive_failures": 0
}
```

:::tip Natural deduplication
A `POST` with the same `(target, on_change, delivery_address)` triple as an existing subscription returns the existing record with `200 OK`. Use `idempotency_key` for stable, caller-controlled deduplication.
:::

---

### List subscriptions — `GET /v1/subscriptions`

Returns all subscriptions owned by the authenticated caller. BOLA: other callers' subscriptions are never returned.

```bash
curl -s http://localhost:8765/v1/subscriptions \
  -H 'X-API-Key: your-key'
```

**Response `200 OK`**

```json
{
  "subscriptions": [ /* array of SubscriptionRecord */ ],
  "total": 1
}
```

---

### Get subscription — `GET /v1/subscriptions/{id}`

```bash
curl -s http://localhost:8765/v1/subscriptions/3fa85f64-... \
  -H 'X-API-Key: your-key'
```

Returns `404 Not Found` if the subscription does not exist or is owned by another caller (§20.3.2 BOLA guard).

---

### Cancel subscription — `DELETE /v1/subscriptions/{id}`

```bash
curl -s -X DELETE http://localhost:8765/v1/subscriptions/3fa85f64-... \
  -H 'X-API-Key: your-key'
```

Returns `204 No Content` on success, `404` if the subscription does not exist or is owned by another caller.

---

### Replay events — `GET /v1/subscriptions/{id}/events`

Retrieve delivery events within the replay window. Useful for catching up after a webhook outage.

```bash
curl -s 'http://localhost:8765/v1/subscriptions/3fa85f64-.../events?limit=100' \
  -H 'X-API-Key: your-key'
```

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `since` | ISO 8601 | Return events at or after this timestamp (clamped to replay window start) |
| `cursor` | string | Opaque pagination cursor from the previous response |
| `limit` | integer 1–500 | Page size (default `50`) |

**Response `200 OK`**

```json
{
  "events": [
    {
      "id": "evt-uuid",
      "subscription_id": "3fa85f64-...",
      "event_type": "fact_asserted",
      "entity_uri": "stigmem://company.example/user/alice",
      "fact_id": "fact-uuid",
      "payload": { /* sanitized fact payload */ },
      "created_at": "2026-05-04T10:01:00Z",
      "delivered_at": "2026-05-04T10:01:01Z",
      "delivery_status": "delivered",
      "delivery_attempts": 1
    }
  ],
  "total": 1,
  "cursor": null
}
```

`delivery_status` values: `pending`, `delivered`, `failed`.

:::warning Security re-check at replay time
The §17 garden ACL and §19 sanitizer are re-applied when events are served from the replay window. If the subscriber's garden membership was revoked after delivery, the event payload is replaced with `{"fact_id": "...", "redacted": true}`. This prevents the replay window from becoming a bypass for access revocation. (Spec §20.5.5.)
:::

---

## Webhook payload shape

Each `POST` to your webhook URL carries:

```json
{
  "event_id": "evt-uuid",
  "idempotency_key": "evt-uuid",
  "subscription_id": "sub-uuid",
  "event_type": "fact_asserted",
  "fact": {
    "id": "fact-uuid",
    "entity": "stigmem://company.example/user/alice",
    "relation": "memory:prefers",
    "value_type": "string",
    "value_v": "dark mode",
    "source": "agent:settings",
    "timestamp": "2026-05-04T10:01:00Z",
    "confidence": 1.0,
    "scope": "local"
  }
}
```

Headers sent with every webhook:

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `X-Stigmem-Event-Id` | Event UUID — use for idempotent processing |

**Retry behaviour:**

- `5xx` or `429` → exponential backoff retry (1 s, 2 s, 4 s … max 300 s).
- `4xx` (except `429`) → permanent failure; no retry.
- `410 Gone` → subscription is immediately cancelled server-side.

---

## Wake delivery

When `on_change = "wake"`, the node writes a JSON object to **stderr** on each delivery:

```json
{
  "stigmem_wake": {
    "event_id": "evt-uuid",
    "subscription_id": "sub-uuid",
    "subscriber_identity": "stigmem://company.example/agent/watcher",
    "delivery_address": "stigmem://company.example/agent/watcher",
    "event_type": "fact_asserted",
    "fact": { /* sanitized fact payload */ },
    "ts": "2026-05-04T10:01:00Z"
  }
}
```

:::caution Platform trust boundary
Wake delivery writes all subscribers' sanitized fact payloads to the same stderr stream. Any process with access to the node's stderr can read all wake events regardless of subscriber identity. Operators requiring per-subscriber isolation should run one node per subscriber. (Spec §20.6.2 note P1.)
:::

---

## Security enforcement (§17 / §19)

Both delivery modes and the replay endpoint apply the same two checks at delivery time:

1. **Token revocation check** (§19.3.4) — if the subscriber no longer holds a valid API key, delivery is silently dropped.
2. **Garden ACL re-check** (§17) — if the fact belongs to a garden and the subscriber is no longer a member, delivery is silently dropped.

"At delivery time" includes both the background delivery sweep and the replay window endpoint. Subscriptions created before access was revoked do not become a persistent side channel.

---

## Configuration

| Environment variable | Default | Description |
|----------------------|---------|-------------|
| `STIGMEM_SUBSCRIPTION_REPLAY_S` | `86400` | Replay window in seconds (24 h) |
| `STIGMEM_SUBSCRIPTION_DELIVERY_SWEEP_S` | `30` | How often the background sweep retries pending events |
| `STIGMEM_SUBSCRIPTION_CIRCUIT_THRESHOLD` | `10` | Consecutive failures before the circuit breaker opens |

---

## Python example

```python
import httpx

BASE = "http://localhost:8765"
KEY = "your-key"

# Create a webhook subscription on the "local" scope
resp = httpx.post(
    f"{BASE}/v1/subscriptions",
    headers={"X-API-Key": KEY},
    json={
        "target": "local",
        "on_change": "webhook",
        "delivery_address": "https://hooks.example.com/stigmem",
        "idempotency_key": "agent-watcher-v1",
    },
)
resp.raise_for_status()
sub = resp.json()
print(f"Subscription created: {sub['id']}")

# Replay the last hour of events
events = httpx.get(
    f"{BASE}/v1/subscriptions/{sub['id']}/events",
    headers={"X-API-Key": KEY},
    params={"since": "2026-05-04T09:00:00Z", "limit": 500},
).json()
for evt in events["events"]:
    print(evt["event_type"], evt["fact_id"], evt["delivery_status"])

# Cancel
httpx.delete(f"{BASE}/v1/subscriptions/{sub['id']}", headers={"X-API-Key": KEY})
```
