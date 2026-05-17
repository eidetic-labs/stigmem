---
spec_id: Spec-X7-Subscriptions
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: pre-reset §20.5 subscription material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-03-HTTP-API >= 0.1.0-alpha.0
  - Spec-06-Capability-Tokens >= 0.1.0-alpha.0
title: Subscriptions
sidebar_label: Subscriptions
audience: Spec
description: "Stigmem experimental subscriptions spec — push-style event delivery for fact, contradiction, and memory-card changes."
stability: experimental
since: 0.9.0a1
---

# Spec-X7-Subscriptions

**Status:** Experimental. This material is deferred from the supported v0.9.0aN
surface and must pass ADR-008 gates before reintroduction.

**Source material:** pre-reset §20.5 subscription material, extracted from the
archived recall-and-graph design. This file is the ADR-010 colocated home for
subscription semantics under `experimental/subscriptions/`.

Subscriptions provide push-style notification for changes to scopes or entities.
The primitive is useful for webhook consumers and agent wake-ups, but it expands
the authorization boundary because event delivery can leak information after a
caller loses access. For that reason, subscriptions remain experimental until
delivery-time authorization, replay, and operator runbook requirements are
validated.

## Route

The subscription API follows standard REST conventions: POST to create, GET to
list or inspect, DELETE to cancel. Subscription state is server-managed: the
node tracks cursors internally and delivers events through the configured change
mechanism.

```text
POST   /v1/subscriptions
GET    /v1/subscriptions
GET    /v1/subscriptions/:id
DELETE /v1/subscriptions/:id
```

## Request Shape

A subscription request binds a `target` (either a scope or a specific entity) to
a change-notification mechanism. The `on_change` field selects between
`webhook` for HTTP-based push delivery and `wake` for Paperclip-integrated agent
wake-ups. The `event_filter` array lets callers subscribe to a subset of event
types, reducing noise for consumers that only care about specific lifecycle
events. The `idempotency_key` ensures that retried creation requests do not
produce duplicate subscriptions.

```json
{
  "target": "scope:global" | "entity:{entity_uri}",
  "on_change": "webhook" | "wake",
  "webhook_url": "https://example.com/hook",
  "wake_agent_id": "{uuid}",
  "event_filter": [
    "fact_assert",
    "fact_retract",
    "contradiction_detected",
    "card_refreshed"
  ],
  "idempotency_key": "{opaque string}",
  "scope": "{scope_id}"
}
```

- `target` MUST be either a `scope:` prefixed scope identifier or an `entity:`
  prefixed entity URI.
- `on_change = "webhook"` delivers events to `webhook_url` through HTTP POST.
  `webhook_url` MUST use HTTPS.
- `on_change = "wake"` wakes the specified agent by triggering a Paperclip wake
  event on its assigned issue. Standalone deployments that do not support wake
  delivery MUST return HTTP 422 with error code `wake_not_supported`.
- Subscriptions MUST be scoped to the caller's authorized garden or to the
  global scope if the caller has global read access.
- Duplicate subscriptions (same `target` plus `on_change` plus
  `webhook_url`/`wake_agent_id`) MUST be deduplicated using `idempotency_key` if
  provided, or matched by structural equality if not. A duplicate POST MUST
  return 200 with the existing subscription.

## Event Shape

Events are delivered as JSON payloads with the following structure:

```json
{
  "subscription_id": "{uuid}",
  "event_id": "{uuid}",
  "event_type": "fact_assert" | "fact_retract" | "contradiction_detected" | "card_refreshed",
  "entity": "{entity_uri}",
  "scope": "{scope_id}",
  "fact_id": "{uuid}",
  "hlc": "{hlc}",
  "payload": {},
  "idempotency_key": "{event_id}"
}
```

The `idempotency_key` in the delivery envelope MUST equal `event_id`.
Subscribers MUST treat deliveries with the same `idempotency_key` as duplicates
and discard them after first processing.

## Delivery Guarantees

- Implementations MUST deliver each event at least once.
- Implementations MUST retry failed webhook deliveries with exponential backoff
  (initial delay 1 second, max 10 attempts, cap 300 seconds).
- A webhook endpoint that returns 5xx or times out after 10 seconds triggers a
  retry. A 410 response permanently removes the subscription.
- Implementations MUST maintain a replay window of
  `STIGMEM_SUBSCRIPTION_REPLAY_S` (default 3600 seconds). Subscribers MAY
  request replay from a given `event_id` using
  `GET /v1/subscriptions/:id/events?after={event_id}` within this window.
- Events outside the replay window are not recoverable. Implementations SHOULD
  expose this limit in the subscription response as `replay_window_s`.

## Auth And Scoping

Subscription creation MUST require the caller to hold a capability token with
verb `subscribe` on the target scope or entity URI. Tokens MUST be validated
before any subscription is persisted.

The security boundary is critical: a subscription's event stream MUST NOT leak
facts from garden-scoped entities to callers without garden read access. At each
event delivery, implementations MUST perform the following checks in order:

1. Token revocation check: verify the subscriber's capability token is not
   revoked. A revoked token MUST be treated the same as access revocation below.
2. Garden ACL check: re-evaluate the caller's garden ACL against the event's
   target entity/scope, not just at subscription creation time.

If either check fails, event content MUST NOT be populated or delivered. The
event record MAY be queued internally before these checks to honor at-least-once
delivery semantics, but event content MUST be withheld from the subscriber until
both checks pass at delivery time. If the caller's access or token has been
revoked since subscription creation, delivery MUST be silently dropped and the
subscription MUST be automatically cancelled with event type
`subscription_cancelled_access_revoked`.

This is the primary security concern for the subscription primitive:
cross-garden leakage through event streams.

## Storage

Implementations that enable this experimental feature persist subscription state
and a replay buffer with dedicated tables. The replay buffer supports
at-least-once delivery and short-window event replay without storing events in
the core fact table.

```sql
CREATE TABLE IF NOT EXISTS subscriptions (
    id               TEXT PRIMARY KEY,
    target           TEXT NOT NULL,
    on_change        TEXT NOT NULL CHECK (on_change IN ('webhook', 'wake')),
    webhook_url      TEXT,
    wake_agent_id    TEXT,
    event_filter     TEXT NOT NULL DEFAULT '["fact_assert","fact_retract"]',
    scope            TEXT NOT NULL,
    idempotency_key  TEXT,
    created_at       INTEGER NOT NULL,
    last_event_at    INTEGER,
    cancelled_at     INTEGER,
    replay_window_s  INTEGER NOT NULL DEFAULT 3600
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_target
    ON subscriptions (target, scope);

CREATE TABLE IF NOT EXISTS subscription_events (
    id               TEXT PRIMARY KEY,
    subscription_id  TEXT NOT NULL REFERENCES subscriptions(id),
    event_type       TEXT NOT NULL,
    entity           TEXT,
    fact_id          TEXT,
    hlc              TEXT,
    payload          TEXT,
    delivered_at     INTEGER,
    created_at       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sub_events_sub_id
    ON subscription_events (subscription_id, created_at DESC);
```

## Error Reference

| HTTP | Error code | Condition |
|---|---|---|
| 404 | `subscription_not_found` | No subscription with given id exists |
| 422 | `wake_not_supported` | `on_change = "wake"` on a non-Paperclip deployment |
