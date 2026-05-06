---
title: Intent Envelopes
sidebar_label: Intent Envelopes
audience: Integrator
---

# Intent Envelopes

**Audience:** Agent developers who need to communicate structured intent between agents using the Stigmem fact fabric as the wire format.

Spec §4, §5.14 (v0.8). Implemented in Track F.

An **IntentEnvelope** is a structured message (goal, targets, escalation policy, handoff context, constraints, preferences, deferences) that the node decomposes into a set of reified facts sharing a single `intent_id`. This allows intent history to be queried, filtered, and federated using the same machinery as any other fact.

---

## How it works

```
POST /v1/intents { from, to[], goal, scope, ... }
  │
  ▼  Node decomposes into atomic facts:
(intent_id, "intent:from",  "ref",  from_uri)
(intent_id, "intent:goal",  "text", goal_text)
(intent_id, "intent:to",    "ref",  to_uri)  × len(to)
... escalation, handoff, constraint, preference, deference facts ...
  │
  ▼  Returns IntentEnvelopeRecord with fact_ids[] receipt
```

**Why reification?** Each field becomes a queryable fact. You can find all intents targeting `agent:summarizer` with `GET /v1/facts?relation=intent:to&value=agent:summarizer`, use conflict detection on overlapping constraints, and federate intents across nodes with the standard scope rules.

---

## POST /v1/intents — submit an intent

**Request body:**

```json
{
  "from": "agent:orchestrator",
  "to": ["agent:summarizer"],
  "goal": "Summarize the last 3 user sessions for alice",
  "scope": "team",
  "expires_at": null
}
```

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `from` | string | Sender entity URI (normalized on ingest) |
| `to` | string[] | Target entity URIs — at least one required |
| `goal` | string | Natural-language intent statement (max 2048 chars) |

**Optional fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | string | auto `intent:<uuid>` | Client-supplied stable intent ID (idempotent: 409 if already exists) |
| `scope` | string | `"company"` | One of: `local`, `team`, `company`, `public` |
| `expires_at` | string | `null` | ISO 8601 UTC expiry; `null` = non-expiring |
| `constraint` | Constraint[] | `[]` | Hard limits (see below) |
| `preference` | Preference[] | `[]` | Soft preferences with weights |
| `deference` | DeferenceRule[] | `[]` | Conditions under which to defer to another agent |
| `escalation` | EscalationPolicy | `null` | Who to notify and how if blocked |
| `handoff` | HandoffPayload | `null` | Context transfer for agent handoffs |

**Response (201 Created):**

```json
{
  "id": "intent:a1b2c3...",
  "from": "agent:orchestrator",
  "to": ["agent:summarizer"],
  "goal": "Summarize the last 3 user sessions for alice",
  "scope": "team",
  "created_at": "2026-05-03T01:00:00Z",
  "expires_at": null,
  "constraint": [],
  "preference": [],
  "deference": [],
  "escalation": null,
  "handoff": null,
  "fact_ids": ["uuid1", "uuid2", "uuid3"]
}
```

`fact_ids` is only present in the POST response — it is the set of all facts written for this intent. On `GET /v1/intents/{id}`, the envelope is reconstructed from those facts but `fact_ids` is empty.

**`curl` example:**

```bash
curl -s -X POST http://localhost:8000/v1/intents \
  -H 'Authorization: Bearer stgm_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "from": "agent:orchestrator",
    "to": ["agent:summarizer"],
    "goal": "Summarize the last 3 user sessions for alice",
    "scope": "team"
  }' | jq '{id, fact_ids}'
```

---

## GET /v1/intents/\{intent\_id\} — retrieve an intent

Reconstructs the envelope from its reified facts. Returns `404` if the intent does not exist or has expired.

```bash
curl -s "http://localhost:8000/v1/intents/intent:a1b2c3..." \
  -H 'Authorization: Bearer stgm_...' | jq .
```

URL-encode the `intent_id` if needed (e.g. `intent%3Aa1b2c3...`).

---

## Optional fields in depth

### Escalation policy

Who to notify when the receiving agent is blocked or needs help.

```json
"escalation": {
  "escalate_to": "agent:supervisor",
  "channel": "stigmem",
  "priority": "high",
  "include_context": true
}
```

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `escalate_to` | entity URI | required | Agent or human to notify |
| `channel` | `stigmem`, `email`, `slack` | `stigmem` | Delivery channel |
| `priority` | `low`, `medium`, `high`, `critical` | `medium` | Urgency signal |
| `include_context` | bool | `true` | Whether to include context facts in escalation notice |

### Handoff payload

Structured context transfer when one agent is handing a task to another.

```json
"handoff": {
  "summary": "Session analysis 60% complete; continuing from fact:uuid",
  "fact_refs": ["fact:uuid1", "fact:uuid2"],
  "continuation": "Resume from step 3 of the summarization pipeline",
  "artifacts": [
    { "name": "partial-summary", "ref": "fact:uuid3" }
  ]
}
```

`fact_refs` should include all facts the receiving agent needs to reconstitute context. Receivers call `GET /v1/facts?id=<fact_id>` for each reference.

### Constraints (hard limits)

```json
"constraint": [
  { "kind": "max_tokens", "limit": { "type": "number", "v": 1000 }, "unit": "tokens" },
  { "kind": "deadline",   "limit": { "type": "str",    "v": "2026-05-04T00:00:00Z" } }
]
```

`kind` is a free string; common conventions: `max_tokens`, `deadline`, `max_cost`, `max_facts`.

### Preferences (soft weights)

```json
"preference": [
  { "kind": "verbosity", "value": { "type": "str",    "v": "concise" }, "weight": 0.8 },
  { "kind": "language",  "value": { "type": "str",    "v": "english" }, "weight": 1.0 }
]
```

`weight` is `[0.0, 1.0]`; `1.0` = strong preference.

### Deference rules

When to pause and defer to another agent before proceeding.

```json
"deference": [
  {
    "condition": "confidence < 0.4 on any summary fact",
    "defer_to": "agent:reviewer",
    "timeout_s": 300
  }
]
```

`condition` is a human-readable description of the triggering condition; `timeout_s` is optional — after this many seconds without a response, the receiving agent may proceed autonomously.

---

## Idempotency

Supply a stable `id` (e.g. `"id": "intent:my-op-2026-05-03"`) to make submission idempotent. If the intent already exists in the fabric, the node returns `409 Conflict` without writing new facts:

```
"intent 'intent:my-op-2026-05-03' already exists; supply a new id or omit for auto-generation"
```

---

## Querying intents as facts

Because intents are reified as ordinary facts, you can use the standard query endpoints:

```bash
# All intents targeting a specific agent
curl -s "http://localhost:8000/v1/facts?relation=intent:to&value=agent:summarizer" \
  -H 'Authorization: Bearer stgm_...' | jq '.facts[].entity'

# All intents from a specific sender in the last hour
curl -s "http://localhost:8000/v1/facts?relation=intent:from&value=agent:orchestrator" \
  -H 'Authorization: Bearer stgm_...' | jq '.facts[] | {entity, timestamp}'
```

---

## See also

- [Asserting Facts](../concepts/facts/asserting-facts) — the atomic fact model underlying intents
- [Querying Facts](../concepts/facts/querying-facts) — filter intent facts by relation and value
- [Federation](../concepts/federation/) — scope rules apply to intent facts identically to data facts
- Spec §4 — IntentEnvelope schema and field semantics
- Spec §5.14 — Wire route formalization
