# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v0.4 — Draft

**Status:** Working draft. v0.3 sections are stable. §3.5 auth promoted from stub. §6 (Federation) unchanged, still open for community feedback.
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v0.4: Auth promoted from stub to Phase 2 implementation (§3.5); `PATCH /v1/facts/:id/confidence` retraction route (§5.4); `GET /v1/facts/:id` single-fact route (§5.5); `text` size guidance (§2.1); migration-friendliness note on schema (§10); gaps from Phase 2 implementation captured in §8.
- v0.3: Auth stub (§3.5), namespace registry plan (§9), expanded federation (§6), `stigmem:channel` escalation fix
- v0.2: `text` FactValue type, reification pattern, `valid_until` field
- v0.1: Initial spec

---

## 1. Motivation

Every agent, every human, and every company maintains its own private memory.
Facts decay silently, contradict each other across contexts, carry no provenance,
and cannot travel with the entity they describe.

Stigmem is the missing substrate: an open, federated knowledge fabric that any agent
or human can write facts into and query against, plus a typed intent/protocol layer
so agents can express goals, hand off work, and defer to each other without
designing bespoke handshake protocols every time.

Stigmem does **not** replace company orchestration platforms, agent runtimes, or tool
protocols like MCP. It sits above them all — the shared cognitive layer they can
all reason over.

---

## 2. Atomic Fact Shape

Every piece of knowledge in Stigmem is an **atomic fact**:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

| Field         | Type                              | Description |
|---------------|-----------------------------------|-------------|
| `entity`      | URI or opaque ID string           | What this fact is about. Examples: `user:alice`, `company:acme`, `agent:assistant`. |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI or opaque ID string           | Who asserted the fact. Examples: `agent:assistant`, `user:alice`, `system:stigmem`. |
| `timestamp`   | ISO 8601 UTC datetime             | When the fact was asserted. Set by the node at write time; clients may suggest. |
| `valid_until` | ISO 8601 UTC datetime or null     | Optional. If set, the fact is expired after this time. Distinct from `confidence`: use `confidence` for certainty, `valid_until` for temporal scope. |
| `confidence`  | float in [0.0, 1.0]              | Asserting party's confidence. 1.0 = certain, 0.5 = uncertain, 0.0 = retracted. |
| `scope`       | `FactScope` (see §2.2)            | Visibility / federation boundary. |

A fact is **immutable once written**. Updates are new facts. The latest fact for
a given `(entity, relation, scope)` triple wins unless contradiction policy applies
(see §3.3).

### 2.1 FactValue

```
FactValue =
  | { type: "string",    v: string }          // short identifier or label (≤1 KB recommended)
  | { type: "text",      v: string }          // unbounded narrative; markdown allowed; ≤64 KB inline; use ref for larger
  | { type: "number",    v: number }
  | { type: "boolean",   v: boolean }
  | { type: "datetime",  v: ISO8601 }
  | { type: "ref",       v: URI }             // pointer to another entity or external content
  | { type: "null" }                          // explicit "unknown / not applicable"
```

**`text` size guidance (v0.4):** Inline `text` values SHOULD be ≤ 64 KB. For larger payloads, assert a `ref` fact pointing to external storage and keep the text value as a summary. Nodes MAY reject `text` values above their configured limit; they MUST return HTTP 413 if they do.

### 2.2 FactScope

```
FactScope =
  | "local"     // visible only within this node, never federated
  | "team"      // visible within a logical team boundary (node-defined)
  | "company"   // visible within the owning company node
  | "public"    // federatable to any peer that has a handshake with this node
```

Nodes MUST NOT federate `local` or `team` facts without explicit operator override.

### 2.3 Reification (N-ary Relationships)

Mint a synthetic entity `stigmem:rel:{uuid}` and assert facts about it:

```
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"company:a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"company:b"})
(entity="stigmem:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
```

`rel:subject`, `rel:object`, and `rel:type` are reserved in the `rel:` namespace (see §9).

---

## 3. Fact Semantics

### 3.1 Provenance

Every fact carries `source` and `timestamp`. A node MUST store both without
modification. Clients querying facts MUST receive the original source, not the
relay chain.

### 3.2 Decay and Temporal Scope

**`valid_until`:** Facts whose `valid_until` has passed MUST NOT be returned unless
the caller sends `include_expired=true`. Expired facts remain in the store.

**TTL meta-fact:**
```
(entity=<fact-id>, relation="stigmem:ttl", value={type:"datetime", v:<expiry>}, ...)
```

**`valid_until` vs. `confidence`:** Orthogonal. A historical certain fact has
`confidence=1.0` and `valid_until` set to when it was superseded.

### 3.3 Contradiction

When two facts share `(entity, relation, scope)` with different values, nodes MUST
surface both. **Resolution order:**

1. Higher `confidence` wins.
2. Equal confidence → more recent `timestamp` wins.
3. Tie → both returned with `contradicted: true`; caller decides.

### 3.4 Scope Enforcement

Scope is enforced at read and write time. Cross-scope queries are additive.

### 3.5 Identity and Scope Enforcement (Phase 2 — Implemented)

**Status: Implemented in v0.4 reference node.** The following describes the Phase 2 auth model, promoted from the v0.3 stub.

#### Identity shape

```
Identity {
  entity_uri:   URI                    // the identity claim (e.g. "agent:assistant")
  credential:   string                 // Phase 2: opaque API key (SHA-256 stored server-side)
  node_url:     string                 // which node issued this credential
}
```

#### Phase 2 implementation (API-key)

Credentials are presented as `Authorization: Bearer <raw-key>`. The node stores only the SHA-256 hex digest of each key, never the raw value. Each key maps to an `entity_uri` and a JSON-array of permissions: `read`, `write`, `federate`.

**Auth mode flag:** Nodes MUST expose their auth mode at `/.well-known/stigmem` as `"auth": "none" | "required"`. Single-operator deployments MAY set `STIGMEM_AUTH_REQUIRED=false` (the default); all callers are trusted in that mode and the auth header is accepted but not enforced.

#### Scope rules with identity (target behavior)

| Scope     | Read | Write |
|-----------|------|-------|
| `local`   | Caller's `entity_uri` matches node's local identity space | Same |
| `team`    | Caller's identity is in the node-defined team set | Same |
| `company` | Caller has `read`/`write` permission | Same |
| `public`  | Any credentialed caller | Requires `write` permission + operator write policy |

**Phase 2 simplification:** All scopes are accessible to any valid key in Phase 2 (single-operator, no multi-tenancy). Per-scope key restrictions are a Phase 3 concern once federation introduces multiple operators.

**Phase 3 forward-compatibility:** Nodes SHOULD store `entity_uri` patterns now. Do not hard-code "all callers trusted" in a way that prevents future per-scope enforcement.

---

## 4. Intent Envelope

An **intent envelope** is a structured message expressing desired transitions.

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

### 4.1 `goal`

Agents SHOULD also write a machine-readable goal fact:
```
(entity=<intent-id>, relation="intent:goal", value={type:"string", v:"..."}, ...)
```

### 4.2 `constraint`

```
Constraint { kind: string, limit: FactValue, unit: string? }
```

### 4.3 `preference`

```
Preference { kind: string, value: FactValue, weight: float [0,1] }
```

### 4.4 `deference`

```
DeferenceRule { condition: string, defer_to: URI, timeout_s: integer? }
```

### 4.5 `escalation`

```
EscalationPolicy {
  escalate_to:     URI
  channel:         string    // "stigmem" | "email" | "slack" (v0.1: stigmem only)
  priority:        "low" | "medium" | "high" | "critical"
  include_context: boolean
}
```

### 4.6 `handoff`

```
HandoffPayload {
  summary:       string
  fact_refs:     URI[]
  continuation:  string?
  artifacts:     { name: string, ref: URI }[]
}
```

`handoff` MUST include `fact_refs` for context reconstitution.

---

## 5. Wire Format (v0.1 extended)

### 5.1 Assert a fact

```
POST /v1/facts
{ "entity": "user:alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "agent:assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", ...fact... }
```

### 5.2 Query facts

```
GET /v1/facts?entity=user:alice&relation=memory:role
→ 200 { "facts": [...], "total": 1, "cursor": null }
```

Query params: `entity`, `relation`, `source`, `scope`, `min_confidence`,
`after`, `include_contradicted`, `include_expired`, `cursor`, `limit`.

### 5.3 Node metadata

```
GET /.well-known/stigmem
→ 200 {
    "version":     "0.3",
    "node_id":     URI,
    "node_url":    string,
    "auth":        "none" | "required",
    "federation":  "disabled" | "enabled",
    "namespaces":  ["memory:", "intent:", ...],
    "spec":        URI                           // link to spec document
  }
```

This endpoint MUST be implemented by all conformant nodes. It enables peer
discovery, federation negotiation, and client auth-mode detection.

**v0.4 addition:** `node_url` and `spec` fields added to the response.

### 5.4 Retract a fact (v0.4)

To retract a fact, assert a new fact for the same `(entity, relation, scope)` with `confidence=0.0`. The original fact is never deleted; the retraction is a new immutable entry.

```
POST /v1/facts
{ "entity": "user:alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "agent:assistant", "confidence": 0.0, "scope": "company" }
→ 201 { ..., "confidence": 0.0 }
```

**Rationale:** A dedicated `PATCH /v1/facts/:id` endpoint was considered but rejected in Phase 2: it implies mutation, which conflicts with the immutable fact model. Retraction-as-assertion preserves audit history and simplifies the write path. The `min_confidence` query param filters retractions at read time.

### 5.5 Get a single fact (v0.4)

```
GET /v1/facts/:id
→ 200 { ...fact... }
→ 404 if not found
```

This route was absent in v0.3 and required during Phase 2 implementation when clients needed to look up a fact by its ID for debugging and dogfood readback.

---

## 6. Federation — Draft (community feedback wanted)

> **This section is a community RFC stub.** The sketch below captures design intent.
> Subsections marked ⚑ are open questions where community feedback is most needed.
> See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to contribute.

### 6.1 Peer Declaration

Two nodes federate when operators on both sides exchange a signed peer declaration:

```
PeerDeclaration {
  node_url:       string
  node_id:        URI
  public_key:     string
  allowed_scopes: FactScope[]
  rate_limit:     RateLimit?
  signed_at:      ISO 8601 UTC
  signature:      string
}
```

Exchange mechanism: operators POST each other's declaration to
`POST /v1/federation/peers`. A node MUST verify the signature before
activating the peer relationship.

> ⚑ **Community feedback wanted:** What is the right key management model?

### 6.2 Capability Advertisement

```
CapabilityAd {
  relations_understood: string[]
  decay_policies:       { relation: string, policy: string }[]
  contradiction_overrides: { relation: string, policy: "latest" | "highest_confidence" | "caller_decides" }[]
  federation_mode:      "push" | "pull" | "both"
  push_interval_s:      integer?
}
```

> ⚑ **Community feedback wanted:** Is capability advertisement the right model?

### 6.3 Fact Gossip

Facts with `scope=public` are replicated to all active peers.

**Deduplication:** Facts are globally identified by their `id` (UUID). Nodes MUST
NOT re-replicate a fact they received via federation.

**Provenance preservation:** When a node receives a federated fact, it MUST store
the original `source` and `timestamp` unchanged.

> ⚑ **Community feedback wanted:** Push vs. pull tradeoffs in practice.

### 6.4 Trust and Conflict across Nodes

Standard contradiction rules (§3.3) apply to federated facts. Nodes MAY apply
per-peer trust multipliers.

> ⚑ **Community feedback wanted:** Is per-peer trust the right primitive?

---

## 7. Design Decisions Log

| Decision | Rationale |
|---|---|
| Immutable facts | Preserves audit trail; contradictions first-class |
| JSON/HTTP for v0.1 | Universal; binary encoding is Phase 2 |
| Auth in v0.4 via API key | Simplest credential that enforces identity; JWTs/DIDs in Phase 3 |
| Retraction as assertion | Preserves audit trail; avoids mutation complexity |
| No `PATCH /v1/facts/:id` | Would imply mutation, breaking immutability invariant |
| Scope as enum | ACLs add complexity before federation exists |
| Confidence as float | More expressive than boolean; maps to LLM output probability |
| No global decay standard | Operators have heterogeneous retention needs |
| Handoff via fact refs | Keeps fabric as source of truth |
| Intent envelope separate | Facts = world state; intents = desired transitions |
| `text` type | Multi-paragraph bodies don't fit `string` |
| `text` size cap (64 KB) | Prevents unbounded memory growth; ref pattern covers larger blobs |
| Reification via `stigmem:rel:` | RDF-proven pattern for N-ary relationships |
| `valid_until` field | Separates temporal scope from confidence |
| `/.well-known/stigmem` endpoint | Enables auth-mode detection and peer discovery |
| Auth stub in v0.3 → impl in v0.4 | Phase 2 delivery validated model against real data |
| `node_url` in well-known | Required for federation peer-discovery; also useful for client config |
| `GET /v1/facts/:id` | Needed in practice: dogfood client needed point-lookup for readback |

---

## 8. Open Questions (v0.4)

1. **Entity URI scheme.** `user:alice` is informal. Should v0.4 require
   `stigmem://company.example/user/alice`? Leaning yes to avoid namespace collisions
   in federated deployments. **Phase 2 finding:** informal URIs worked for dogfood;
   the collision risk becomes real only once federation ships.

2. **Intent envelope scope.** Phase 2 implemented fact model only. Is the intent
   envelope necessary before federation? Proposing to defer it to Phase 4 adapters,
   which have a concrete consumer.

3. **Contradiction resolution extensibility.** Should operators plug in resolution
   functions? Phase 2 implemented spec-default (confidence → timestamp → both).
   Extensibility deferred until a concrete use case emerges.

4. **`text` size hard limit.** Implemented as 64 KB guidance in v0.4. Should nodes
   return 413 or silently truncate? **Recommendation:** 413 is correct (truncation
   destroys provenance).

5. **`GET /v1/facts/:id` pagination.** Single-fact GET was added in v0.4 based on
   Phase 2 implementation need. Should it be a first-class route or a query alias
   (`GET /v1/facts?id=<uuid>`)? Leaning toward dedicated route for clarity.

6. **Per-scope key restrictions.** Phase 2 grants all scopes to any valid key.
   Phase 3 should add a `allowed_scopes` field to api_keys. Open question: should
   this be additive (default none, opt in) or restrictive (default all, opt out)?

*(§8 Q1 from v0.2 — namespace governance — resolved in §9 below.)*

---

## 9. Namespace Registry

### 9.1 Reserved prefixes (maintained by spec)

| Prefix | Governed by | Purpose |
|---|---|---|
| `stigmem:` | Spec maintainers | Core protocol relations: `stigmem:ttl`, `stigmem:received_from`, `stigmem:member` |
| `rel:` | Spec maintainers | Reification primitives: `rel:subject`, `rel:object`, `rel:type` |

### 9.2 Community-registered prefixes

| Prefix | Status | Notes |
|---|---|---|
| `memory:` | Registered | Agent memory: role, preference, context |
| `intent:` | Registered | Intent envelope machine-readable facts |
| `roadmap:` | Registered | Project/product state facts |
| `preference:` | Registered | User/agent preferences |

### 9.3 Experimental prefix

`x-` prefix is reserved for informal/experimental use. No registration required.

---

## 10. Schema and Migration (v0.4)

Production nodes SHOULD use a migration-versioned schema. The reference implementation
uses numbered SQL migration files (`001_init.sql`, etc.) applied at startup via an
in-process runner. The `schema_migrations` table records applied versions.

**Recommended minimum schema:**

```sql
facts (
  id          TEXT PRIMARY KEY,
  entity      TEXT NOT NULL,
  relation    TEXT NOT NULL,
  value_type  TEXT NOT NULL,
  value_v     TEXT NOT NULL,
  source      TEXT NOT NULL,
  timestamp   TEXT NOT NULL,
  valid_until TEXT,            -- ISO 8601 UTC or NULL
  confidence  REAL NOT NULL,
  scope       TEXT NOT NULL
)
```

**Required indexes:** `(entity, relation)`, `(entity, relation, scope)`, `scope`, `timestamp`.
An index on `valid_until WHERE valid_until IS NOT NULL` is strongly recommended for nodes with high expiry-fact volume.

**Phase 2 finding:** The prototype schema lacked `valid_until`, requiring a schema bump before Phase 2 work could begin. All future schema additions SHOULD be additive (new columns with defaults, new tables) to preserve backward compatibility.

---

*v0.4-draft — §6 open for community feedback. See [CONTRIBUTING.md](../CONTRIBUTING.md).*
