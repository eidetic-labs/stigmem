# Loom — Federated Knowledge Fabric + Intent Protocol
## Specification v0.2 — DRAFT (Phase 0 scoping)

**Status:** Phase 0 draft. Not yet public. Subject to revision after design-partner interviews.  
**License:** Apache-2.0 (planned)  
**Working name:** Loom (board may rename)  
**Layer:** above the company (Paperclip, etc.), below the open internet  
**Changelog:** v0.2 adds `text` FactValue type (Gap 2), reification pattern for N-ary relationships (Gap 4), and `valid_until` field inspired by Zep/Graphiti temporal edge model (Gap 3 partial).

---

## 1. Motivation

Every agent, every human, and every company maintains its own private memory.
Facts decay silently, contradict each other across contexts, carry no provenance,
and cannot travel with the entity they describe.

Loom is the missing substrate: an open, federated knowledge fabric that any agent
or human can write facts into and query against, plus a typed intent/protocol layer
so agents can express goals, hand off work, and defer to each other without
designing bespoke handshake protocols every time.

Loom does **not** replace Paperclip (company substrate), OpenClaw (agent runtime),
or MCP (tool protocol). It sits one layer above them all — the shared cognitive
layer they can all reason over.

---

## 2. Atomic Fact Shape

Every piece of knowledge in Loom is an **atomic fact**:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

| Field         | Type                              | Description |
|---------------|-----------------------------------|-------------|
| `entity`      | URI or opaque ID string           | What this fact is about. Examples: `user:barry`, `company:acme`, `agent:cto`. |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI or opaque ID string           | Who asserted the fact. Examples: `agent:cto`, `user:barry`, `system:loom`. |
| `timestamp`   | ISO 8601 UTC datetime             | When the fact was asserted. Set by the node at write time; clients may suggest. |
| `valid_until` | ISO 8601 UTC datetime or null     | Optional. If set, the fact is considered expired (not active) after this time. Distinct from `confidence`: use `confidence` for certainty, `valid_until` for temporal scope. Inspired by Zep/Graphiti's `valid_at`/`invalid_at` temporal edge model. |
| `confidence`  | float in [0.0, 1.0]              | Asserting party's confidence. 1.0 = certain, 0.5 = uncertain, 0.0 = retracted. |
| `scope`       | `FactScope` (see §2.2)            | Visibility / federation boundary. |

A fact is **immutable once written**. Updates are new facts. The latest fact for
a given `(entity, relation, scope)` triple wins unless contradiction policy applies
(see §3.3).

### 2.1 FactValue

A value is one of:

```
FactValue =
  | { type: "string",    v: string }          // short identifier or label (≤1 KB recommended)
  | { type: "text",      v: string }          // unbounded narrative; markdown allowed
  | { type: "number",    v: number }
  | { type: "boolean",   v: boolean }
  | { type: "datetime",  v: ISO8601 }
  | { type: "ref",       v: URI }             // pointer to another entity or external content
  | { type: "null" }                          // explicit "unknown / not applicable"
```

`string` is for atomic identifiers, labels, and short values. `text` is for
multi-paragraph narrative content (rationale, notes, design decisions) where the
body is part of the fact, not a separate content store. Both are stored inline.

For very large documents (>64 KB), use `{ type: "ref", v: "<content-store-URI>" }`
and store the body in an external blob; the fact carries only the pointer. The URI
SHOULD resolve to the content over HTTP with a stable content hash in the path
(e.g. `sha256:<hash>`) so readers can verify integrity without a separate lookup.

### 2.2 FactScope

Scope controls where a fact is visible and whether it federates:

```
FactScope =
  | "local"     // visible only within this node, never federated
  | "team"      // visible within a logical team boundary (node-defined)
  | "company"   // visible within the owning company node
  | "public"    // federatable to any peer that has a handshake with this node
```

Nodes MUST NOT federate `local` or `team` facts without explicit operator override.

### 2.3 Reification (N-ary Relationships)

The base fact shape is binary: one `entity`, one `value`. When you need to model
a relationship that involves **multiple entities** or attach metadata to a
relationship itself, use **reification**:

1. Mint a synthetic entity URI: `loom:rel:{uuid}` (the "relationship node").
2. Assert atomic facts about the relationship node:

```
// "Acme–Giganomix partnership requires board approval"
(entity="loom:rel:abc123", relation="rel:subject",  value={type:"ref", v:"company:acme"})
(entity="loom:rel:abc123", relation="rel:object",   value={type:"ref", v:"company:giganomix"})
(entity="loom:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
(entity="loom:rel:abc123", relation="rel:approver", value={type:"ref",   v:"entity:board"})
```

Relationship nodes SHOULD follow the `loom:rel:` prefix so queries can distinguish
them from domain entities. The `rel:subject`, `rel:object`, and `rel:type` relations
are reserved in the `rel:` namespace.

**When NOT to reify:** if the relationship is truly binary and the value is a
simple scalar or a single ref, use the direct fact shape. Reification adds query
complexity; use it only when two or more entities participate in the same statement.

---

## 3. Fact Semantics

### 3.1 Provenance

Every fact carries `source` and `timestamp`. A node MUST store both without
modification. Clients querying facts MUST receive the original source, not the
relay chain, so downstream consumers can make their own trust judgments.

Facts with `source = system:loom` are written by the node itself (e.g., TTL
expiry markers, contradiction tombstones).

### 3.2 Decay and Temporal Scope

Facts are permanent records by default.

**Temporal scope (`valid_until`):** The preferred mechanism for time-bounded facts.
Set `valid_until` at write time when you know the fact has a natural expiry — e.g.,
a scheduled event, a fiscal-quarter goal, a temporary policy. A node MUST NOT
return facts whose `valid_until` has passed unless the caller explicitly includes
`include_expired=true`. Expired facts remain in the store (immutable record); they
are filtered at read time.

**TTL via meta-fact:** For facts whose expiry is not known at write time, decay can
be expressed as a separate meta-fact:

```
(entity=<fact-id>, relation="loom:ttl", value={type:"datetime", v:<expiry>},
 source=<original-source>, ...)
```

A node MAY tombstone expired facts by writing a `confidence=0.0` successor fact.
Clients querying an expired fact SHOULD receive it with a `decayed: true` flag so
they can distinguish "unknown" from "was known, now expired."

**`valid_until` vs. `confidence`:** These are orthogonal. A historically certain
fact (e.g., "roadmap v3 was active in Q3 2025") should have `confidence=1.0` and
`valid_until` set to when it became superseded. Do not lower confidence to express
that a fact is historical — that conflates certainty with recency.

Decay rates are not globally standardized in v0.2 — left to node operators. Phase 5
introduces built-in decay functions.

### 3.3 Contradiction

When two facts share the same `(entity, relation, scope)` triple but have different
values, a contradiction exists. Loom nodes MUST surface contradictions rather than
silently discarding one.

**Resolution order (v0.1 default):**

1. Higher `confidence` wins.
2. On equal confidence, more recent `timestamp` wins.
3. On tie, both facts are returned with `contradicted: true`; the caller decides.

A node operator MAY configure per-relation override policies. Contradiction
resolution logic is a first-class observable: callers can always request
`include_contradicted=true` to see all competing facts.

### 3.4 Scope

Scope is enforced at read and write time:

- A write with `scope=public` to a node with no federation peers is stored locally;
  it becomes federable when peers are added.
- A read with no `scope` filter returns facts from all scopes the caller is
  authorized to see (authorization is out of scope for v0.1 — all callers trusted).
- Cross-scope queries are additive: `scope IN (local, company)` returns the union.

---

## 4. Intent Envelope

An **intent envelope** is a structured message from one actor (agent or human) to
one or more recipients, expressing what the sender wants to happen. Unlike facts
(which describe the world), intents describe desired transitions.

```
IntentEnvelope {
  id:          UUID (generated by sender)
  from:        URI                     // sender entity
  to:          URI[]                   // target entity/entities
  goal:        string                  // what the sender wants to achieve
  constraint:  Constraint[]            // non-negotiable limits
  preference:  Preference[]            // soft preferences
  deference:   DeferenceRule[]         // who to defer to on conflict
  escalation:  EscalationPolicy        // when/how to escalate
  handoff:     HandoffPayload?         // structured context transfer (optional)
  created_at:  ISO 8601 UTC
  expires_at:  ISO 8601 UTC?           // null = no expiry
}
```

### 4.1 `goal`

A human-readable string describing the desired outcome. Agents SHOULD also write
a machine-readable goal fact into the knowledge fabric for the same interaction:

```
(entity=<intent-id>, relation="intent:goal", value={type:"string", v:"..."}, ...)
```

### 4.2 `constraint`

Non-negotiable limits. A recipient MUST NOT proceed if a constraint cannot be met;
instead it MUST escalate or refuse.

```
Constraint {
  kind:    string           // e.g. "budget", "deadline", "scope"
  limit:   FactValue        // the hard limit
  unit:    string?          // e.g. "USD", "hours", "words"
}
```

### 4.3 `preference`

Soft preferences. A recipient SHOULD try to honor them but MAY override with a
reason written back into the fabric.

```
Preference {
  kind:    string           // e.g. "tone", "format", "priority"
  value:   FactValue
  weight:  float [0,1]      // 1.0 = strong preference
}
```

### 4.4 `deference`

When the receiving agent encounters an ambiguity or conflict, `deference` says who
to ask:

```
DeferenceRule {
  condition:  string        // human-readable trigger ("cost > $500")
  defer_to:   URI           // entity to consult
  timeout_s:  integer?      // wait this many seconds before escalating
}
```

### 4.5 `escalation`

If a constraint is unresolvable or a deference times out:

```
EscalationPolicy {
  escalate_to:  URI         // entity to notify
  channel:      string      // e.g. "loom", "email", "slack" (v0.1: loom only)
  priority:     "low" | "medium" | "high" | "critical"
  include_context: boolean  // attach full intent + relevant facts
}
```

### 4.6 `handoff`

Structured transfer of in-flight context from one agent to another:

```
HandoffPayload {
  summary:       string              // human-readable state summary
  fact_refs:     URI[]               // relevant fact IDs from the fabric
  continuation:  string?            // what the receiver should do next
  artifacts:     { name: string, ref: URI }[]  // files, outputs, etc.
}
```

A `handoff` MUST include `fact_refs` so the receiving agent can reconstitute
context from the fabric rather than relying solely on the summary.

---

## 5. Wire Format (v0.1)

v0.1 uses JSON over HTTP. Future versions MAY add a binary encoding.

### 5.1 Assert a fact

```
POST /v1/facts
Content-Type: application/json

{
  "entity":     "user:barry",
  "relation":   "memory:role",
  "value":      { "type": "string", "v": "CEO" },
  "source":     "agent:cto",
  "confidence": 1.0,
  "scope":      "company"
}

→ 201 Created
{
  "id":        "<fact-uuid>",
  "timestamp": "2026-05-01T00:00:00Z",
  ...full fact...
}
```

### 5.2 Query facts

Pattern query: any field may be omitted (wildcard). Multiple values for a field
are OR-joined.

```
GET /v1/facts?entity=user:barry&relation=memory:role

→ 200 OK
{
  "facts": [ ...FactRecord... ],
  "total":  1,
  "cursor": null
}
```

Supported query parameters: `entity`, `relation`, `source`, `scope`, `min_confidence`,
`after` (timestamp), `include_contradicted`, `include_decayed`, `cursor`, `limit`.

---

## 6. Federation Handshake (Phase 3 sketch — not v0.1)

Federation is out of scope for Phase 0. This sketch captures the design intent
so the v0.1 spec can be written with federation in mind.

Two nodes federate when:

1. Operators on both sides exchange a signed **peer declaration** (node URL,
   public key, allowed scopes, rate limits).
2. Nodes exchange a **capability advertisement** listing which relations they
   understand, their decay policies, and contradiction resolution overrides.
3. Facts scoped `public` are gossiped on a push or pull cadence (operator choice).

The handshake deliberately mirrors email's MX/SMTP trust model and ActivityPub's
`Follow`/`Accept` exchange. Details deferred to Phase 3.

---

## 7. Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| Immutable facts, not updates | Preserves audit trail; contradictions are first-class, not silent overwrites |
| JSON/HTTP for v0.1 | Boring and universal; binary encoding is a Phase 2 optimization |
| No auth in v0.1 | Prototype only; auth is a production-hardening concern (Phase 2+) |
| Scope as enum, not ACL | ACLs add complexity before federation exists; enum covers 95% of cases |
| Confidence as [0,1] float | More expressive than boolean; maps to LLM output probability language |
| No global decay standard | Node operators have heterogeneous retention needs; standardize in Phase 5 |
| Handoff via fact refs, not copies | Keeps the fabric as source of truth; prevents drift between snapshot and reality |
| Intent envelope separate from facts | Facts = world state; intents = desired transitions. Conflating them muddies both. |
| `text` type added alongside `string` | Shadow migration (D3) revealed multi-paragraph rationale bodies don't fit `string`. Inline `text` avoids a content store for moderate-size bodies. `ref` for blobs >64 KB. |
| Reification via `loom:rel:` entities | Shadow migration surfaced a policy involving three entities; no natural primary entity. Reification is the RDF-proven pattern; encoding N-ary logic into a value type adds parsing complexity downstream. |
| `valid_until` field added to fact shape | Zep/Graphiti `valid_at`/`invalid_at` temporal edge model is the closest prior art. Separating temporal scope from `confidence` prevents "lower confidence to express a historical fact" anti-pattern found in D3. |

---

## 8. Open Questions (Phase 0 exit)

1. **Relation namespace governance.** Who owns `memory:*`, `intent:*`, `rel:*`?
   IANA-style registry, or community PRs to a spec repo? Unresolved before Phase 1.

2. **Entity URI scheme.** `user:barry` is informal. Should v0.2 require a more
   structured URI (`loom://company.acme/user/barry`)? Leaning yes before Phase 1
   to avoid namespace collisions in federated deployments.

3. **Handoff vs. fact-only approach.** Is the intent envelope necessary in v0.1,
   or should Phase 0 test only the fact shape and defer the envelope to Phase 2?
   Design partner feedback should resolve this.

4. **Contradiction resolution extensibility.** Should operators be able to plug in
   arbitrary resolution functions (LLM-based synthesis, etc.) in v0.1?

5. **Scope enforcement without auth.** In a multi-tenant deployment, scope is
   meaningless without identity. v0.2 acknowledges this gap honestly; auth is a
   Phase 2 requirement.

6. **`text` size limit.** 64 KB threshold for inline `text` vs. `ref` is arbitrary.
   Should v0.2 specify a hard limit or leave it to node operators?

7. **Reification query ergonomics.** The `loom:rel:*` pattern requires two-hop
   queries (find the rel entity, then fetch its subject/object). Should v0.2 define
   a shorthand query parameter (`?subject=X&object=Y`) or keep it pure graph traversal?

---

*v0.1 drafted by CTO, Acme Corp — Phase 0 scoping sprint. v0.2 updated with Gap 2/3/4 fixes from shadow migration and Zep/Graphiti peer research. See [ACM-19](/ACM/issues/ACM-19) for sprint context.*
