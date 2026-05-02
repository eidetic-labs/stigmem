# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v0.5 — Draft

**Status:** Working draft. §1–5, §7–10 promoted from v0.4 (stable). §6 Federation promoted from RFC stub to concrete spec. §11 Failure Modes new.
**License:** Apache-2.0
**Authors:** Giganomix
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v0.5: §6 Federation promoted from RFC stub to concrete implementable spec; new federation wire routes (§5.6–§5.10); HLC timestamps (§2.4); per-scope key restrictions on `api_keys` (§3.5); conflict-first-class semantics formalized (§3.3, §6.5); §11 Failure Modes acceptance scenarios; schema additions (§10); design decisions updated.
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
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

| Field         | Type                              | Description |
|---------------|-----------------------------------|-------------|
| `entity`      | URI or opaque ID string           | What this fact is about. Examples: `user:alice`, `company:acme`, `agent:assistant`. |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI or opaque ID string           | Who asserted the fact. Examples: `agent:assistant`, `user:alice`, `system:stigmem`. |
| `timestamp`   | ISO 8601 UTC datetime             | Wall-clock time when the fact was asserted. Set by the node at write time; clients may suggest. |
| `hlc`         | HLC string (see §2.4)            | Hybrid Logical Clock timestamp. Causality-preserving; required for federation. |
| `valid_until` | ISO 8601 UTC datetime or null     | Optional. If set, the fact is expired after this time. |
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
`company`-scoped facts are only federated when the active PeerDeclaration explicitly
includes `"company"` in `allowed_scopes` (see §6.1).

### 2.3 Reification (N-ary Relationships)

Mint a synthetic entity `stigmem:rel:{uuid}` and assert facts about it:

```
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"company:a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"company:b"})
(entity="stigmem:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
```

`rel:subject`, `rel:object`, and `rel:type` are reserved in the `rel:` namespace (see §9).

### 2.4 Hybrid Logical Clock (HLC) — v0.5

Every node maintains a **Hybrid Logical Clock**:

```
HLC = wall_ms || counter
```

Format: `"{wall_ms_utc}.{counter}"` — e.g. `"1746230400000.003"`.

**Advance rules:**
1. On local write: `hlc = max(now_ms, last_hlc_ms)` as `wall_ms`; increment `counter` if `wall_ms` unchanged.
2. On receiving a federated fact: `hlc = max(now_ms, received_hlc_ms)` as `wall_ms`; increment counter.

**Causal ordering:** Two facts `a`, `b` are causally ordered iff `a.hlc < b.hlc`. Equal HLCs on different nodes indicate concurrent writes; standard contradiction policy (§3.3) applies.

**Wire encoding:** `hlc` is included in all fact responses and replication payloads. Clients that do not understand HLC MAY ignore the field; nodes MUST store and propagate it.

---

## 3. Fact Semantics

### 3.1 Provenance

Every fact carries `source` and `timestamp`. A node MUST store both without
modification. Clients querying facts MUST receive the original source, not the
relay chain.

**Federated provenance:** Inbound federated facts MUST additionally carry a
`stigmem:received_from` meta-fact (asserted automatically by the receiving node):

```
(entity=<fact-id>, relation="stigmem:received_from",
 value={type:"ref", v:"<originating-node-id>"},
 source="system:stigmem", ...)
```

This meta-fact is stored locally and MUST NOT be re-replicated.

### 3.2 Decay and Temporal Scope

**`valid_until`:** Facts whose `valid_until` has passed MUST NOT be returned unless
the caller sends `include_expired=true`. Expired facts remain in the store.

**TTL meta-fact:**
```
(entity=<fact-id>, relation="stigmem:ttl", value={type:"datetime", v:<expiry>}, ...)
```

**`valid_until` vs. `confidence`:** Orthogonal. A historical certain fact has
`confidence=1.0` and `valid_until` set to when it was superseded.

### 3.3 Contradiction — v0.5 formalized

A **contradiction** exists when two facts `a`, `b` satisfy all of:
- `a.entity == b.entity`
- `a.relation == b.relation`
- `a.scope == b.scope`
- `a.value != b.value`
- `a.confidence > 0.0 && b.confidence > 0.0`

**Both facts are retained. Neither is silently overwritten.**

**Resolution order at query time:**
1. Higher `confidence` wins.
2. Equal confidence → higher `hlc` wins (causal ordering).
3. Tie → both returned with `contradicted: true` on each; caller decides.

**Contradiction fact (v0.5):** When a contradiction is detected on write, the node
MUST assert a system-generated contradiction record:

```
POST /v1/facts  (system-generated, source="system:stigmem")
{
  "entity":   "stigmem:conflict:<uuid>",
  "relation": "stigmem:conflict:between",
  "value":    { "type": "text", "v": "<fact-id-a> <fact-id-b>" },
  "source":   "system:stigmem",
  "confidence": 1.0,
  "scope":    <same scope as the conflicting facts>
}
```

A second fact records status:
```
(entity="stigmem:conflict:<uuid>", relation="stigmem:conflict:status",
 value={type:"string", v:"unresolved"}, ...)
```

**Conflict entities** are queryable at `GET /v1/conflicts` (§5.9).

**Resolution:** A human or agent resolves via `POST /v1/conflicts/:id/resolve` (§5.10).
The resolution is itself a new fact with provenance; the conflict status is updated to
`"resolved"`.

### 3.4 Scope Enforcement

Scope is enforced at read and write time. Cross-scope queries are additive.

**Federation enforcement:** Nodes MUST reject outbound replication of facts whose
scope is not permitted by the active PeerDeclaration. Nodes MUST reject inbound
facts whose scope exceeds what the peer is authorized to write. See §6.4.

### 3.5 Identity and Auth (v0.5 extended)

**Status:** Phase 2 API-key model implemented. v0.5 extends with per-scope key
restrictions and peer-token auth for federation.

#### Identity shape

```
Identity {
  entity_uri:     URI
  credential:     string          // API key (SHA-256 stored server-side)
  node_url:       string
  allowed_scopes: FactScope[]     // v0.5: restricts which scopes this key can read/write
}
```

**Per-scope key restrictions (v0.5):** `api_keys` MUST store `allowed_scopes`. Default
is `["local","team","company","public"]` (all scopes) for backward compatibility.
Additive model: if `allowed_scopes` is empty, the key has no access. Operators SHOULD
restrict service-to-service keys to the minimum required scope.

#### Phase 2 API-key model (unchanged)

Credentials are presented as `Authorization: Bearer <raw-key>`. The node stores only
the SHA-256 hex digest.

**Auth mode flag:** `/.well-known/stigmem` exposes `"auth": "none" | "required"`.

#### Federation peer tokens (v0.5)

Federated replication uses short-lived **peer tokens** distinct from API keys:

```
PeerToken {
  iss:      URI          // issuing node_id
  sub:      URI          // target node_id
  iat:      epoch_ms
  exp:      epoch_ms     // MUST be ≤ iat + 3600000 (1 hour)
  nonce:    UUID         // replay protection
  scopes:   FactScope[]  // permitted scopes for this token
}
```

Tokens are Ed25519-signed JWTs. The signing key is the node's federation keypair
(separate from API keys; published at `/.well-known/stigmem` as `federation_pubkey`).

Receiving nodes MUST verify:
1. Signature against `iss` node's `federation_pubkey` (fetched at peer registration, cached).
2. `sub` matches the receiving node's own `node_id`.
3. `exp` has not passed.
4. `nonce` has not been seen within the node's nonce window (default: 5 minutes).

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

## 5. Wire Format

### 5.1 Assert a fact

```
POST /v1/facts
{ "entity": "user:alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "agent:assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", "hlc": "...", ...fact... }
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
    "version":            "0.5",
    "node_id":            URI,
    "node_url":           string,
    "auth":               "none" | "required",
    "federation":         "disabled" | "enabled",
    "federation_pubkey":  string,   // v0.5: base64url Ed25519 public key; omit if federation disabled
    "federation_version": string,   // v0.5: semver range this node speaks, e.g. "0.5"
    "federation_endpoints": {       // v0.5: advertised federation routes
      "peers":    string,           // e.g. "/v1/federation/peers"
      "facts":    string,           // e.g. "/v1/federation/facts"
      "push":     string | null     // null if push not supported
    },
    "namespaces":         ["memory:", "intent:", ...],
    "spec":               URI
  }
```

Nodes with `federation: "enabled"` MUST populate `federation_pubkey`,
`federation_version`, and `federation_endpoints`.

### 5.4 Retract a fact

To retract a fact, assert a new fact for the same `(entity, relation, scope)` with `confidence=0.0`.
The original fact is never deleted; the retraction is a new immutable entry.

```
POST /v1/facts
{ "entity": "user:alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "agent:assistant", "confidence": 0.0, "scope": "company" }
→ 201 { ..., "confidence": 0.0 }
```

### 5.5 Get a single fact

```
GET /v1/facts/:id
→ 200 { ...fact... }
→ 404 if not found
```

### 5.6 Register a peer — v0.5

```
POST /v1/federation/peers
Authorization: Bearer <api-key with federate permission>
{
  "node_url":       "https://node-b.example.com",
  "node_id":        "stigmem://node-b.example.com",
  "federation_pubkey": "<base64url Ed25519 pubkey>",
  "allowed_scopes": ["public"],
  "declaration_sig": "<base64url Ed25519 signature over canonical JSON of above fields + signed_at>",
  "signed_at":      "2026-05-02T00:00:00Z"
}
→ 201 {
    "peer_id":  "<uuid>",
    "status":   "pending_verification",
    "verified_at": null
  }
```

**Verification flow:**
1. Receiving node fetches `{node_url}/.well-known/stigmem` to retrieve the peer's
   `federation_pubkey`.
2. Node verifies `declaration_sig` over the canonical JSON payload.
3. If valid, peer status transitions to `"active"`. If `federation_pubkey` in the
   declaration does not match the one at `/.well-known/stigmem`, status becomes
   `"rejected"`.
4. Mutual federation requires both sides to register each other. A node MAY auto-register
   a reciprocal peer declaration; it MUST NOT begin replicating until both sides are `"active"`.

### 5.7 List peers — v0.5

```
GET /v1/federation/peers
→ 200 { "peers": [{ "peer_id": "...", "node_id": "...", "node_url": "...",
                     "status": "active" | "pending_verification" | "rejected" | "revoked",
                     "allowed_scopes": [...], "established_at": "..." }] }
```

### 5.8 Pull replication — v0.5

```
GET /v1/federation/facts?scope=public&cursor=<cursor>&limit=100
Authorization: Bearer <peer-token>
→ 200 {
    "facts":      [...],          // facts since cursor; max limit=500
    "cursor":     "<opaque>",     // new cursor; persist this for next call
    "has_more":   true | false
  }
```

**Cursor semantics:** An opaque string encoding the HLC of the last fact returned.
The cursor is stable: re-requesting the same cursor returns the same facts (idempotent).
A cursor of `null` requests from the beginning.

**Scope filtering:** The peer token's `scopes` claim restricts which scopes can be
returned. Nodes MUST NOT return facts outside the intersection of `allowed_scopes`
in the PeerDeclaration and the token's `scopes` claim.

**Idempotency:** Nodes MUST deduplicate by fact `id`. Re-ingesting a fact that already
exists locally is a silent no-op; the node MUST NOT create a duplicate or update
the existing record.

### 5.9 List conflicts — v0.5

```
GET /v1/conflicts?status=unresolved&cursor=<cursor>&limit=50
→ 200 {
    "conflicts": [{
      "conflict_id":  "stigmem:conflict:<uuid>",
      "fact_a":       { ...fact... },
      "fact_b":       { ...fact... },
      "status":       "unresolved" | "resolved",
      "resolved_by":  "<fact-id>" | null,
      "detected_at":  "ISO8601"
    }],
    "cursor": "...",
    "has_more": false
  }
```

### 5.10 Resolve a conflict — v0.5

```
POST /v1/conflicts/:conflict_id/resolve
Authorization: Bearer <api-key>
{
  "winning_fact_id": "<fact-id>",     // one of the two conflicting facts, OR null
  "resolution_note": "string",        // human-readable rationale; stored as fact
  "new_value": { FactValue }          // optional: assert a fresh reconciliation value
}
→ 200 {
    "resolution_fact_id": "<uuid>",   // the new fact that captures the resolution
    "conflict_status":    "resolved"
  }
```

**Resolution semantics:** The node asserts:
1. A new fact for `(entity, relation, scope)` with the winning or new value and `confidence=1.0`.
2. A `stigmem:resolves` meta-fact:
   ```
   (entity=<resolution-fact-id>, relation="stigmem:resolves",
    value={type:"ref", v:"<conflict_id>"}, source=<caller's entity_uri>, ...)
   ```
3. Updates the conflict's `stigmem:conflict:status` to `"resolved"`.

Both original conflicting facts remain immutable in the store.

### 5.11 Push replication (optional) — v0.5

Nodes that advertise a non-null `federation_endpoints.push` MUST accept:

```
POST /v1/federation/facts/push
Authorization: Bearer <peer-token>
{ "facts": [...],   // array of FactObject as they would appear in GET /v1/facts responses
  "sender_hlc": "<hlc>" }
→ 202 { "accepted": <int>, "rejected": <int>, "errors": [...] }
```

Push is opt-in. Nodes that do not support push SHOULD return 405. Implementations
SHOULD prefer pull; push is provided for low-latency delivery behind a feature flag
(`STIGMEM_FEDERATION_PUSH_ENABLED`, default `false`).

---

## 6. Federation — v0.5 Specification

> **v0.5 status:** §6 promoted from RFC stub to concrete spec. The design below is
> stable enough to implement. Remaining open questions are in §8.

### 6.1 Peer Declaration

Two nodes federate when operators on both sides exchange a signed **PeerDeclaration**.

```
PeerDeclaration {
  node_url:          string       // reachable HTTPS base URL of the declaring node
  node_id:           URI          // stable identity URI for the node
  federation_pubkey: string       // base64url Ed25519 public key for token verification
  allowed_scopes:    FactScope[]  // which scopes this node is willing to share with the peer
  rate_limit:        RateLimit?   // optional: max facts/second this peer may pull
  signed_at:         ISO 8601 UTC
  declaration_sig:   string       // Ed25519 sig over canonical JSON of the above fields
}

RateLimit {
  facts_per_second: integer
  burst:            integer
}
```

**Canonical JSON** for signing: fields in lexicographic key order, no whitespace, UTF-8.

**Key lifecycle:**
- Nodes SHOULD rotate their federation keypair no more often than weekly to avoid
  verification races during rotation.
- During rotation, nodes MUST keep the old key active for 24 hours and publish the
  new key at `/.well-known/stigmem`. Peers that fail token verification SHOULD
  re-fetch the well-known document once before treating it as an attack.

### 6.2 Capability Negotiation

After peer registration, peers MAY exchange capability advertisements to optimize
replication:

```
CapabilityAd {
  relations_understood:    string[]
  decay_policies:          { relation: string, policy: string }[]
  contradiction_overrides: { relation: string, policy: "latest" | "highest_confidence" | "caller_decides" }[]
  federation_mode:         "push" | "pull" | "both"
  push_interval_s:         integer?   // if mode includes push
  pull_interval_s:         integer?   // recommended pull cadence; advisory only
}
```

Capability exchange: `GET /v1/federation/peers/:peer_id/capabilities` returns the
remote node's capability advertisement (fetched lazily on first pull). A node MAY
cache this for up to 1 hour.

**Minimum viable implementation:** Nodes are not required to implement capability
negotiation in Phase 3. A node that does not advertise capabilities MUST be treated
as supporting `federation_mode: "pull"` and no contradiction overrides.

### 6.3 Replication Protocol

#### Pull cadence

The **subscriber** (the node that wants facts) polls the **publisher**:

```
loop every pull_interval_s (default: 30s):
  cursor = load_cursor(peer_id) or null
  resp   = GET {peer.node_url}/v1/federation/facts?scope=public&cursor={cursor}
           Authorization: Bearer {fresh_peer_token}
  for fact in resp.facts:
    ingest_fact(fact)
  save_cursor(peer_id, resp.cursor)
```

**Pull interval:** Default 30 seconds. Configurable via `STIGMEM_FEDERATION_PULL_INTERVAL_S`.
The publisher's capability advertisement MAY suggest a different interval; the
subscriber treats this as advisory.

**Back-pressure:** If the publisher returns 429, the subscriber MUST back off
exponentially with jitter. Max backoff: 5 minutes.

#### Idempotent ingestion

```python
def ingest_fact(fact):
    if facts.exists(id=fact.id):
        return  # no-op; do not update, do not create duplicate
    assert_fact(fact)
    assert_received_from_meta(fact.id, sender_node_id)
    detect_contradiction(fact)  # see §3.3
```

The `stigmem:received_from` meta-fact MUST be written atomically with the fact.

#### HLC synchronization

When ingesting a federated fact, the receiving node MUST advance its own HLC:
```
local_hlc = max(local_hlc.wall_ms, fact.hlc.wall_ms)
```

### 6.4 Permission Enforcement

**Scope boundary rules (strict):**

| Fact scope  | Federatable?                                                                |
|-------------|-----------------------------------------------------------------------------|
| `local`     | Never. Nodes MUST NOT expose `local` facts on federation endpoints.          |
| `team`      | Never, unless operator sets `STIGMEM_FEDERATION_ALLOW_TEAM=true` (audit-logged). |
| `company`   | Only if the active PeerDeclaration's `allowed_scopes` includes `"company"`. |
| `public`    | Yes, to any active peer.                                                     |

**Inbound enforcement:**
- Nodes MUST reject any fact whose scope is not permitted by the peer's PeerDeclaration.
- Nodes MUST reject any fact whose `source` does not match the peer's `node_id` or a
  sub-entity explicitly delegated by the peer (i.e., a fact from `peer-b` should not claim
  `source="user:alice@peer-c"` unless `peer-b`'s declaration covers that entity space).

**Audit log:** All rejected inbound facts MUST be recorded with: peer_id, fact_id,
rejection reason, timestamp. Accessible at `GET /v1/federation/audit?peer_id=<id>`.

### 6.5 Conflict-First-Class Semantics

When a federated fact conflicts with a locally-held fact (same entity/relation/scope,
different non-zero-confidence values), the receiving node MUST:

1. Store both facts.
2. Assert the system-generated `stigmem:conflict:between` fact (§3.3).
3. Return both facts when queried, with `contradicted: true`.
4. NOT silently prefer either fact without explicit resolution.

**Cross-node conflicts are expected.** The protocol treats them as information, not errors.
Nodes SHOULD surface unresolved conflicts in monitoring/alerting.

**Contradiction entity namespace:** All conflict entities use `stigmem:conflict:<uuid>`.
These entities MUST NOT be federated (they are local accounting artifacts).

### 6.6 Security Invariants

The following invariants MUST hold at all times:

1. **Scope non-escalation.** An inbound fact may not raise its own scope. A fact
   arriving with `scope="public"` on a wire that the PeerDeclaration restricts to
   `["public"]` is valid. A fact arriving with `scope="company"` on a `["public"]`-only
   peer MUST be rejected.

2. **Provenance non-forgery.** A peer MUST NOT assert facts with `source` values it
   does not own. The receiving node validates `source` against the sender's declared
   `node_id` and any explicitly delegated entity namespaces.

3. **Replay resistance.** Peer tokens carry a `nonce` and `exp`. The receiving node
   MUST maintain a nonce cache for the duration of the token's validity window (max 1
   hour). Tokens with already-seen nonces MUST be rejected with 401.

4. **Partition safety.** During a network partition, each node MUST continue accepting
   local reads and writes without degradation. Replication resumes from the last
   persisted cursor when connectivity is restored.

5. **No silent data loss.** A node MUST NOT discard facts during reconciliation after
   a partition. All divergent writes MUST be ingested; contradictions are surfaced to
   callers.

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
| Ed25519 for peer tokens | Fast, compact, widely supported; avoids RSA key size debates |
| HLC over pure vector clocks | HLC is O(1) state per node; vector clocks are O(N) and impractical beyond small clusters |
| Pull-based replication default | Simpler operational model; push is opt-in for latency-sensitive deployments |
| Contradiction as first-class fact | Forces explicit reconciliation; prevents silent data corruption across nodes |
| Peer tokens separate from API keys | Federation auth is machine-to-machine with short TTL; API keys are long-lived operator credentials |
| Nonce window 5 minutes | Balances replay protection with clock skew tolerance; tunable via env var |
| Conflict entities not federated | Conflicts are local accounting; federating them would cause infinite loops |
| Per-scope key restrictions additive | Default-all with opt-out is more backward-compatible; default-none would break existing deployments |

---

## 8. Open Questions (v0.5)

1. **Entity URI scheme.** `user:alice` is informal. Should v0.5 require
   `stigmem://company.acme/user/alice`? The collision risk becomes real once federation
   ships. **Leaning yes for v0.6** — Phase 3 implementation should warn on informal URIs
   but not break on them.

2. **Intent envelope scope.** Phase 2 implemented fact model only. Proposing to defer
   intent envelope to Phase 4 adapters.

3. **Multi-node federation (3+ nodes).** v0.5 specifies two-node federation. Gossip
   protocols for N>2 are deferred to Phase 5. Phase 3 MUST NOT design in a way that
   makes N-node extension impossible.

4. **Capability negotiation requirement.** Capability advertisement is optional in
   Phase 3. Should it become required in v0.6? Leaning yes once we have two
   implementations to compare.

5. **Conflict resolution policy plugins.** Should operators be able to register custom
   resolution functions? Deferred until a concrete use case emerges from Phase 3 testing.

6. **Audit log retention.** The federation audit log has no specified retention policy.
   Nodes SHOULD retain at least 7 days. Formal policy is a Phase 7 concern.

7. **`company`-scoped federation.** The spec allows `company` facts to cross federation
   with explicit opt-in. Is this too permissive? Phase 3 test matrix covers scope-leak
   attempts; findings will inform v0.6.

---

## 9. Namespace Registry

### 9.1 Reserved prefixes (maintained by spec)

| Prefix | Governed by | Purpose |
|---|---|---|
| `stigmem:` | Spec maintainers | Core protocol relations: `stigmem:ttl`, `stigmem:received_from`, `stigmem:member`, `stigmem:conflict:between`, `stigmem:conflict:status`, `stigmem:resolves` |
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

## 10. Schema and Migration (v0.5)

Production nodes SHOULD use a migration-versioned schema. The reference implementation
uses numbered SQL migration files applied at startup.

### Existing tables (v0.4, unchanged)

```sql
facts (
  id          TEXT PRIMARY KEY,
  entity      TEXT NOT NULL,
  relation    TEXT NOT NULL,
  value_type  TEXT NOT NULL,
  value_v     TEXT NOT NULL,
  source      TEXT NOT NULL,
  timestamp   TEXT NOT NULL,
  valid_until TEXT,
  confidence  REAL NOT NULL,
  scope       TEXT NOT NULL
)
```

**Required indexes:** `(entity, relation)`, `(entity, relation, scope)`, `scope`, `timestamp`.

### New columns — migration 002 (v0.5)

```sql
ALTER TABLE facts ADD COLUMN hlc           TEXT;          -- HLC timestamp; NULL for pre-v0.5 facts
ALTER TABLE facts ADD COLUMN received_from TEXT;          -- node_id if federated; NULL if local
```

### New tables — migration 002 (v0.5)

```sql
peers (
  id              TEXT PRIMARY KEY,       -- uuid
  node_id         TEXT NOT NULL UNIQUE,   -- peer's stable URI
  node_url        TEXT NOT NULL,
  federation_pubkey TEXT NOT NULL,        -- base64url Ed25519
  allowed_scopes  TEXT NOT NULL,          -- JSON array
  status          TEXT NOT NULL,          -- pending_verification | active | rejected | revoked
  established_at  TEXT,                   -- ISO 8601; set when status→active
  declaration_sig TEXT NOT NULL,
  signed_at       TEXT NOT NULL
)

replication_cursors (
  peer_id         TEXT NOT NULL REFERENCES peers(id),
  direction       TEXT NOT NULL,          -- "inbound" | "outbound"
  cursor          TEXT,                   -- opaque HLC string; NULL = start from beginning
  updated_at      TEXT NOT NULL,
  PRIMARY KEY (peer_id, direction)
)

conflicts (
  id              TEXT PRIMARY KEY,       -- "stigmem:conflict:<uuid>"
  fact_a_id       TEXT NOT NULL REFERENCES facts(id),
  fact_b_id       TEXT NOT NULL REFERENCES facts(id),
  status          TEXT NOT NULL DEFAULT 'unresolved',
  resolution_fact_id TEXT,
  detected_at     TEXT NOT NULL
)

federation_audit (
  id              TEXT PRIMARY KEY,
  peer_id         TEXT NOT NULL,
  event_type      TEXT NOT NULL,          -- "rejected_fact" | "rejected_token" | "scope_violation" | "replay_attempt"
  detail          TEXT,                   -- JSON blob with fact_id, reason, etc.
  ts              TEXT NOT NULL
)

nonce_cache (
  nonce           TEXT PRIMARY KEY,
  peer_id         TEXT NOT NULL,
  expires_at      TEXT NOT NULL           -- prune when expires_at < now
)
```

**Indexes to add:**
- `conflicts(status)` for unresolved-conflict queries
- `federation_audit(peer_id, ts)` for audit queries
- `nonce_cache(expires_at)` for TTL pruning
- `facts(hlc)` for cursor-based replication queries
- `facts(received_from)` for provenance queries

---

## 11. Failure Mode Acceptance Scenarios — v0.5

These scenarios are **acceptance gates** for Phase 3. All four MUST pass before
the phase is considered complete.

### 11.1 Split-Brain

**Setup:** Two nodes A and B are federated with `scope=public`. Both are initially
in sync (same public facts).

**Scenario:**
1. Cut network connectivity between A and B (simulated partition).
2. Write fact `F_a` to node A: `(entity="test:entity", relation="test:value", value="from-a", scope="public")`.
3. Write fact `F_b` to node B: `(entity="test:entity", relation="test:value", value="from-b", scope="public")`.
4. Maintain partition for >5 minutes. Both nodes continue accepting reads and writes.
5. Restore connectivity.
6. Allow replication to complete (pull cycle fires on both sides).

**Expected outcomes:**
- Both nodes store both `F_a` and `F_b`.
- A `stigmem:conflict:between` fact exists on both nodes (or at minimum on the node
  that ingested the second fact — the local node MUST detect the conflict on ingestion).
- `GET /v1/conflicts?status=unresolved` returns the conflict on both nodes.
- `GET /v1/facts?entity=test:entity&relation=test:value&include_contradicted=true` returns
  both facts with `contradicted: true`.
- No fact is silently discarded.

### 11.2 Malicious Peer

**Setup:** Node A and Node B are federated. A third process ("attacker") obtains
a valid peer token for the `node_b` → `node_a` direction (simulating a compromised
peer or MITM).

**Scenario:**
1. Attacker attempts to push a fact with `scope="company"` to node A's
   `/v1/federation/facts/push`, where the PeerDeclaration only allows `["public"]`.
2. Attacker attempts to push a fact with `source="user:alice"` (an entity not
   belonging to node B's declared namespace).
3. Attacker replays a previously-seen valid peer token (captured from an earlier
   legitimate exchange) after the nonce window expires. Then replays within the window.

**Expected outcomes:**
1. HTTP 403. Fact rejected. `federation_audit` record written: `event_type="scope_violation"`.
2. HTTP 403. Fact rejected. `federation_audit` record written: `event_type="rejected_fact"`, reason=`source_not_owned`.
3. First replay (outside nonce window): token accepted (nonce evicted). Second replay (inside window): HTTP 401. `federation_audit` record: `event_type="replay_attempt"`.
   - Node A's fact store is not corrupted by either replay attempt.

### 11.3 Partial Failure (Peer Down Mid-Replication)

**Setup:** Node A (subscriber) is pulling from Node B (publisher). Node B has 1000
public facts. A has pulled 500 so far; cursor is stored.

**Scenario:**
1. Node B crashes after returning facts 501–600 but before node A persists the cursor
   for that batch. (Simulate: kill node B's process; reset A's cursor to the 500 mark.)
2. Node A attempts its next pull; node B is unreachable.
3. Node A continues serving read and write requests normally.
4. Node B restarts.
5. Node A's next pull cycle fires.

**Expected outcomes:**
- During step 2: Node A returns 503 or times out on the pull attempt; no crash; local
  reads/writes unaffected.
- After step 5: Node A resumes from cursor 500 (not 0, not 600). Facts 501–1000 are
  ingested. No duplicates created (idempotency check passes on facts 501–600 that may
  have been partially ingested).
- Final state: Node A has all 1000 facts.

### 11.4 Replay Attack

**Setup:** Node A and B are federated. A valid peer token `T` is intercepted.

**Scenario:**
1. Token `T` is used legitimately for a pull request by node B. Succeeds.
2. Token `T` is immediately replayed by an attacker. (Within nonce window.)
3. A new token `T2` is generated with the same nonce as `T` but a fresh `iat`/`exp`.
4. Token `T3` is generated with a past `exp` (already expired).

**Expected outcomes:**
1. First use: HTTP 200, facts returned.
2. Replay of `T`: HTTP 401, `error: "nonce_already_seen"`. Audit log entry.
3. `T2` (duplicate nonce): HTTP 401. The nonce cache matches on nonce value, not token identity.
4. `T3` (expired): HTTP 401, `error: "token_expired"`.

---

## 12. Reserved for Phase 4+

The following are explicitly out of scope for v0.5 / Phase 3:

- OpenClaw / Paperclip / MCP adapters
- Hosted public Stigmem node
- Multi-tenant RBAC / OIDC
- N > 2 node gossip
- Binary wire encoding
- Entity URI scheme enforcement (warning only in Phase 3)

---

*v0.5-draft — §6 and §11 are new and open for team review. Remaining RFC questions in §8.*
