---
title: §4. Intent Envelope
sidebar_label: §4 Intent Envelope
audience: Spec
description: "Stigmem spec section 4 — Goal/constraint/preference/handoff envelope types for richer agent coordination."
---

# §4. Intent Envelope {#section-4}

**Status:** Stable (v1.0)

Goal/constraint/preference/handoff envelope types for richer agent coordination.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

An **intent envelope** is a structured message expressing desired transitions.
Where atomic facts (§2) record what *is* known, an intent envelope records what
an agent (or human) *wants* to happen — a goal plus the rules and context
needed to act on it. Envelopes are the unit Stigmem uses to coordinate
multi-agent work without inventing a bespoke handshake protocol per pair of
participants.

The envelope shape is fixed:

```
IntentEnvelope {
  id:          UUID
  from:        URI
  to:          URI[]
  goal:        string
  constraint:  Constraint[]
  preference:  Preference[]
  deference:   DeferenceRule[]
  escalation:  EscalationPolicy
  handoff:     HandoffPayload?
  created_at:  ISO 8601 UTC
  expires_at:  ISO 8601 UTC?
}
```

The fields split cleanly by purpose: `from`/`to` carry routing; `goal`,
`constraint`, `preference`, `deference` describe the work; `escalation`,
`handoff`, and `expires_at` describe what to do when execution falls off the
happy path. Each is detailed below.

### §4.1 `goal` {#section-4-1}

A free-text statement of what the sender wants done. Free-text is acceptable
because the goal is read by an agent that already has access to the same fact
substrate the sender does — full natural-language is more expressive than any
enumerated set of intents, and the recipient can interrogate the substrate
to fill in context.

So that the goal is also queryable by other agents (not just the recipient),
agents SHOULD additionally assert a machine-readable goal fact at envelope
creation time:

```
(entity=<intent-id>, relation="intent:goal", value={type:"string", v:"..."}, ...)
```

The `entity` is the envelope's `id`; the `relation` is the reserved
`intent:goal`; the `value` is the same string as the envelope's `goal` field.
Asserting this fact lets observers query for "what intents are currently in
flight against goal X?" without needing direct access to envelope traffic.

### §4.2 `constraint` {#section-4-2}

A constraint is a hard limit the recipient MUST respect. Unlike preferences
(§4.3), constraint violations are failures — if the recipient cannot satisfy
all listed constraints, it MUST escalate (§4.5) rather than partially satisfy:

```
Constraint { kind: string, limit: FactValue, unit: string? }
```

`kind` is the constraint axis (`budget`, `deadline`, `latency_ms`,
`max_calls`, etc. — see §9 namespace registry for reserved kinds). `limit`
carries the threshold using the typed `FactValue` shape from §2.1 so units
and types are explicit. `unit` is optional and only used when `kind` doesn't
imply one (e.g. `budget` always takes a money value with a currency code in
the `FactValue`, so `unit` would be redundant).

### §4.3 `preference` {#section-4-3}

A preference is a soft-weighted hint. Unlike constraints, the recipient MAY
violate preferences if doing so is necessary to satisfy a constraint; it
SHOULD optimize against them otherwise:

```
Preference { kind: string, value: FactValue, weight: float [0,1] }
```

`weight` allows expressing relative importance when multiple preferences
compete (e.g. "minimize cost weight=0.9, minimize latency weight=0.3" tells
the recipient to prefer cost optimization roughly 3× more than latency).

### §4.4 `deference` {#section-4-4}

A deference rule names another agent or system to consult before deciding
on a particular axis. Use it when the sender has specialised authority but
wants a second opinion on certain dimensions:

```
DeferenceRule { condition: string, defer_to: URI, timeout_s: integer? }
```

`condition` is a short predicate-style string (e.g. `cost > 100`,
`requires_legal_review`). `defer_to` is the URI of the agent or human to
consult. `timeout_s` bounds how long the recipient should wait for the
deferred party — on timeout, the recipient proceeds with its own judgment
and SHOULD record the timeout as a fact for audit.

### §4.5 `escalation` {#section-4-5}

The escalation policy fires when the recipient cannot satisfy the envelope
within its own authority — typically because a constraint can't be met or
no deference target responded in time:

```
EscalationPolicy {
  escalate_to:     URI
  channel:         string    // "stigmem" | "email" | "slack" (v0.1: stigmem only)
  priority:        "low" | "medium" | "high" | "critical"
  include_context: boolean
}
```

`escalate_to` is the URI of the human or agent to notify. `channel` selects
the delivery mechanism; v0.1 only supports `"stigmem"` (escalation arrives
as a fact in the escalator's inbox). `priority` is informational — it does
not change Stigmem's wire behaviour, but recipients can use it to drive
their own UX. `include_context` controls whether the escalation message
embeds the full envelope plus referenced facts (`true`) or just the
envelope ID with a query hint (`false`); set `false` when escalations
travel over channels with size limits.

### §4.6 `handoff` {#section-4-6}

A handoff is the payload sent to the next agent in a multi-step plan. It
exists separately from the envelope itself because handoffs MAY carry
artefacts (files, structured documents) that aren't appropriate to embed in
every envelope:

```
HandoffPayload {
  summary:       string
  fact_refs:     URI[]
  continuation:  string?
  artifacts:     { name: string, ref: URI }[]
}
```

`summary` is the one-paragraph human-readable handoff note. `fact_refs` MUST
be present and non-empty so the receiving agent can reconstitute context by
querying those facts (this requirement is what lets handoffs be terse —
the receiver has the same fact substrate as the sender). `continuation` is
an optional structured cursor for resumable workflows. `artifacts` carries
external content references (a deck URL, a spreadsheet, a diff) without
embedding them inline.

`handoff` MUST include `fact_refs` for context reconstitution.

---
