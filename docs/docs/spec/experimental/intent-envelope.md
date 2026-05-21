---
spec_id: Spec-X8-Intent-Envelope
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-14
supersedes: spec/stigmem-spec-v0.9.0a1.md section 4 intent envelope material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
title: §4. Intent Envelope
sidebar_label: §4 Intent Envelope
audience: Spec
description: "Stigmem spec section 4 — Goal/constraint/preference/handoff envelope types for richer agent coordination."
stability: experimental
since: 0.9.0a1
---

# §4. Intent Envelope {#section-4}

<p className="stigmem-meta"><span>5 min read</span><span>Spec contributor · Adapter author</span><span>Experimental · future plugin line</span></p>

<div className="stigmem-lead">

**What this section covers**

A structured message expressing desired transitions. Where atomic
facts (§2) record what *is* known, an intent envelope records what
an agent (or human) *wants* to happen — a goal plus the rules and
context needed to act on it.

</div>

**Status:** Experimental / deferred indefinitely

**Source material:** Archived evolutionary spec snapshots. This page preserves the maintained Spec-X home for intent-envelope semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

<div className="stigmem-keypoint">

**Envelopes are the unit Stigmem uses to coordinate multi-agent work.**

Without inventing a bespoke handshake protocol per pair of
participants.

</div>

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

The fields split cleanly by purpose:

<div className="stigmem-grid">

<div><h4>Routing</h4><p><code>from</code> / <code>to</code> carry routing.</p></div>
<div><h4>Work description</h4><p><code>goal</code>, <code>constraint</code>, <code>preference</code>, <code>deference</code> describe the work.</p></div>
<div><h4>Off-happy-path</h4><p><code>escalation</code>, <code>handoff</code>, <code>expires_at</code> describe what to do when execution falls off the happy path.</p></div>

</div>

### §4.1 `goal` {#section-4-1}

A free-text statement of what the sender wants done. Free-text is acceptable because the goal is read by an agent that already has access to the same fact substrate the sender does — full natural-language is more expressive than any enumerated set of intents, and the recipient can interrogate the substrate to fill in context.

So that the goal is also queryable by other agents (not just the recipient), agents SHOULD additionally assert a machine-readable goal fact at envelope creation time:

```
(entity=<intent-id>, relation="intent:goal", value={type:"string", v:"..."}, ...)
```

The `entity` is the envelope's `id`; the `relation` is the reserved `intent:goal`; the `value` is the same string as the envelope's `goal` field. Asserting this fact lets observers query for "what intents are currently in flight against goal X?" without needing direct access to envelope traffic.

### §4.2 `constraint` {#section-4-2}

<div className="stigmem-keypoint">

**Constraint violations are failures.**

Unlike preferences, a constraint is a hard limit the recipient MUST
respect. If the recipient cannot satisfy all listed constraints, it
MUST escalate (§4.5) rather than partially satisfy.

</div>

```
Constraint { kind: string, limit: FactValue, unit: string? }
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>kind</code></dt>
<dt><span className="stigmem-fields__type">axis</span></dt>
<dd>The constraint axis (<code>budget</code>, <code>deadline</code>, <code>latency_ms</code>, <code>max_calls</code> — see §9 namespace registry).</dd>
</div>

<div>
<dt><code>limit</code></dt>
<dt><span className="stigmem-fields__type">FactValue</span></dt>
<dd>Threshold using the typed <code>FactValue</code> shape so units and types are explicit.</dd>
</div>

<div>
<dt><code>unit</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Used only when <code>kind</code> doesn't imply one.</dd>
</div>

</div>

### §4.3 `preference` {#section-4-3}

A preference is a soft-weighted hint. Unlike constraints, the recipient MAY violate preferences if doing so is necessary to satisfy a constraint; it SHOULD optimize against them otherwise:

```
Preference { kind: string, value: FactValue, weight: float [0,1] }
```

`weight` allows expressing relative importance when multiple preferences compete (e.g. "minimize cost weight=0.9, minimize latency weight=0.3" tells the recipient to prefer cost optimization roughly 3× more than latency).

### §4.4 `deference` {#section-4-4}

A deference rule names another agent or system to consult before deciding on a particular axis. Use it when the sender has specialised authority but wants a second opinion on certain dimensions:

```
DeferenceRule { condition: string, defer_to: URI, timeout_s: integer? }
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>condition</code></dt>
<dt><span className="stigmem-fields__type">predicate</span></dt>
<dd>Short predicate-style string (e.g. <code>cost &gt; 100</code>, <code>requires_legal_review</code>).</dd>
</div>

<div>
<dt><code>defer_to</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd>URI of the agent or human to consult.</dd>
</div>

<div>
<dt><code>timeout_s</code></dt>
<dt><span className="stigmem-fields__type">integer?</span></dt>
<dd>Bounds how long the recipient should wait. On timeout, the recipient proceeds with its own judgment and SHOULD record the timeout as a fact for audit.</dd>
</div>

</div>

### §4.5 `escalation` {#section-4-5}

The escalation policy fires when the recipient cannot satisfy the envelope within its own authority — typically because a constraint can't be met or no deference target responded in time:

```
EscalationPolicy {
  escalate_to:     URI
  channel:         string    // "stigmem" | "email" | "slack" (v0.1: stigmem only)
  priority:        "low" | "medium" | "high" | "critical"
  include_context: boolean
}
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>escalate_to</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd>The human or agent to notify.</dd>
</div>

<div>
<dt><code>channel</code></dt>
<dt><span className="stigmem-fields__type">delivery</span></dt>
<dd>v0.1 only supports <code>"stigmem"</code> (escalation arrives as a fact in the escalator's inbox).</dd>
</div>

<div>
<dt><code>priority</code></dt>
<dt><span className="stigmem-fields__type">informational</span></dt>
<dd>Does not change Stigmem's wire behavior, but recipients can use it to drive their own UX.</dd>
</div>

<div>
<dt><code>include_context</code></dt>
<dt><span className="stigmem-fields__type">boolean</span></dt>
<dd>Controls whether the escalation embeds the full envelope plus referenced facts (<code>true</code>) or just the envelope ID with a query hint (<code>false</code>); set <code>false</code> when escalations travel over channels with size limits.</dd>
</div>

</div>

### §4.6 `handoff` {#section-4-6}

A handoff is the payload sent to the next agent in a multi-step plan. It exists separately from the envelope itself because handoffs MAY carry artefacts (files, structured documents) that aren't appropriate to embed in every envelope:

```
HandoffPayload {
  summary:       string
  fact_refs:     URI[]
  continuation:  string?
  artifacts:     { name: string, ref: URI }[]
}
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>summary</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>One-paragraph human-readable handoff note.</dd>
</div>

<div>
<dt><code>fact_refs</code></dt>
<dt><span className="stigmem-fields__type">non-empty</span></dt>
<dd>MUST be present and non-empty so the receiving agent can reconstitute context by querying those facts.</dd>
</div>

<div>
<dt><code>continuation</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Structured cursor for resumable workflows.</dd>
</div>

<div>
<dt><code>artifacts</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>External content references (a deck URL, a spreadsheet, a diff) without embedding them inline.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**`handoff` MUST include `fact_refs` for context reconstitution.**

This is what lets handoffs be terse — the receiver has the same fact
substrate as the sender.

</div>

---
