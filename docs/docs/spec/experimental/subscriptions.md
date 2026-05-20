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

<p className="stigmem-meta"><span>4 min read</span><span>Spec contributor · Node operator</span><span>Experimental · v0.9.0bN</span></p>

<div className="stigmem-lead">

**What this spec defines**

Push-style notification for changes to scopes or entities. Useful
for webhook consumers and agent wake-ups, but the primitive expands
the authorization boundary because event delivery can leak
information after a caller loses access.

</div>

**Status:** Experimental. This material is deferred from the supported v0.9.0aN
surface and must pass ADR-008 gates before reintroduction.

**Source material:** pre-reset §20.5 subscription material, extracted from the
archived recall-and-graph design.

<div className="stigmem-keypoint">

**Subscriptions remain experimental until delivery-time authorization, replay, and operator runbook requirements are validated.**

</div>

## Route

The subscription API follows standard REST conventions: POST to create, GET to list or inspect, DELETE to cancel. Subscription state is server-managed: the node tracks cursors internally and delivers events through the configured change mechanism.

```text
POST   /v1/subscriptions
GET    /v1/subscriptions
GET    /v1/subscriptions/:id
DELETE /v1/subscriptions/:id
```

## Request shape

A subscription request binds a `target` (either a scope or a specific entity) to a change-notification mechanism. The `on_change` field selects between `webhook` for HTTP-based push delivery and `wake` for Paperclip-integrated agent wake-ups. The `event_filter` array lets callers subscribe to a subset of event types, reducing noise for consumers that only care about specific lifecycle events. The `idempotency_key` ensures that retried creation requests do not produce duplicate subscriptions.

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

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Constraint</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>target</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>MUST be either a <code>scope:</code> prefixed scope identifier or an <code>entity:</code> prefixed entity URI.</dd>
</div>

<div>
<dt><code>on_change=webhook</code></dt>
<dt><span className="stigmem-fields__type">HTTPS only</span></dt>
<dd>Delivers events to <code>webhook_url</code> through HTTP POST. <code>webhook_url</code> MUST use HTTPS.</dd>
</div>

<div>
<dt><code>on_change=wake</code></dt>
<dt><span className="stigmem-fields__type">Paperclip</span></dt>
<dd>Wakes the specified agent by triggering a Paperclip wake event on its assigned issue. Standalone deployments that do not support wake delivery MUST return HTTP 422 with error code <code>wake_not_supported</code>.</dd>
</div>

<div>
<dt>Scoping</dt>
<dt><span className="stigmem-fields__type">authorized only</span></dt>
<dd>Subscriptions MUST be scoped to the caller's authorized garden or to the global scope if the caller has global read access.</dd>
</div>

<div>
<dt>Duplicates</dt>
<dt><span className="stigmem-fields__type">dedup</span></dt>
<dd>Duplicate subscriptions MUST be deduplicated using <code>idempotency_key</code> if provided, or matched by structural equality if not. A duplicate POST MUST return 200 with the existing subscription.</dd>
</div>

</div>

## Event shape

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

<div className="stigmem-keypoint">

**The `idempotency_key` in the delivery envelope MUST equal `event_id`.**

Subscribers MUST treat deliveries with the same `idempotency_key` as
duplicates and discard them after first processing.

</div>

## Delivery guarantees

<div className="stigmem-grid">

<div><h4>At-least-once</h4><p>Implementations MUST deliver each event at least once.</p></div>
<div><h4>Exponential backoff</h4><p>Retry failed webhook deliveries with exponential backoff (initial 1 s, max 10 attempts, cap 300 s).</p></div>
<div><h4>5xx / timeout</h4><p>Triggers retry. Webhook timeout is 10 seconds.</p></div>
<div><h4>410 Gone</h4><p>Permanently removes the subscription.</p></div>
<div><h4>Replay window</h4><p><code>STIGMEM_SUBSCRIPTION_REPLAY_S</code> default 3600 s. Subscribers MAY replay via <code>GET /v1/subscriptions/:id/events?after=&#123;event_id&#125;</code>.</p></div>
<div><h4>Beyond window</h4><p>Events outside the replay window are not recoverable. Nodes SHOULD expose this limit as <code>replay_window_s</code>.</p></div>

</div>

## Auth and scoping

Subscription creation MUST require the caller to hold a capability token with verb `subscribe` on the target scope or entity URI. Tokens MUST be validated before any subscription is persisted.

<div className="stigmem-keypoint">

**The primary security concern is cross-garden leakage through event streams.**

A subscription's event stream MUST NOT leak facts from
garden-scoped entities to callers without garden read access.

</div>

At each event delivery, implementations MUST perform the following checks in order:

<ol className="stigmem-steps">
<li><strong>Token revocation check:</strong> verify the subscriber's capability token is not revoked. A revoked token MUST be treated the same as access revocation below.</li>
<li><strong>Garden ACL check:</strong> re-evaluate the caller's garden ACL against the event's target entity/scope, not just at subscription creation time.</li>
</ol>

If either check fails, event content MUST NOT be populated or delivered. The event record MAY be queued internally before these checks to honor at-least-once delivery semantics, but event content MUST be withheld from the subscriber until both checks pass at delivery time. If the caller's access or token has been revoked since subscription creation, delivery MUST be silently dropped and the subscription MUST be automatically cancelled with event type `subscription_cancelled_access_revoked`.

## Storage

Implementations that enable this experimental feature persist subscription state and a replay buffer with dedicated tables. The replay buffer supports at-least-once delivery and short-window event replay without storing events in the core fact table.

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

## Error reference

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type"><code>subscription_not_found</code></span></dt>
<dd>No subscription with given id exists.</dd>
</div>

<div>
<dt>422</dt>
<dt><span className="stigmem-fields__type"><code>wake_not_supported</code></span></dt>
<dd><code>on_change="wake"</code> on a non-Paperclip deployment.</dd>
</div>

</div>
