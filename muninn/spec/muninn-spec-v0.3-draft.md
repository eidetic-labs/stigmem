# Muninn — Federated Knowledge Fabric + Intent Protocol
## Specification v0.3 — Draft

**Status:** Working draft. v0.2 sections are stable. §6 (Federation) is open for community feedback.
**License:** Apache-2.0
**Authors:** Giganomix
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v0.3: Auth stub (§3.5), namespace registry plan (§9), expanded federation (§6), `muninn:channel` escalation fix
- v0.2: `text` FactValue type, reification pattern, `valid_until` field
- v0.1: Initial spec

---

## 1. Motivation

Every agent, every human, and every company maintains its own private memory.
Facts decay silently, contradict each other across contexts, carry no provenance,
and cannot travel with the entity they describe.

Muninn is the missing substrate: an open, federated knowledge fabric that any agent
or human can write facts into and query against, plus a typed intent/protocol layer
so agents can express goals, hand off work, and defer to each other without
designing bespoke handshake protocols every time.

Muninn does **not** replace company orchestration platforms, agent runtimes, or tool
protocols like MCP. It sits above them all — the shared cognitive layer they can
all reason over.

---

## 2. Atomic Fact Shape

Every piece of knowledge in Muninn is an **atomic fact**:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

| Field         | Type                              | Description |
|---------------|-----------------------------------|-------------|
| `entity`      | URI or opaque ID string           | What this fact is about. Examples: `user:alice`, `company:acme`, `agent:assistant`. |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI or opaque ID string           | Who asserted the fact. Examples: `agent:assistant`, `user:alice`, `system:muninn`. |
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
  | { type: "text",      v: string }          // unbounded narrative; markdown allowed
  | { type: "number",    v: number }
  | { type: "boolean",   v: boolean }
  | { type: "datetime",  v: ISO8601 }
  | { type: "ref",       v: URI }             // pointer to another entity or external content
  | { type: "null" }                          // explicit "unknown / not applicable"
```

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

Mint a synthetic entity `muninn:rel:{uuid}` and assert facts about it:

```
(entity="muninn:rel:abc123", relation="rel:subject",  value={type:"ref", v:"company:a"})
(entity="muninn:rel:abc123", relation="rel:object",   value={type:"ref", v:"company:b"})
(entity="muninn:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
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
(entity=<fact-id>, relation="muninn:ttl", value={type:"datetime", v:<expiry>}, ...)
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

### 3.5 Identity and Scope Enforcement — Auth Stub (Phase 2)

**This section is a forward-compatible placeholder. Auth is NOT enforced in v0.1/v0.2.**

Scope without identity is theater. In a multi-tenant deployment, `scope=company`
is meaningless if any caller can claim to be any entity. Muninn v0.1 makes this
gap explicit and intentional: the prototype is single-operator, all callers trusted.

Production identity (Phase 2) will gate scope semantics on a verified caller
identity. The intended model:

```
Identity {
  entity_uri:   URI                    // the identity claim (e.g. "agent:assistant")
  credential:   SignedToken            // verifiable proof (JWT, DID-auth, etc.)
  node_url:     string                 // which node issued this credential
}
```

**Scope rules with identity (Phase 2 target behavior):**

| Scope | Read | Write |
|---|---|---|
| `local` | Caller's `entity_uri` matches node's local identity space | Same |
| `team` | Caller's identity is in the node-defined team set | Same |
| `company` | Caller's identity is credentialed by the owning node | Same |
| `public` | Any credentialed caller on any federated node | Requires operator-defined write policy |

**What implementations SHOULD do now (forward-compatibility):**
- Accept an optional `Authorization` header on all routes; ignore but log it in v0.1
- Do not hard-code "all callers trusted" in a way that prevents a future auth layer
- The identity model above SHOULD inform data modeling: store `entity_uri` patterns now

**v0.1 commitment:** Nodes MUST document their auth status in a `/.well-known/muninn`
endpoint response (see §5.3). This allows clients to detect whether they are talking
to a trusted-only or auth-enforced node.

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
  channel:         string    // "muninn" | "email" | "slack" (v0.1: muninn only)
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

## 5. Wire Format (v0.1)

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
GET /.well-known/muninn
→ 200 {
    "version":     "0.1",
    "node_id":     URI,
    "auth":        "none" | "required",   // v0.1 = "none"
    "federation":  "disabled" | "enabled",
    "namespaces":  ["memory:", "intent:", ...]  // relations this node understands
  }
```

This endpoint MUST be implemented by all conformant nodes. It enables peer
discovery, federation negotiation, and client auth-mode detection.

---

## 6. Federation — Draft (community feedback wanted)

> **This section is a community RFC stub.** The sketch below captures design intent.
> Subsections marked ⚑ are open questions where community feedback is most needed.
> See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to contribute.

### 6.1 Peer Declaration

Two nodes federate when operators on both sides exchange a signed peer declaration:

```
PeerDeclaration {
  node_url:       string          // canonical URL of the declaring node
  node_id:        URI             // stable identity URI
  public_key:     string          // base64-encoded public key for signature verification
  allowed_scopes: FactScope[]     // which scopes this node will accept from the peer
  rate_limit:     RateLimit?      // requests/sec, facts/hour limits
  signed_at:      ISO 8601 UTC
  signature:      string          // signs the above fields; algorithm in key metadata
}
```

Exchange mechanism: operators POST each other's declaration to
`POST /v1/federation/peers`. A node MUST verify the signature before
activating the peer relationship.

> ⚑ **Community feedback wanted:** What is the right key management model? Raw RSA/EC keys,
> DIDs, or something lighter? What's the revocation story?

### 6.2 Capability Advertisement

After peer declaration, nodes exchange capability advertisements:

```
CapabilityAd {
  relations_understood: string[]     // namespaced relations this node indexes
  decay_policies:       { relation: string, policy: string }[]
  contradiction_overrides: { relation: string, policy: "latest" | "highest_confidence" | "caller_decides" }[]
  federation_mode:      "push" | "pull" | "both"
  push_interval_s:      integer?
}
```

Nodes SHOULD only push facts for relations the peer has declared it understands.
Unknown relations MUST be stored but MAY be deprioritized for sync.

> ⚑ **Community feedback wanted:** Is capability advertisement the right model, or should nodes
> just accept all `public` facts and filter locally? Tradeoffs around bandwidth vs.
> control?

### 6.3 Fact Gossip

Facts with `scope=public` are replicated to all active peers.

**Push model:** The originating node pushes batches of new `public` facts to peers
at a configurable interval (default: as-available, bounded by rate limit).

**Pull model:** Peers poll `GET /v1/facts?scope=public&after=<cursor>` at a
configurable interval.

**Deduplication:** Facts are globally identified by their `id` (UUID). Nodes MUST
NOT re-replicate a fact they received via federation (no gossip loops).

**Provenance preservation:** When a node receives a federated fact, it MUST store
the original `source` and `timestamp` unchanged. The receiving node SHOULD add a
`muninn:received_from` meta-fact:
```
(entity=<fact-id>, relation="muninn:received_from", value={type:"ref", v:<peer-node-id>}, ...)
```

> ⚑ **Community feedback wanted:** Push vs. pull tradeoffs in practice. What failure modes
> have you seen in real gossip systems? How do you handle a node that goes offline
> for days and comes back with a large backlog?

### 6.4 Trust and Conflict across Nodes

When a federated fact contradicts a local fact, the standard contradiction rules
(§3.3) apply. Nodes MAY apply a trust weight to federated facts:

- A fact from a peer with `allowed_scopes=["public"]` has no special trust bonus.
- Operators MAY configure per-peer trust multipliers that adjust effective confidence.

> ⚑ **Community feedback wanted:** Is per-peer trust the right primitive? Alternatives:
> namespace-based trust, cryptographic endorsement, or just surface contradictions
> without a trust layer?

---

## 7. Design Decisions Log

| Decision | Rationale |
|---|---|
| Immutable facts | Preserves audit trail; contradictions first-class |
| JSON/HTTP for v0.1 | Universal; binary encoding is Phase 2 |
| No auth in v0.1 | Prototype only; §3.5 stub ensures forward-compatibility |
| Scope as enum | ACLs add complexity before federation exists |
| Confidence as float | More expressive than boolean; maps to LLM output probability |
| No global decay standard | Operators have heterogeneous retention needs |
| Handoff via fact refs | Keeps fabric as source of truth |
| Intent envelope separate | Facts = world state; intents = desired transitions |
| `text` type | Multi-paragraph bodies don't fit `string` |
| Reification via `muninn:rel:` | RDF-proven pattern for N-ary relationships |
| `valid_until` field | Separates temporal scope from confidence (Zep/Graphiti prior art) |
| `/.well-known/muninn` endpoint | Enables auth-mode detection and peer discovery without out-of-band coordination |
| Auth stub in v0.3 | §5 Q5 surfaced that scope without identity is theater. Documenting the intended model now prevents implementations that are hard to retrofit. |

---

## 8. Open Questions

1. **Entity URI scheme.** `user:alice` is informal. Should v0.3 require
   `muninn://company.acme/user/alice`? Leaning yes to avoid namespace collisions
   in federated deployments. Community input wanted.

2. **Handoff vs. fact-only.** Is the intent envelope necessary in v0.1 or should
   Phase 0 test only the fact shape? Community feedback will resolve.

3. **Contradiction resolution extensibility.** Should operators plug in arbitrary
   resolution functions (LLM synthesis, etc.) in v0.1?

4. **`text` size limit.** 64 KB for inline `text` vs. `ref` — hard limit or
   operator-defined?

5. **Reification query ergonomics.** Should v0.3 define `?subject=X&object=Y`
   shorthand or keep it pure graph traversal?

*(§8 Q1 from v0.2 — namespace governance — resolved in §9 below.)*

---

## 9. Namespace Registry

Namespace prefixes govern the relation vocabulary. This section establishes the
governance model; a machine-readable registry lives at `namespaces.md` in the
spec repo.

### 9.1 Reserved prefixes (maintained by spec)

| Prefix | Governed by | Purpose |
|---|---|---|
| `muninn:` | Spec maintainers | Core protocol relations: `muninn:ttl`, `muninn:received_from`, `muninn:member` |
| `rel:` | Spec maintainers | Reification primitives: `rel:subject`, `rel:object`, `rel:type` |

These prefixes MUST NOT be used for application-level facts. Breaking changes
require a spec version bump.

### 9.2 Community-registered prefixes

| Prefix | Status | Notes |
|---|---|---|
| `memory:` | Registered | Agent memory: role, preference, context |
| `intent:` | Registered | Intent envelope machine-readable facts |
| `roadmap:` | Registered | Project/product state facts |
| `preference:` | Registered | User/agent preferences |

**Registration process:** Submit a PR to `namespaces.md` in the spec repo with:
- The prefix string
- Owner/maintainer (GitHub handle or org)
- Intended use and example relations
- A link to any existing implementations

Prefixes are registered on a first-come, first-served basis. The spec maintainer
merges if no namespace collision exists.

### 9.3 Experimental prefix

`x-` prefix is reserved for informal/experimental use: e.g., `x-myapp:custom-field`.
No registration required. Not guaranteed to survive federation.

---

*v0.3-draft — §6 open for community feedback. See [CONTRIBUTING.md](../CONTRIBUTING.md).*
