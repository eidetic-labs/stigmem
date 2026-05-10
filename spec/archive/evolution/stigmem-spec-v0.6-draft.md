> **⚠️ Archived — evolutionary snapshot, not the canonical spec.**
>
> This file was a pre-v0.9.0a1 development checkpoint of the stigmem protocol specification. Per [ADR-001](../../../docs/adr/001-versioning.md), the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09); the version *marker* on this snapshot labeled an internal development step, not a tagged release.
>
> The current canonical spec is at [`spec/stigmem-spec-v0.9.0a1.md`](../../stigmem-spec-v0.9.0a1.md). Content from this snapshot was reviewed section-by-section against actual implementation in `node/` and migrated forward into the canonical spec where applicable; deferred sections moved to `experimental/<feature>/spec.md` per [ADR-002](../../../docs/adr/002-v1-scope.md) + [ADR-011](../../../docs/adr/011-cross-cutting-extraction.md).
>
> This snapshot is preserved as historical reference; it is not normative.

---

# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v0.6 — Draft

**Status:** Working draft — CTO reviewed. §1–5, §7–10 promoted from v0.5 (stable). §6 stable. §11 stable. §12 Adapter ABI promoted from Phase 4 reserved to normative. §2.5 Entity URI scheme new (normative). §6.2 capability negotiation now required. Phase 5 additions: §2.6 entity naming rules (normative, implemented), §5.12 lint-semantics (normative, implemented).
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v0.6+phase5: §2.6 entity naming rules normative (strict normalizer shipped); §5.12 lint-semantics new (lint_scope MCP tool + backend route); §5.10 resolution semantics corrected — resolution facts now namespace to `stigmem:resolution:<conflict-id>` to prevent cascade contradiction wave; query_facts `include_contradicted=false` default now enforced server-side.
- v0.6 (CTO review pass): §12.5 context injection schema corrected to match `_facts_to_summary` reference impl (namespace grouping, conditional confidence annotation, em-dash header); §12.4.1 informal URI caveat added with v0.7 migration note; §12.3.2 step 1 documents preference-relation filter; §12.2 `STIGMEM_SOURCE_ENTITY` default clarified as adapter-specific.
- v0.6: §2.5 Entity URI scheme formal scheme (`stigmem://`) now normative; informal URIs deprecated with warning (resolves §8.1); §6.2 capability negotiation promoted from optional to required (resolves §8.4); §12 Adapter ABI promoted from Phase 4 reserved to concrete normative spec based on three shipped adapters (MCP, Paperclip, OpenClaw); §13 Reserved for Phase 5+.
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
| `entity`      | URI (see §2.5)                    | What this fact is about. Formal: `stigmem://company.example/user/alice`. Informal (deprecated): `user:alice`. |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI (see §2.5)                    | Who asserted the fact. Examples: `stigmem://company.example/agent/assistant`, `stigmem://company.example/user/alice`. |
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
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"stigmem://company.example/company/a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"stigmem://company.example/company/b"})
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

### 2.5 Entity URI Scheme — v0.6 Normative

**v0.5 open question §8.1 resolved.** The entity URI scheme is now normative.

#### Formal URI scheme

```
stigmem://{authority}/{type}/{id}
```

| Component   | Description | Examples |
|-------------|-------------|---------|
| `authority` | Hostname of the Stigmem node that owns this entity namespace | `company.example`, `node.example.com` |
| `type`      | Entity type slug (lowercase, no spaces) | `user`, `agent`, `project`, `issue`, `decision`, `team` |
| `id`        | Opaque stable identifier for the entity | `alice`, `cto`, `acme-roadmap`, `EG-42` |

**Examples:**
- `stigmem://company.example/user/alice`
- `stigmem://company.example/agent/cto`
- `stigmem://company.example/issue/EG-42`
- `stigmem://node.acme/decision/use-sqlite`

#### Deprecation of informal URIs

Informal URIs (colon-separated shorthand such as `user:alice`, `agent:cto`,
`project:acme-roadmap`) are **deprecated as of v0.6**.

**Node behavior:**
- Nodes MUST accept informal URIs without rejecting them (backward compatibility).
- Nodes MUST emit a deprecation warning to stderr when storing a fact whose `entity`
  or `source` field does not match the `stigmem://` scheme.
- The deprecation warning MUST include the offending URI and SHOULD include a migration
  hint pointing to the formal scheme.
- Nodes MUST NOT auto-rewrite informal URIs to formal URIs on ingest (that would
  silently alter provenance).

**Adapter behavior:**
- Adapters SHOULD use formal URIs for all new fact assertions as of v0.6.
- Adapters MUST NOT emit informal URIs in new code targeting v0.6 or later.
- Existing stored facts with informal URIs remain valid through at least v0.8.

**Collision rationale:** Informal URIs are inherently ambiguous once federation
is active. `user:alice` on node A and `user:alice` on node B may refer to different
people. The formal scheme binds the authority to the URI, preventing silent identity
collisions across federated nodes.

---

### 2.6 Entity Naming Rules — Phase 5 (v0.7 Normative)

**Root cause of entity fragmentation (Bug 1):** Two agents writing
`project/eg-18`, `project/EG-18`, and `phase4` create three silent entity
fragments that never merge. The node has no basis to treat them as the same entity.
The v0.7 normalization layer closes this gap.

#### Canonical form

The **canonical form** of an entity URI is the unique key used for storage and
lookup. The canonicalization algorithm is:

1. Trim surrounding whitespace.
2. If the URI matches `stigmem://{authority}/{type}/{id}` (formal scheme):
   - Lowercase `authority`, `type`, and `id`.
   - Collapse any internal whitespace in `id` to a single hyphen.
   - Reject if any component is empty after normalization.
   - Return `stigmem://{authority}/{type}/{id}`.
3. Otherwise (informal URI):
   - Lowercase the entire string.
   - Collapse whitespace to hyphens.
   - Return as-is (do NOT convert informal to formal; that is a migration concern).

The algorithm is **deterministic and idempotent**: `normalize(normalize(x)) = normalize(x)`.

#### Node behavior (v0.7)

- Nodes MUST normalize the `entity` and `source` fields on every `assert_fact`
  write using the algorithm above before storing and before contradiction detection.
- Nodes MUST normalize the `entity` and `source` query parameters on every
  `query_facts` call before executing the lookup.
- If normalization fails (empty component), the node MUST return `400 Bad Request`
  with error code `invalid_entity_uri`.
- Nodes MUST NOT apply normalization to `relation` — relation namespacing is governed
  by the convention in §9 and the migration guide.

#### What normalization does NOT do

- Does **not** resolve aliases (`user:alice` ≠ `stigmem://company.example/user/alice`).
  Alias resolution is a Phase 6 fuzzy-resolver concern (§8 open question).
- Does **not** rewrite stored facts. Normalization is applied on write and query only.
- Does **not** merge distinct entities that happen to look similar. Two formally
  distinct URIs are always two entities.

#### Reference implementation

`stigmem/node/src/stigmem_node/entity_normalizer.py` — `normalize_entity_uri()` and
`is_informal()`. The v0.6 node already applies this on every write and query.

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
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", "hlc": "...", ...fact... }
```

### 5.2 Query facts

```
GET /v1/facts?entity=stigmem://company.example/user/alice&relation=memory:role
→ 200 { "facts": [...], "total": 1, "cursor": null }
```

Query params: `entity`, `relation`, `source`, `scope`, `min_confidence`,
`after`, `include_contradicted`, `include_expired`, `cursor`, `limit`.

### 5.3 Node metadata

```
GET /.well-known/stigmem
→ 200 {
    "version":            "0.6",
    "node_id":            URI,
    "node_url":           string,
    "auth":               "none" | "required",
    "federation":         "disabled" | "enabled",
    "federation_pubkey":  string,   // v0.5: base64url Ed25519 public key; omit if federation disabled
    "federation_version": string,   // v0.5: semver range this node speaks, e.g. "0.6"
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
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 0.0, "scope": "company" }
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
1. A new **resolution fact** written under the namespaced entity
   `stigmem:resolution:<conflict_id>` (not the conflicting facts' entity) with the
   winning or new value and `confidence=1.0`. Using a dedicated entity prevents
   the resolution fact from sharing the `(entity, relation, scope)` triple with the
   conflicting facts, which would otherwise trigger a cascading contradiction wave
   when the fact is federated to peer nodes (§6.5).
2. A `stigmem:resolves` meta-fact:
   ```
   (entity=<resolution-fact-id>, relation="stigmem:resolves",
    value={type:"ref", v:"<conflict_id>"}, source="system:stigmem", ...)
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

### 5.12 Lint a scope — Phase 5

Lint is a first-class operation that performs health-check sweeps on a scope.
It is the spec vocabulary for the planned decay engine and sweep work.

```
POST /v1/lint
Authorization: Bearer <api-key>
{
  "scope":             "local" | "team" | "company" | "public",
  "checks":            ["contradiction","stale","orphan","broken_ref"],  // optional; omit = all
  "entity":            string,   // optional: restrict to one entity URI
  "relation":          string,   // optional: restrict to one relation
  "stale_lookahead_s": int       // optional: also flag facts expiring within N seconds
}
→ 200 {
    "findings": [
      {
        "check":    "contradiction" | "stale" | "orphan" | "broken_ref",
        "severity": "error" | "warning" | "info",
        "entity":   string,
        "relation": string | null,
        "fact_ids": string[],
        "detail":   string
      }, ...
    ],
    "checked_at":  ISO 8601,
    "scope":       string,
    "checks_run":  string[],
    "fact_count":  int
  }
```

**Lint checks:**

| Check | Severity | Description |
|-------|----------|-------------|
| `contradiction` | `error` | Facts in unresolved conflicts in the `conflicts` table |
| `stale` | `warning` (expired) / `info` (expiring soon) | Facts with `valid_until ≤ now`; also flags within `stale_lookahead_s` |
| `orphan` | `info` | Source URIs that never appear as `entity` in the given scope |
| `broken_ref` | `warning` | Facts with `value_type="ref"` where `value_v` is not a known fact ID |

**Scope:** Lint operates within a single required scope (`local`, `team`, `company`, `public`).

**Read-only:** Lint MUST NOT modify any stored data. It is a health-check read.
Cleanup actions (deleting orphans, removing stale facts) are operator decisions,
not automatic side-effects of lint.

**Performance:** Lint is an O(n) scan of the facts table for the given scope.
Callers SHOULD rate-limit lint calls in production. Nodes MAY return `429 Too Many Requests`
if lint is called more frequently than once per minute per scope.

**MCP tool:** `lint_scope` — see §12 Adapter ABI for the MCP tool definition.

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

### 6.2 Capability Negotiation — v0.6 Required

**v0.5 open question §8.4 resolved.** Capability negotiation is now required for all
nodes that support federation, based on implementation experience from two Phase 4 adapters.

After peer registration, nodes MUST exchange capability advertisements before the first
replication pull:

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

**Exchange route:** `GET /v1/federation/peers/:peer_id/capabilities` returns the
remote node's capability advertisement. A node MUST respond to this route if it
supports federation. A node MAY cache the remote capability advertisement for up to
1 hour.

**Required behavior:**
- A node MUST advertise at minimum: `federation_mode` and `relations_understood`.
- A node that receives a capability request MUST respond within 10 seconds or the
  requesting node MAY treat it as `{ federation_mode: "pull", relations_understood: [] }`.
- Unknown fields in a received `CapabilityAd` MUST be ignored (forward compatibility).

**Why now required:** Phase 4 shipped the Paperclip and OpenClaw adapters, both of
which use distinct relation namespaces (`paperclip:`, `intent:`). Without capability
exchange, a federated peer cannot distinguish relations it understands from opaque
forwarded data — leading to silent contradiction storms on relations the peer cannot
interpret. Capability advertisement gives both sides a shared understanding of what
to replicate and how to resolve conflicts on those relations.

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
  `source="stigmem://node-c/user/alice"` unless `peer-b`'s declaration covers that entity space).

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
| Formal entity URI scheme in v0.6 | Informal `user:alice` URIs are ambiguous under federation — two peers can have different `user:alice`. Formal `stigmem://authority/type/id` binds identity to the node that owns the namespace. Deprecation-warning approach preserves backward compat while driving migration. |
| Capability negotiation required in v0.6 | Phase 4 shipped two adapters with distinct relation namespaces. Without capability exchange, federated peers silently replicate relations they cannot interpret. Required negotiation prevents contradiction storms on semantically-opaque relations. |
| Crash-forbidden adapter contract | Adapters are middleware in existing agent processes; a Stigmem node failure must not take down the agent. Crash-forbidden is an explicit ABI invariant so all adapter authors share the same degradation model. |

---

## 8. Open Questions (v0.6)

**Resolved in v0.6:**
- ~~§8.1 Entity URI scheme~~ — resolved: formal `stigmem://` scheme normative; informal deprecated with warning (§2.5).
- ~~§8.4 Capability negotiation requirement~~ — resolved: capability negotiation required for federation-enabled nodes (§6.2).

**Remaining open:**

1. **Intent envelope scope.** Phase 2 implemented fact model only. Intent envelope wired
   through Phase 4 adapters (handoff, escalation, decision facts), but the full
   `IntentEnvelope` wire route is not yet implemented. Proposing to defer full envelope
   route to Phase 5.

2. **Multi-node federation (3+ nodes).** v0.5 specifies two-node federation. Gossip
   protocols for N>2 are deferred to Phase 5. Phase 4 MUST NOT design in a way that
   makes N-node extension impossible.

3. **Conflict resolution policy plugins.** Should operators be able to register custom
   resolution functions? Deferred until a concrete use case emerges from Phase 4 testing.

4. **Audit log retention.** The federation audit log has no specified retention policy.
   Nodes SHOULD retain at least 7 heartbeats (initial test period; time-based policy is a Phase 7 concern).

5. **`company`-scoped federation.** The spec allows `company` facts to cross federation
   with explicit opt-in. Phase 4 testing should confirm whether this is too permissive.
   The Phase 3 test matrix covered scope-leak attempts; Phase 4 findings will inform v0.7.

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
| `intent:` | Registered | Intent envelope machine-readable facts; includes `intent:handoff_to`, `intent:handoff_summary`, `intent:context_ref`, `intent:continuation`, `intent:escalation`, `intent:escalate_to`, `intent:goal` |
| `roadmap:` | Registered | Project/product state facts; includes `roadmap:decision`, `roadmap:constraint`, `roadmap:status`, `roadmap:summary` |
| `preference:` | Registered | User/agent preferences |
| `paperclip:` | Registered (Phase 4) | Paperclip adapter lifecycle facts: `paperclip:checkout`, `paperclip:issue_status`, `paperclip:last_active`, `paperclip:blocked_by` |

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
2. Write fact `F_a` to node A: `(entity="stigmem://node-a/test/entity", relation="test:value", value="from-a", scope="public")`.
3. Write fact `F_b` to node B: `(entity="stigmem://node-a/test/entity", relation="test:value", value="from-b", scope="public")`.
4. Maintain partition for >5 minutes. Both nodes continue accepting reads and writes.
5. Restore connectivity.
6. Allow replication to complete (pull cycle fires on both sides).

**Expected outcomes:**
- Both nodes store both `F_a` and `F_b`.
- A `stigmem:conflict:between` fact exists on both nodes (or at minimum on the node
  that ingested the second fact — the local node MUST detect the conflict on ingestion).
- `GET /v1/conflicts?status=unresolved` returns the conflict on both nodes.
- `GET /v1/facts?entity=stigmem://node-a/test/entity&relation=test:value&include_contradicted=true` returns
  both facts with `contradicted: true`.
- No fact is silently discarded.

### 11.2 Malicious Peer

**Setup:** Node A and Node B are federated. A third process ("attacker") obtains
a valid peer token for the `node_b` → `node_a` direction (simulating a compromised
peer or MITM).

**Scenario:**
1. Attacker attempts to push a fact with `scope="company"` to node A's
   `/v1/federation/facts/push`, where the PeerDeclaration only allows `["public"]`.
2. Attacker attempts to push a fact with `source="stigmem://node-c/user/alice"` (an entity not
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

## 12. Adapter ABI — v0.6 Normative

> **v0.6 status:** Promoted from Phase 4 reserved section to normative spec, grounded
> in the three Phase 4 adapters shipped: MCP (`stigmem/adapters/mcp/`), Paperclip
> (`stigmem/adapters/paperclip/`), and OpenClaw (`stigmem/adapters/openclaw/`).

### 12.1 Adapter Archetypes

The ABI recognizes two adapter archetypes with different startup failure contracts:

**Process-mode adapters** (example: MCP `server.ts`): A standalone process whose
sole purpose is to bridge a platform protocol to Stigmem. The process is useless if
Stigmem is not configured; fast failure is correct behavior.

**Middleware adapters** (examples: Paperclip `hook.sh`, OpenClaw `adapter.py`): Code
that extends an existing agent runtime. Stigmem is optional; the agent MUST continue
operating if Stigmem is unconfigured or unreachable.

### 12.2 Required Environment Variables

All adapters MUST honor the following environment variables:

| Variable | Required by | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | All | — | Base URL of the Stigmem node, e.g. `http://localhost:8765` |
| `STIGMEM_API_KEY` | All (optional) | none | API key; required when `auth=required` |
| `STIGMEM_SOURCE_ENTITY` | Middleware | adapter-specific (e.g. `"agent:openclaw"`, `"agent:unknown"`) | Entity URI used as `source` on all write operations. Adapters SHOULD default to a descriptive identity; `"agent:unknown"` is an acceptable last-resort fallback. |

**Process-mode adapters:** MUST exit with a non-zero status code and a clear error
message to stderr if `STIGMEM_URL` is absent.

**Middleware adapters:** MUST silently skip all Stigmem operations if `STIGMEM_URL`
is absent. MUST NOT modify the agent process exit code.

### 12.3 Boot Handshake Protocol

The boot handshake runs once when the adapter initializes. It has two phases:
a node probe and (for middleware adapters) a context pull.

#### 12.3.1 Node probe

Adapters SHOULD issue `GET /.well-known/stigmem` to verify node reachability on startup.

Expected response shape:

```json
{
  "version":    "0.6",
  "node_id":    "<URI>",
  "node_url":   "<string>",
  "auth":       "none" | "required",
  "federation": "disabled" | "enabled"
}
```

Required fields: `version`, `node_id`, `node_url`, `auth`, `federation`.

If the probe fails or required fields are absent:
- **Process-mode adapters:** MUST log an error to stderr. SHOULD NOT crash — allow
  individual tool invocations to fail with a `StigmemError` rather than killing the process.
- **Middleware adapters:** MUST log a warning to stderr. MUST return an empty
  `BootContext`. MUST NOT crash or alter the agent's exit code.

#### 12.3.2 Context pull (middleware adapters only)

After a successful node probe, middleware adapters that inject context into the agent
system prompt MUST issue the following queries in order. All queries are non-fatal:
a failed or empty response on any individual query MUST NOT abort the boot sequence.

1. **User entity facts**
   ```
   GET /v1/facts?entity={user_entity}&scope=company&min_confidence=0.7
   ```
   Adapters SHOULD filter the result to relevant relation namespaces (e.g. `preference:`).
   Injecting all relations for the user entity may produce a large or noisy context;
   retaining `preference:*` is the reference behavior.

2. **Project constraints** (one query per project entity; skip if no project entities configured)
   ```
   GET /v1/facts?entity={project_entity}&relation=roadmap:constraint&scope=company&min_confidence=0.7
   ```

3. **Pending handoffs targeting this adapter**
   ```
   GET /v1/facts?relation=intent:handoff_to&scope=company&min_confidence=0.8
   ```
   Filter client-side to facts where `value.v == STIGMEM_SOURCE_ENTITY`.
   For each matching handoff entity, additionally pull:
   ```
   GET /v1/facts?entity={handoff_entity}&relation=intent:context_ref&scope=company
   ```

4. **Recent escalations**
   ```
   GET /v1/facts?relation=intent:escalation&scope=company&min_confidence=0.8&limit=10
   ```

#### 12.3.3 BootContext shape

```
BootContext {
  facts:   Fact[]   // all successfully retrieved facts; empty list if node unreachable
  summary: string   // markdown-formatted context for system prompt injection (see §12.5)
}
```

`BootContext` is always returned, even on total failure. A failed boot returns
`BootContext { facts: [], summary: "" }`.

### 12.4 Write Surfaces

Adapters MUST assert the following facts on the specified lifecycle events.

**Write invariants (apply to all assertions):**
- `confidence` MUST be 1.0 unless a per-surface override is listed below.
- All write calls MUST use fire-and-forget semantics: errors MUST be suppressed; the
  adapter MUST NOT crash the agent on write failure.
- Write failures SHOULD be logged to stderr at warning level.

#### 12.4.1 Paperclip-style lifecycle facts

For adapters that instrument platform issue/task lifecycle:

| Event | `entity` | `relation` | Value type | Value | `scope` |
|---|---|---|---|---|---|
| Checkout (task claimed) | `issue:{task_id}` | `paperclip:checkout` | `string` | `"in_progress"` | `company` |
| Completion | `issue:{task_id}` | `paperclip:issue_status` | `string` | `"done"` | `company` |
| Blocked | `issue:{task_id}` | `paperclip:issue_status` | `string` | `"blocked"` | `company` |
| Blocked by (optional) | `issue:{task_id}` | `paperclip:blocked_by` | `ref` | `"issue:{blocking_id}"` | `company` |
| Activity ping | `issue:{task_id}` | `paperclip:last_active` | `datetime` | ISO 8601 UTC now | `local` |

**Activity ping scope:** `paperclip:last_active` MUST use `scope="local"`. Activity
pings are heartbeat signals for intra-node observability; they MUST NOT be federated.

**Entity URI format note:** The `entity` column above uses informal URI shorthand
(`issue:{task_id}`). Per §2.5, adapters targeting v0.6+ SHOULD use formal URIs:
`stigmem://{node_authority}/issue/{task_id}`, where `{node_authority}` is the
hostname component of `STIGMEM_URL`. Adapters that do not have access to the
node authority MAY use the informal form — the node will accept it and emit a
deprecation warning to stderr. Migration to formal URIs is tracked for v0.7.

#### 12.4.2 Handoff facts

Emitted when an agent session ends or delegates to another agent. Mint a synthetic
entity `handoff:{uuid}` and assert all of the following:

| `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|
| `intent:handoff_to` | `ref` | target agent entity URI | 1.0 | `company` |
| `intent:handoff_summary` | `text` | human-readable summary (≤ 4 KB) | 1.0 | `company` |
| `intent:context_ref` | `ref` | fact ID URI for each referenced context fact (one assertion per ref) | 1.0 | `company` |
| `intent:continuation` | `text` | continuation note (optional; omit if absent) | 1.0 | `company` |

`intent:handoff_to` and `intent:handoff_summary` are REQUIRED. `intent:context_ref`
MUST have at least one assertion if `fact_refs` is non-empty. `intent:continuation`
is OPTIONAL.

#### 12.4.3 Decision facts

Emitted when an agent makes a significant architectural or roadmap choice:

| `entity` | `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|---|
| `{decision_entity}` | `roadmap:decision` | `text` | decision summary (≤ 4 KB) | 1.0 | `company` |

The `{decision_entity}` SHOULD be a formal URI: `stigmem://{node_authority}/decision/{slug}`.

#### 12.4.4 Escalation facts

Emitted when an agent cannot proceed and must escalate. Mint a synthetic entity
`escalation:{uuid}` and assert:

| `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|
| `intent:escalation` | `string` | priority: `"low"` \| `"medium"` \| `"high"` \| `"critical"` | 1.0 | `company` |
| `intent:escalate_to` | `ref` | target agent or user entity URI | 1.0 | `company` |
| `intent:goal` | `text` | goal statement describing what the agent could not complete (≤ 2 KB) | 1.0 | `company` |

All three assertions are REQUIRED for a complete escalation record.

#### 12.4.5 Minimum confidence and scope requirements summary

| Fact class | Min confidence | Required scope |
|---|---|---|
| Lifecycle status (`paperclip:checkout`, `paperclip:issue_status`, `paperclip:blocked_by`) | 1.0 | `company` |
| Activity ping (`paperclip:last_active`) | 1.0 | `local` (never federated) |
| Handoff facts | 1.0 | `company` |
| Decision facts | 1.0 | `company` |
| Escalation facts | 1.0 | `company` |

Adapters MUST NOT write lifecycle or intent facts with confidence below 1.0. Low-confidence
writes on these relations would pollute conflict resolution and break downstream agents
that depend on these facts for routing.

### 12.5 Context Injection Format

Adapters that inject Stigmem facts into an agent's system prompt MUST use the
following markdown schema:

```markdown
## Stigmem context — {user_entity}

### {namespace}
- **{relation}** on `{entity}`: {value_str}[ _(confidence: {confidence:.2f})_]
```

**Field rendering rules:**
- `{user_entity}`: the primary entity passed to the boot handshake
- `{namespace}`: the relation prefix before the first `:` (e.g. `preference`, `roadmap`);
  facts with the same namespace are grouped under a shared `### {namespace}` subheading
- `{relation}`: the fact's `relation` field, verbatim
- `{entity}`: the fact's `entity` field, verbatim
- `{value_str}`: for `null` type → render `(null)`; for all other types → render `value.v` as a string
- Confidence annotation: rendered only when `confidence < 1.0`, using the format
  `_(confidence: {value:.2f})_`. Facts with `confidence == 1.0` omit the annotation.

**Ordering:** Facts SHOULD be ordered by descending `confidence`, then descending `hlc` within equal confidence.

**Empty context:** If no facts were retrieved, adapters MUST return an empty string
and MUST NOT inject the `## Stigmem context` header. Do not inject a header with
zero fact lines.

**Reference implementation** (`stigmem/adapters/openclaw/adapter.py:_facts_to_summary`):
```python
def _facts_to_summary(facts: list[Fact], user_entity: str) -> str:
    if not facts:
        return ""
    groups: dict[str, list[Fact]] = {}
    for fact in facts:
        ns = fact.relation.split(":")[0] if ":" in fact.relation else fact.relation
        groups.setdefault(ns, []).append(fact)
    lines = [f"## Stigmem context — {user_entity}\n"]
    for ns, ns_facts in groups.items():
        lines.append(f"### {ns}")
        for fact in ns_facts:
            val = getattr(fact.value, "v", "(null)") if fact.value is not None else "(null)"
            confidence_note = f" _(confidence: {fact.confidence:.2f})_" if fact.confidence < 1.0 else ""
            lines.append(f"- **{fact.relation}** on `{fact.entity}`: {val}{confidence_note}")
        lines.append("")
    return "\n".join(lines).rstrip()
```

### 12.6 Error Handling Contract

The crash-forbidden invariant: **under no circumstances MAY a Stigmem adapter crash
the host agent process due to a Stigmem node failure.** The adapter is middleware;
the agent's core functionality MUST remain unaffected if Stigmem is degraded or absent.

| Scenario | Process-mode adapter | Middleware adapter |
|---|---|---|
| `STIGMEM_URL` absent | Exit non-zero with clear error to stderr | Skip all Stigmem ops silently; exit 0 |
| Node unreachable at boot | Log error to stderr; continue (let tool calls fail individually) | Log warning to stderr; return `BootContext { facts:[], summary:"" }`; continue |
| Node unreachable on write | Log warning to stderr; no crash | Log warning to stderr; no crash |
| Node returns HTTP 4xx on write | Log error to stderr; no retry; no crash | Log error to stderr; no retry; no crash |
| Node returns HTTP 5xx on write | Log error to stderr; retry once after 2 s; suppress on second failure | Log error to stderr; retry once after 2 s; suppress on second failure |
| Boot query returns HTTP 4xx | Treat as empty result for that query | Treat as empty result for that query |
| Boot query returns HTTP 5xx | Treat as empty result; log warning | Treat as empty result; log warning |
| Node unreachable on tool invocation (MCP) | Return `isError: true` with error text in tool result; do not exit | N/A |

### 12.7 Conformance Test Vectors

A compliant adapter MUST pass all vectors defined in:

```
sdks/stigmem-py/tests/conformance_vectors.py
```

The vectors are JSON-serialisable dicts shared across the Python and TypeScript SDKs.

**Vector sets:**

| Set | IDs | What it verifies |
|---|---|---|
| `ASSERT_VECTORS` | `assert-string`, `assert-text`, `assert-ref`, `retract` | `POST /v1/facts` with each FactValue type; `confidence=0.0` retraction |
| `QUERY_VECTORS` | `query-by-entity`, `query-by-entity-relation`, `query-min-confidence`, `query-include-contradicted` | `GET /v1/facts` filtering; required response fields |
| `NODE_INFO_VECTOR` | `node-info` | `GET /.well-known/stigmem` required fields: `version`, `node_id`, `node_url`, `auth`, `federation` |

**Running conformance:**
```bash
# Python SDK (also runs adapter integration tests)
pytest sdks/stigmem-py/tests/ -v

# TypeScript SDK
cd sdks/stigmem-ts && npm test
```

**Adapter-specific gate:** Adapters that write lifecycle or intent facts (§12.4) MUST
additionally demonstrate correct assertion behavior via an integration test that
verifies:
1. The expected relations are present in the fact store after each lifecycle event.
2. Facts written with the wrong scope or below minimum confidence are rejected before
   reaching the node (validated client-side) or are caught in the node's response.

A compliant adapter is one that passes all `ASSERT_VECTORS`, `QUERY_VECTORS`,
`NODE_INFO_VECTOR`, and its adapter-specific lifecycle tests with a live Stigmem node.

---

## 13. Reserved for Phase 5+

The following are explicitly out of scope for v0.6 / Phase 4:

- Multi-tenant RBAC / OIDC
- N > 2 node gossip (multi-node federation)
- Binary wire encoding
- Full `IntentEnvelope` wire route (§4 remains spec-only; Phase 5 target)
- Entity URI migration tooling (auto-rewrite from informal to formal URIs)
- Hosted public Stigmem node

---

*v0.6-draft — §2.5 (Entity URI scheme), §6.2 (capability negotiation), and §12 (Adapter ABI) are the primary new sections. §13 replaces the old §12 Phase 4 reserved block. Open for CTO review before promotion to stable.*
