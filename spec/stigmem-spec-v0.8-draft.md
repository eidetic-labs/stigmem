# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v0.8 — Draft

**Status:** Working draft — Phase 6. §1–14 promoted to stable (normative). §15 Decay Semantics new (draft). §16 Synthesis new (draft). §6 extended with N-node backpressure patterns and scope-propagation invariants. §8 open questions updated.
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v0.8 (Phase 6 — public beta): §15 Decay Semantics — decay sweeper, configurable TTL + confidence-decay policies, `POST /v1/decay/sweep`, `DecayPolicy` registry. §16 Synthesis — `synthesize_scope` MCP tool and `POST /v1/synthesis` route, confidence-weighted summary view. §6.7 N-node federation backpressure — cascade behavior in relay nodes, 4-node topology findings. §6.8 Scope propagation invariants — transitive scope escalation prevention, re-federation restrictions. §5.13 `synthesize_scope` wire route. §8 open questions updated: multi-node federation (§8.2) addressed; `company`-scoped federation edge case resolved (§8.5). §§1–14 promoted to stable; footnote on v0.7-draft removed. §9 `stigmem:decay:` prefix reserved. §13 updated for Phase 6 progress.
- v0.7 (Deliverable 4 — entity normalization): §2.6 Entity Naming Rules new normative section. §14 Lint Semantics new normative section. §10 migration 003. See `stigmem-spec-v0.7-draft.md` for full v0.7 changelog.
- [Prior changelog in stigmem-spec-v0.7-draft.md]

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
| `entity`      | URI (see §2.5, §2.6)              | What this fact is about. Formal: `stigmem://company.acme/user/alice`. Informal (deprecated): `user:alice`. Stored in canonical normalized form (§2.6). |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI (see §2.5, §2.6)              | Who asserted the fact. Examples: `stigmem://company.acme/agent/assistant`, `stigmem://company.acme/user/alice`. Stored in canonical normalized form (§2.6). |
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
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"stigmem://company.acme/company/a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"stigmem://company.acme/company/b"})
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
| `authority` | Hostname of the Stigmem node that owns this entity namespace | `company.acme`, `node.example.com` |
| `type`      | Entity type slug (lowercase, no spaces) | `user`, `agent`, `project`, `issue`, `decision`, `team` |
| `id`        | Opaque stable identifier for the entity | `alice`, `cto`, `acme-roadmap`, `EG-42` |

**Examples:**
- `stigmem://company.acme/user/alice`
- `stigmem://company.acme/agent/cto`
- `stigmem://company.acme/issue/EG-42`
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

**v0.7 note:** All components of the formal URI are normalized to lowercase on ingest (§2.6). `stigmem://company.acme/issue/EG-42` is stored as `stigmem://company.acme/issue/eg-42`.

### 2.6 Entity Naming Rules — v0.7 Normative

This section defines canonical entity naming rules and the **strict normalizer** contract. The goal is to prevent **silent entity fragmentation**: multiple facts about the same real-world entity using different URI representations that create disconnected entity nodes in the store.

**v0.7 scope:** The strict normalizer addresses case-based and whitespace-based fragmentation deterministically. Full alias resolution (e.g. `user:alice` ≡ `user:a.smith`) is deferred to the Phase 6 fuzzy resolver.

#### 2.6.1 The fragmentation problem

Before strict normalization, the following assertions create separate entities for the same project:

```
entity="project/eg-18"                            (informal, slash separator, lowercase)
entity="project/EG-18"                            (informal, slash separator, uppercase)
entity="stigmem://company.acme/project/eg-18"     (formal, lowercase id)
entity="stigmem://company.acme/project/EG-18"     (formal, uppercase id)
```

All four refer to the same project. Without normalization, queries for any one form miss the others entirely, and contradiction detection never fires for facts that should conflict.

#### 2.6.2 Canonical form

The canonical form of an entity URI after normalization is the lowercase form of that URI with surrounding whitespace trimmed and internal whitespace in the `id` component collapsed to hyphens.

For **formal URIs** (`stigmem://authority/type/id`):

| Component   | Canonical rule |
|-------------|---------------|
| `authority` | Lowercase; trim surrounding whitespace |
| `type`      | Lowercase; trim surrounding whitespace |
| `id`        | Lowercase; trim surrounding whitespace; collapse internal whitespace runs to a single hyphen |

For **informal URIs** (any non-`stigmem://` form):
- Lowercase the entire string; trim surrounding whitespace; collapse internal whitespace to hyphens.
- The URI format is **preserved** (informal stays informal — not converted to formal).
- The §2.5 constraint "nodes MUST NOT auto-rewrite informal URIs to formal URIs" is honored: lowercasing the informal form is not the same as expanding it to the formal scheme.

#### 2.6.3 Strict normalizer — normative algorithm

Reference implementation at `stigmem/node/src/stigmem_node/entity_normalizer.py`:

```python
import re

_FORMAL_URI_RE = re.compile(r"^stigmem://([^/]+)/([^/]+)/(.+)$")
_WHITESPACE_RE = re.compile(r"\s+")

class NormalizationError(ValueError):
    pass

def normalize_entity_uri(raw: str) -> str:
    """Return the canonical form of an entity URI string.

    Raises NormalizationError on empty or whitespace-only input.
    """
    if not raw or not raw.strip():
        raise NormalizationError("entity URI must not be empty")

    stripped = raw.strip()
    m = _FORMAL_URI_RE.match(stripped)
    if m:
        authority = m.group(1).strip().lower()
        type_slug = m.group(2).strip().lower()
        id_part   = _WHITESPACE_RE.sub("-", m.group(3).strip().lower())
        if not authority or not type_slug or not id_part:
            raise NormalizationError(
                f"normalization produced empty component in formal URI: {raw!r}"
            )
        return f"stigmem://{authority}/{type_slug}/{id_part}"

    # Informal URI: lowercase and collapse whitespace; format preserved
    return _WHITESPACE_RE.sub("-", stripped.lower())
```

**Invariants the normalizer MUST satisfy:**

1. **Deterministic:** identical inputs always produce identical outputs.
2. **Idempotent:** `normalize(normalize(x)) == normalize(x)` for all valid inputs.
3. **Total on valid inputs:** every non-empty string produces exactly one output; invalid inputs raise `NormalizationError`.

**What the strict normalizer does NOT do:**
- Alias resolution (e.g., `user:alice` ≡ `user:a.smith`) — Phase 6 fuzzy resolver.
- Existence validation against the fact store.
- Semantic similarity matching.
- Conversion of informal URIs to formal URIs (§2.5 prohibits silent auto-rewrite).

#### 2.6.4 Ingest-path contract

Nodes MUST apply the strict normalizer to the `entity` and `source` fields of every incoming fact **before** persistence:

1. If `normalize_entity_uri` returns a canonical URI, store the canonical form.
2. If the input was an informal URI (does not match `stigmem://`), also emit a deprecation warning to stderr as specified in §2.5.
3. If `normalize_entity_uri` raises `NormalizationError`, reject the fact:

```
HTTP 400
{ "error": "invalid_entity_uri", "detail": "<NormalizationError message>" }
```

**Why normalize at ingest (not query):** Query-time normalization would require every consumer to carry normalization logic and would leave non-canonical data permanently in the store. Ingest normalization ensures the stored form is always canonical; all queries use exact string matching on the canonical form, keeping query performance O(1) on indexed lookups.

**Retraction and contradiction compatibility:** Ingest normalization is safe for retractions (§5.4) and contradiction detection (§3.3). If a retraction and the original fact both normalize to the same canonical entity, they match correctly. A client sending a retraction for a non-canonical URI normalizes to the same canonical form as the original, and retraction semantics apply as expected.

#### 2.6.5 Query-time backward compatibility

For nodes upgrading to v0.7, **query parameters are also normalized** before matching:

```
GET /v1/facts?entity=<raw>&...
```

The node MUST apply `normalize_entity_uri` to the `entity` and `source` query parameters before executing the database query. This allows clients holding references to pre-normalization forms to still retrieve existing facts written after v0.7 is deployed.

For pre-v0.7 facts stored with non-canonical URIs, the alias table (§2.6.6, migration 003) is the recommended migration path.

#### 2.6.6 Migration guide for existing facts

Facts stored before v0.7 strict normalization was deployed may use informal URIs or non-canonical formal URIs. Because facts are immutable (§2), they cannot be rewritten in place. The following migration strategies are available:

**Option A — Alias table (recommended for production nodes)**

Migration 003 adds an `entity_aliases` table that maps known informal/legacy URIs to their canonical equivalents (see §10). Populate it by scanning the `facts` table for non-canonical `entity` and `source` values and inserting the raw → canonical mapping. At query time, the node can join against this table to find pre-v0.7 facts via canonical queries.

**Option B — Re-assertion sweep (for smaller nodes or clean migration windows)**

For each fact with a non-canonical entity URI:
1. Assert a new fact with the canonical entity, the same `(relation, value, scope, confidence)`, and provenance `source="system:stigmem:migration"`.
2. Retract the original fact by asserting `confidence=0.0` for the original `(entity_raw, relation, scope)`.

The original facts are retained in the store with `confidence=0.0` for audit purposes.

**Phased rollout recommendation:**

| Phase | Action |
|-------|--------|
| v0.7 deploy | Enable strict normalizer on ingest. Query normalization enabled. |
| +2 weeks | Scan facts table; populate alias table for any non-canonical existing facts. |
| +4 weeks | Run re-assertion sweep for nodes with < 10k facts; otherwise maintain alias table. |
| v0.8 target | Remove alias table read path; all facts use canonical URIs. |

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

**Decay sweeper (v0.8):** For operator-managed confidence decay over time, see §15. The decay sweeper handles gradual confidence reduction and bulk TTL retraction without requiring clients to manage each fact's expiry individually.

### 3.3 Contradiction — v0.5 formalized

A **contradiction** exists when two facts `a`, `b` satisfy all of:
- `a.entity == b.entity`
- `a.relation == b.relation`
- `a.scope == b.scope`
- `a.value != b.value`
- `a.confidence > 0.0 && b.confidence > 0.0`

**Both facts are retained. Neither is silently overwritten.**

**v0.7 note:** Because `entity` is normalized on ingest (§2.6), two facts about the same real-world entity written with different cases (e.g. `project/EG-18` vs `project/eg-18`) now normalize to the same canonical entity and correctly trigger contradiction detection. Pre-v0.7 fragmented facts are not retroactively merged — use the alias table or re-assertion sweep (§2.6.6) to consolidate them.

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

**v0.8 note:** In N-node topologies, scope enforcement is per-hop, not end-to-end. See §6.8 for the transitive scope propagation invariant that closes the re-federation gap.

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
{ "entity": "stigmem://company.acme/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.acme/agent/assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", "hlc": "...", ...fact... }
```

### 5.2 Query facts

```
GET /v1/facts?entity=stigmem://company.acme/user/alice&relation=memory:role
→ 200 { "facts": [...], "total": 1, "cursor": null }
```

Query params: `entity`, `relation`, `source`, `scope`, `min_confidence`,
`after`, `include_contradicted`, `include_expired`, `cursor`, `limit`.

### 5.3 Node metadata

```
GET /.well-known/stigmem
→ 200 {
    "version":            "0.8",
    "node_id":            URI,
    "node_url":           string,
    "auth":               "none" | "required",
    "federation":         "disabled" | "enabled",
    "federation_pubkey":  string,   // v0.5: base64url Ed25519 public key; omit if federation disabled
    "federation_version": string,   // v0.5: semver range this node speaks, e.g. "0.8"
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
{ "entity": "stigmem://company.acme/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.acme/agent/assistant", "confidence": 0.0, "scope": "company" }
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

### 5.12 Lint — v0.7 Normative

See §14 for semantics and wire shape.

```
POST /v1/lint
Authorization: Bearer <api-key>
{ "scope": "company", "checks": ["contradiction", "stale"] }
→ 200 { "findings": [...], "checked_at": "...", "scope": "company",
         "checks_run": ["contradiction","stale"], "fact_count": 142 }
```

### 5.13 Synthesize scope — v0.8 Draft

See §16 for semantics. Returns a confidence-weighted summary view of a scope's live facts.

```
POST /v1/synthesis
Authorization: Bearer <api-key>
{ "scope": "company", "entity": "<optional-uri>", "min_confidence": 0.5 }
→ 200 { "summary": [...], "synthesized_at": "...", "scope": "company",
         "fact_count": 142, "contradiction_count": 3 }
```

---

## 6. Federation — v0.5 Specification (extended v0.8)

> **v0.5 status:** §6 promoted from RFC stub to concrete spec. §6.1–§6.6 are stable (normative). §6.7–§6.8 are new v0.8 draft sections covering N-node backpressure and scope propagation invariants.

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
exponentially with jitter. Max backoff: 5 minutes. See §6.7 for N-node cascade
backpressure patterns.

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

### 6.7 N-node Backpressure Patterns — v0.8 Draft

> **v0.8 status:** These patterns were identified during Phase 6 4-node local topology
> work. They are draft guidance, pending validation in the D1 correctness test suite.
> Promotion to normative is a v0.9 target.

In topologies with N > 2 nodes, backpressure from one publisher can cascade through
relay nodes (nodes that both ingest from peers and are themselves pulled from).

#### 6.7.1 The relay cascade problem

Consider a 4-node topology: A ← B ← C ← D (each node pulls from the next).

If node A emits a burst of 10,000 public facts within a short window:
1. B receives the burst and its ingest queue grows.
2. C is pulling from B at the normal cadence. B may return 429 if its write
   path is saturated (disk I/O, WAL flush, etc.).
3. C backs off on B, but D continues pulling from C at the normal rate.
4. C now has a growing lag behind B AND is serving D at full pull rate.

Without relay-aware backpressure, C can fall further and further behind B while
continuing to serve D with stale data, without any signal to D that it is receiving
lagged facts.

#### 6.7.2 Recommended relay behavior (draft)

Nodes that are simultaneously a subscriber and publisher (relay nodes) SHOULD:

1. **Propagate backpressure signals.** If a relay node's inbound replication lag
   exceeds `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` (default: 60,000 ms), it SHOULD
   include a `X-Stigmem-Replication-Lag: <lag_ms>` response header on pull responses
   to its own subscribers. Subscribers MAY use this to slow their pull cadence.

2. **Apply admission throttle.** If the relay node's inbound lag exceeds
   `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` (default: 300,000 ms — 5 minutes), the node
   MAY return HTTP 503 on pull requests from its own subscribers with body:
   ```json
   { "error": "relay_lag_exceeded", "lag_ms": <integer>, "retry_after_s": <integer> }
   ```
   The `retry_after_s` SHOULD be proportional to the lag: `lag_ms / 1000`.

3. **Expose lag in well-known.** Nodes SHOULD include a `replication_lag_ms` field in
   `/.well-known/stigmem` (value: max lag across all inbound peers; omit if not a relay
   or if lag is within normal bounds). This allows topology health tools to detect
   degraded relay nodes without polling pull endpoints.

#### 6.7.3 Backpressure conformance (draft)

These env vars configure relay behavior:

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` | `60000` | Lag threshold for warning header |
| `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` | `300000` | Lag threshold for 503 throttle |
| `STIGMEM_FEDERATION_RELAY_ENABLED` | `true` | Set `false` to disable relay behavior (leaf nodes) |

Conformance tests for relay backpressure will be added to the 4-node topology test
suite (`stigmem/node/tests/test_federation_4node.py`) before v0.8 stabilization.

### 6.8 Scope Propagation Invariants — v0.8 Draft

> **v0.8 status:** These invariants close the transitive scope escalation gap identified
> during Phase 6 4-node topology work. Draft; to be validated against correctness tests
> before promotion to normative.

In a 2-node topology, scope enforcement is bilateral and straightforward. In an N-node
topology, a fact can travel through multiple hops. The following invariants ensure that
scope boundaries set by the originating node are respected end-to-end.

#### 6.8.1 Transitive scope non-escalation

**Invariant:** A fact's scope MUST NOT be escalated at any relay hop.

A relay node (node B, receiving from node A and serving node C) MUST NOT:
- Return a fact with `scope="company"` to node C if node A's PeerDeclaration with
  node B restricts to `allowed_scopes=["public"]`.
- Infer that because node C is permitted `company` scope with node B, node B can
  re-federate `company` facts it received from node A under a `["public"]`-only declaration.

**Implementation requirement:** Nodes MUST tag every ingested federated fact with its
**source peer's declaration scope** at ingest time. When serving a pull request, a
relay node MUST intersect the fact's `origin_allowed_scopes` (the scope permitted when
the fact first entered the federation) with the current peer's `allowed_scopes`. Only
facts where `fact.scope ∈ origin_allowed_scopes ∩ current_peer.allowed_scopes` are
returned.

The `received_from` meta-fact (§3.1) records the immediate sender, not the origin.
Relay nodes MUST also store `origin_node_id` and `origin_allowed_scopes` per-fact when
ingesting federated facts. These fields are internal to the node and MUST NOT be
re-replicated.

#### 6.8.2 Re-federation restriction for company-scoped facts

**v0.8 resolves §8.5 (v0.7 open question).** The following rule is normative as of v0.8:

A node that receives a `company`-scoped fact from peer A (where peer A's declaration
explicitly includes `"company"` in `allowed_scopes`) MUST NOT re-federate that fact
to any third node C, regardless of what node C's PeerDeclaration allows.

**Rationale:** `company`-scoped facts represent internal knowledge of the originating
organization. The originating node's explicit `allowed_scopes=["company"]` declaration
is an authorization grant to a specific peer, not a grant to that peer's downstream
federation network.

**Implementation requirement:** `company`-scoped ingested facts MUST be tagged
`re_federation_blocked=true` at ingest. Federation pull responses MUST exclude facts
with `re_federation_blocked=true`.

**Exception:** If the originating node explicitly sets
`STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=true` (default `false`), the
re-federation restriction is lifted for that node's outbound `company` facts. This
flag is operator-level and MUST be logged to the federation audit log each time it
is applied.

#### 6.8.3 Scope propagation edge cases

The following edge cases were identified during Phase 6 4-node topology testing:

1. **Mixed-scope batch push.** A push payload (`POST /v1/federation/facts/push`) may
   contain facts of multiple scopes. Nodes MUST enforce per-fact scope checking within
   a batch; a scope violation on one fact MUST NOT cause the entire batch to be rejected.
   The response's `rejected` count and `errors` array MUST enumerate each rejected fact.

2. **Scope of contradiction meta-facts.** When a federated fact creates a contradiction,
   the `stigmem:conflict:between` meta-fact MUST inherit the scope of the conflicting
   facts. If two facts in `company` scope conflict, the conflict record is `company`-scoped.
   If a `public` fact from a peer conflicts with a local `company` fact (same entity, same
   relation), the conflict record is `company`-scoped (the narrower scope wins).

3. **`team`-scoped fact from a misbehaving peer.** If a peer sends a `team`-scoped fact
   and the PeerDeclaration does not include `"team"` in `allowed_scopes`, the fact MUST be
   rejected with HTTP 403 and logged as `event_type="scope_violation"` in the federation
   audit log. This applies even if `STIGMEM_FEDERATION_ALLOW_TEAM=true` is set locally —
   the PeerDeclaration is the authoritative grant, not the local env flag.

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
| Case normalization at ingest (v0.7) | `project/EG-18` and `project/eg-18` created silent entity fragments — the root cause in earlier work. Normalizing at ingest (not query) keeps query O(1) on indexed lookups and prevents non-canonical data from accumulating in the store. Informal URIs are lowercased in place (not converted to formal) to preserve the §2.5 anti-rewrite invariant. |
| Lint as first-class operation (v0.7) | Karpathy LLM-Wiki analysis (Phase 5) identified that adapter-side ad-hoc contradiction/stale queries are inconsistent and fragile. A single normative `POST /v1/lint` provides uniform sweep semantics with deterministic severity levels, enabling the decay engine (Phase 6) to delegate sweep discovery to the node rather than each adapter reimplementing it. |
| Lint uses POST, not GET (v0.7) | The lint request body can include multiple optional filter fields (`entity`, `relation`, `checks`, `stale_lookahead_s`). A GET query string with complex filters risks URL-length limits and encoding ambiguity. POST body is unambiguous. Lint is idempotent despite using POST; this is documented explicitly (§14.5). |
| Lint is strictly read-only (v0.7) | Diagnostic operations must not modify state. A lint sweep that auto-retracted stale facts would conflate discovery with action, removing the human/agent approval step before retraction. Lint observes; retraction is a deliberate subsequent operation. |
| Four lint checks, independently selectable (v0.7) | Contradiction detection is an operational concern (run continuously); stale/orphan sweeps are maintenance tasks (run on schedule); broken-ref detection is a data-quality check (run during ingestion audits). Decoupling them lets callers compose the sweep they need without paying for all four. |
| Decay sweeper separate from lint (v0.8) | Lint is read-only diagnosis; decay is write-path remediation (confidence reduction + retraction). Merging them would violate the lint read-only invariant and make audit harder. Sweeper runs are logged separately from lint runs. |
| confidence decay over `valid_until` reduction (v0.8) | Setting `valid_until` is a binary expiry; confidence decay is gradual. For knowledge that degrades over time (e.g. an agent's working context facts), a smooth confidence reduction gives downstream agents a calibrated signal to de-weight the fact before it disappears entirely. Both mechanisms coexist. |
| Company-scoped re-federation blocked by default (v0.8) | Phase 6 4-node topology revealed that a relay node with wider permissions than the originating peer could silently propagate company-internal facts to third parties. Blocking re-federation by default closes this scope escalation path while preserving the explicit opt-in escape hatch for operators who need it. |
| Relay lag signal in response headers (v0.8) | Subscribers cannot know a relay's inbound lag from the facts themselves (HLC timestamps reflect write time, not ingestion lag). A response header is the lowest-overhead signaling path; it does not require a new route and is backward-compatible (old clients ignore unknown headers). |

---

## 8. Open Questions (v0.8)

**Resolved in v0.6:**
- ~~§8.1 Entity URI scheme~~ — resolved: formal `stigmem://` scheme normative; informal deprecated with warning (§2.5).
- ~~§8.4 Capability negotiation requirement~~ — resolved: capability negotiation required for federation-enabled nodes (§6.2).

**Resolved in v0.7:**
- ~~Lint primitive vocabulary~~ — resolved: lint promoted to first-class operation; §14 Lint Semantics normative; `POST /v1/lint` route; `lint_scope` MCP tool.
- ~~Entity fragmentation from case variation~~ — resolved: strict normalizer on ingest (§2.6); case normalization and whitespace collapse applied to `entity` and `source` fields; migration 003 (entity_aliases table) for pre-v0.7 data.

**Resolved in v0.8:**
- ~~§8.2 Multi-node federation (3+ nodes)~~ — resolved: §6.7 N-node backpressure patterns (draft); §6.8 scope propagation invariants (draft). The N-node model uses pairwise PeerDeclarations; gossip is not required. Relay backpressure and transitive scope enforcement are draft; to be validated by D1 correctness tests before final promotion.
- ~~§8.5 `company`-scoped federation permissiveness~~ — resolved: `company`-scoped facts received from a peer MUST NOT be re-federated to third nodes (§6.8.2). The originating node's grant is non-transitive by default.

**Remaining open:**

1. **Intent envelope wire route.** Phase 2 implemented fact model only. Intent envelope wired
   through Phase 4 adapters (handoff, escalation, decision facts), but the full
   `IntentEnvelope` wire route is not yet implemented. Deferred to Phase 7.

2. **Conflict resolution policy plugins.** Should operators be able to register custom
   resolution functions? Deferred until a concrete use case emerges from Phase 6 testing.

3. **Audit log retention.** The federation audit log has no specified retention policy.
   Nodes SHOULD retain at least 7 days (time-based policy is a Phase 7 concern).

4. **Async lint job API.** The synchronous lint route (§14.5) is sufficient for scopes
   under 100,000 facts. The async job API (`GET /v1/lint/jobs/:job_id`) is specified but
   not yet implemented. Phase 7 target.

5. **Async decay sweep API.** The synchronous decay sweep (§15.4) is appropriate for
   moderate scope sizes. Async sweep for large scopes (>100,000 facts) follows the lint
   async pattern (§14.5); specified in §15.4 but deferred for implementation.

6. **Fuzzy entity resolver.** Alias-based resolution (§2.6.6) handles canonical URI
   lookup. Semantic similarity matching (e.g. `user:alice` ≡ `user:a.smith`) is
   deferred to the Phase 7 fuzzy resolver (Kompl-style 3-layer matcher).

7. **Synthesis aggregation strategy for contradicted facts.** When `synthesize_scope`
   encounters a contradicted `(entity, relation, scope)` triple, it currently returns
   the highest-confidence value and annotates the output with `contradicted: true`.
   Whether synthesis should surface both values or attempt a weighted merge is an open
   question for Phase 7.

---

## 9. Namespace Registry

### 9.1 Reserved prefixes (maintained by spec)

| Prefix | Governed by | Purpose |
|---|---|---|
| `stigmem:` | Spec maintainers | Core protocol relations: `stigmem:ttl`, `stigmem:received_from`, `stigmem:member`, `stigmem:conflict:between`, `stigmem:conflict:status`, `stigmem:resolves` |
| `rel:` | Spec maintainers | Reification primitives: `rel:subject`, `rel:object`, `rel:type` |
| `stigmem:lint:` | Spec maintainers | Reserved for future lint-related protocol relations. v0.7 lint is a pure API operation (no fact assertions); this prefix is reserved to prevent squatting ahead of Phase 6 lint enhancements. |
| `stigmem:decay:` | Spec maintainers | Reserved for decay sweeper protocol relations. v0.8 decay sweep is a pure API operation; this prefix is reserved for future decay policy fact assertions (e.g. per-entity decay overrides). |

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

## 10. Schema and Migration (v0.5 + v0.7)

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

### New tables — migration 003 (v0.7)

```sql
-- Entity alias table for pre-v0.7 migration tooling (spec §2.6.6)
CREATE TABLE IF NOT EXISTS entity_aliases (
    raw_uri       TEXT NOT NULL,          -- original non-canonical stored form
    canonical_uri TEXT NOT NULL,          -- normalized form (output of normalize_entity_uri)
    created_at    TEXT NOT NULL,
    PRIMARY KEY (raw_uri)
);

CREATE INDEX IF NOT EXISTS idx_entity_aliases_canonical ON entity_aliases(canonical_uri);
```

### New columns — migration 004 (v0.8)

```sql
-- Scope propagation tracking for N-node federation (spec §6.8.1)
ALTER TABLE facts ADD COLUMN origin_node_id        TEXT;   -- NULL for locally-asserted facts
ALTER TABLE facts ADD COLUMN origin_allowed_scopes TEXT;   -- JSON array; NULL for locally-asserted facts
ALTER TABLE facts ADD COLUMN re_federation_blocked INTEGER NOT NULL DEFAULT 0;  -- 1 if company-scope re-fed is blocked

CREATE INDEX IF NOT EXISTS idx_facts_re_federation ON facts(re_federation_blocked, scope);
```

**Note:** Migration 004 columns are NULL for all pre-v0.8 facts. Nodes MUST populate
`origin_node_id` and `origin_allowed_scopes` only for facts received via federation
after v0.8 is deployed.

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
  "version":    "0.8",
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
| `LINT_VECTORS` | `lint-contradiction`, `lint-stale`, `lint-stale-lookahead`, `lint-orphan`, `lint-broken-ref`, `lint-broken-ref-intent`, `lint-clean`, `lint-scope-filter` | `POST /v1/lint` — all four checks; severity mapping; scope isolation |
| `DECAY_VECTORS` | `decay-confidence-reduction`, `decay-retraction`, `decay-scope-filter`, `decay-dry-run`, `decay-exempt` | `POST /v1/decay/sweep` — confidence decay, retraction, scope isolation, dry-run mode, exempt relations |
| `SYNTHESIS_VECTORS` | `synthesis-basic`, `synthesis-contradicted`, `synthesis-min-confidence`, `synthesis-empty` | `POST /v1/synthesis` — confidence ordering, contradiction annotation, min-confidence filter |

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
`NODE_INFO_VECTOR`, `LINT_VECTORS`, `DECAY_VECTORS`, `SYNTHESIS_VECTORS`, and its
adapter-specific lifecycle tests with a live Stigmem node.

---

## 13. Phase 6 Progress

The following Phase 5 deliverables are addressed in v0.7 (complete):

- **Lint primitive** (Phase 5 Deliverable 3): §14 Lint Semantics normative. Done.
- **Entity normalization layer** (Phase 5 Deliverable 4): §2.6 Entity Naming Rules normative; strict normalizer on ingest path implemented (`entity_normalizer.py`); migration 003 (entity_aliases). Done.
- **Bug fixes**: §resolution-semantics (Deliverable 1) and §query-semantics (Deliverable 2) complete.

Phase 6 deliverables addressed in v0.8 (draft):

- **4-node federation backpressure + scope propagation** (Phase 6 D1 findings): §6.7–§6.8 draft normative sections. Pending D1 correctness test validation before stable promotion.
- **Decay semantics** (Phase 6 D4): §15 Decay Semantics draft. `POST /v1/decay/sweep` route; `DecayPolicy` registry; `decay_scope` MCP tool. Pending D4 implementation.
- **Synthesis** (Phase 6 D4): §16 Synthesis draft. `POST /v1/synthesis` route; `synthesize_scope` MCP tool. Pending D4 implementation.
- **Schema migration 004**: `origin_node_id`, `origin_allowed_scopes`, `re_federation_blocked` columns for scope-propagation tracking. Pending D1 validation.

The following are deferred to Phase 7+:

- Multi-tenant RBAC / OIDC
- Binary wire encoding
- Full `IntentEnvelope` wire route (§4 remains spec-only; Phase 7 target)
- Entity URI migration tooling (auto-rewrite from informal to formal URIs)
- Hosted public Stigmem node
- Async lint job API (`GET /v1/lint/jobs/:job_id`)
- Async decay sweep API (large scope; follows lint async pattern)
- Fuzzy entity resolver (Kompl-style 3-layer)
- Conflict resolution policy plugins
- Audit log retention policy

---

## 14. Lint Semantics — v0.7 Normative

The **lint** operation is a first-class Stigmem protocol operation that performs
health-check sweeps over a bounded scope or entity. Lint is strictly **read-only**:
it observes and reports issues without writing facts or modifying node state.

Lint bridges the decay engine (§15) and the current production node.
Running `lint_scope` against a live node reveals knowledge-base health degradation
before it affects query results or agent behavior.

### 14.1 Lint Checks

Four normative checks, each independently selectable:

| Check | What it detects |
|---|---|
| `contradiction` | Facts sharing the same `(entity, relation, scope)` tuple where both have `confidence > 0.0` and the conflict is unresolved (status `"unresolved"` in the `conflicts` table). |
| `stale` | Facts whose `valid_until < now` and whose `confidence > 0.0`; optionally, facts whose `valid_until < now + stale_lookahead_s` (approaching expiry). |
| `orphan` | Entities where every known fact is either retracted (`confidence = 0.0`) or expired (`valid_until < now`). No live facts remain for the entity. |
| `broken_ref` | Facts with `value.type = "ref"` whose `value.v` targets an entity or fact ID that has no live (non-retracted, non-expired) facts on this node. |

**Default behavior:** If `checks` is omitted or empty, all four checks run.

**Scope of search:** Each check operates within the `scope` specified in the lint
request. Checks never cross scope boundaries — a `broken_ref` finding in `company` scope
is only reported if the broken ref also falls within `company` scope.

### 14.2 LintFinding Shape

```
LintFinding {
  check:    "contradiction" | "stale" | "orphan" | "broken_ref"
  severity: "error" | "warning" | "info"
  entity:   URI               // entity under examination
  relation: string | null     // relevant relation; null for the orphan check
  fact_ids: UUID[]            // IDs of the fact(s) involved in the finding
  detail:   string            // human-readable explanation suitable for display
}
```

### 14.3 Severity Mapping

| Check | Condition | Severity |
|---|---|---|
| `contradiction` | Unresolved conflict between two live facts | `error` |
| `stale` | `valid_until < now` and `confidence > 0.0` | `warning` |
| `stale` | `valid_until < now + stale_lookahead_s` (not yet expired but approaching) | `info` |
| `orphan` | Entity has no live facts | `info` |
| `broken_ref` | Ref target entity has no live facts in this node's store | `warning` |
| `broken_ref` | Broken ref where `relation` is `intent:handoff_to` or `intent:context_ref` | `error` |

**Severity rationale:**
- `contradiction` is always `error` — unresolved contradictions corrupt query results for all callers.
- `stale` and `orphan` are non-critical health signals; expired or empty entities do not block reads.
- `broken_ref` on intent-routing relations (`intent:handoff_to`, `intent:context_ref`) is `error`
  because a broken handoff silently discards agent context during delegation.

### 14.4 Wire Format

#### Request

```
POST /v1/lint
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":             FactScope,   // required: which scope to sweep
  "checks":            string[],    // optional; default: ["contradiction","stale","orphan","broken_ref"]
  "entity":            URI?,        // optional: restrict sweep to one entity
  "relation":          string?,     // optional: restrict sweep to one relation
  "stale_lookahead_s": integer?     // optional: also flag facts expiring within N seconds; default 0
}
```

#### Response

```
200 OK
{
  "findings":   LintFinding[],   // zero or more findings; empty array = clean
  "checked_at": string,          // ISO 8601 UTC timestamp of when the sweep ran
  "scope":      FactScope,       // echoed from the request
  "checks_run": string[],        // which checks actually ran (echoed or defaulted)
  "fact_count": integer          // number of facts scanned (not findings; helps gauge sweep completeness)
}
```

#### Authorization

The caller's API key must have read access to the requested `scope` (§3.5). Nodes MUST
return HTTP 403 if the key's `allowed_scopes` does not include the requested `scope`.

#### Error responses

| HTTP | Condition |
|---|---|
| 400 | `scope` field missing or invalid; unknown `checks` value |
| 403 | Caller's key is not authorized for the requested scope |
| 202 | Scope exceeds 100,000 facts (async path; see §14.5) |

### 14.5 Performance Contract

- `POST /v1/lint` MUST respond synchronously within **30 seconds** for scopes with fewer
  than 100,000 facts.
- For scopes exceeding 100,000 facts, nodes MAY respond with **HTTP 202**:
  ```
  202 Accepted
  { "job_id": "<uuid>", "status": "pending", "estimated_s": integer }
  ```
  The caller polls `GET /v1/lint/jobs/:job_id` until `status` is `"done"` or `"failed"`.
  The async job API is specified here but deferred to Phase 7 implementation.
- The sweep MUST be **read-only**. Nodes MUST NOT assert, retract, or update any fact
  as a side effect of a lint call. This invariant applies even to internal bookkeeping.

### 14.6 Relationship to Other Operations

Lint is **diagnostic**, not prescriptive:

| Finding type | Lint reports | Remediation action (separate call) |
|---|---|---|
| `contradiction` | Which facts conflict | `POST /v1/conflicts/:id/resolve` (§5.10) |
| `stale` | Which facts have expired | `POST /v1/decay/sweep` with `mode="retract"` (§15) or `POST /v1/facts` with `confidence=0.0` |
| `orphan` | Which entities have no live facts | No action required; orphans are informational |
| `broken_ref` | Which ref facts have missing targets | Assert missing target entity, or retract the broken ref |

### 14.7 MCP Tool: `lint_scope`

The `lint_scope` MCP tool exposes `POST /v1/lint` to any MCP-aware agent without SDK
installation.

#### Tool definition

```json
{
  "name": "lint_scope",
  "description": "Sweep a Stigmem scope for knowledge-base health issues. Checks for: unresolved contradictions, stale or expiring facts, orphaned entities with no live facts, and broken cross-references. Read-only — reports findings without modifying any facts. Use resolve_contradiction to fix contradictions found here.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to sweep."
      },
      "checks": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["contradiction", "stale", "orphan", "broken_ref"]
        },
        "description": "Which checks to run. Omit to run all four."
      },
      "entity": {
        "type": "string",
        "description": "Optional. Restrict sweep to facts about a single entity URI."
      },
      "relation": {
        "type": "string",
        "description": "Optional. Restrict sweep to a single relation."
      },
      "stale_lookahead_s": {
        "type": "integer",
        "description": "Optional. Also flag facts expiring within this many seconds. Default 0 (expired-only)."
      }
    },
    "required": ["scope"]
  }
}
```

#### Output shape

```json
{
  "findings": [
    {
      "check": "contradiction",
      "severity": "error",
      "entity": "stigmem://company.acme/user/alice",
      "relation": "memory:role",
      "fact_ids": ["fact-uuid-1", "fact-uuid-2"],
      "detail": "Two live facts with different values for (entity, relation, scope)"
    }
  ],
  "checked_at": "2026-05-02T14:00:00Z",
  "scope": "company",
  "checks_run": ["contradiction", "stale", "orphan", "broken_ref"],
  "fact_count": 1024
}
```

### 14.8 Conformance Test Vectors

Normative lint vectors are defined in `sdks/stigmem-py/tests/conformance_vectors.py`
under `LINT_VECTORS`. Each vector includes a `setup` list of fact assertions to run
before the lint sweep, so results are deterministic.

**Required vectors for conformance:**

| Vector ID | Check | Scenario | Expected `findings` |
|---|---|---|---|
| `lint-contradiction` | `contradiction` | Two facts same (entity, relation, scope), different values, both confidence > 0 | ≥1 finding, check=`contradiction`, severity=`error` |
| `lint-stale` | `stale` | Fact with `valid_until` in the past | ≥1 finding, check=`stale`, severity=`warning` |
| `lint-stale-lookahead` | `stale` | Fact with `valid_until` within lookahead window but not yet elapsed | ≥1 finding, check=`stale`, severity=`info` |
| `lint-orphan` | `orphan` | Entity with only retracted facts (confidence=0.0) | ≥1 finding, check=`orphan`, severity=`info` |
| `lint-broken-ref` | `broken_ref` | Ref fact pointing to entity with no live facts | ≥1 finding, check=`broken_ref`, severity=`warning` |
| `lint-broken-ref-intent` | `broken_ref` | Broken ref on `intent:handoff_to` relation | ≥1 finding, check=`broken_ref`, severity=`error` |
| `lint-clean` | all | Scope with only one healthy live fact | findings = `[]` |
| `lint-scope-filter` | `contradiction` | Contradiction exists in `company` scope; lint request on `local` scope | findings = `[]` (scope isolation) |

All eight vectors MUST pass against a reference Stigmem node for conformance.

---

## 15. Decay Semantics — v0.8 Draft

> **v0.8 status:** Draft. The decay sweeper (`POST /v1/decay/sweep`) and `decay_scope`
> MCP tool are specified here. Implementation is the D4 deliverable. Wire
> format and DecayPolicy registry are draft; conformance test vectors (`DECAY_VECTORS`)
> will be finalized with D4 implementation. This section will be promoted to normative
> in v0.9 once conformance tests pass against a live node.

The **decay** operation applies operator-configured TTL and confidence-reduction policies
to live facts, producing retractions or confidence updates. Decay is the **remediation
complement to lint**: lint identifies stale/low-confidence facts; the decay sweeper acts
on them.

### 15.1 DecayPolicy

A `DecayPolicy` configures how facts of a given relation (or all relations) decay over time.

```
DecayPolicy {
  id:              string          // unique identifier for this policy
  relation:        string | "*"   // relation this policy applies to; "*" = all relations
  scope:           FactScope | "*" // scope this policy applies to; "*" = all scopes
  mode:            DecayMode
  ttl_s:           integer?        // for mode="retract": retract facts older than ttl_s seconds
  half_life_s:     integer?        // for mode="confidence": halve confidence every half_life_s seconds
  min_confidence:  float?          // for mode="confidence": do not reduce below this floor; default 0.0
  exempt_relations: string[]       // relations that are never decayed by this policy (e.g. stigmem: namespace)
}

DecayMode =
  | "retract"      // assert confidence=0.0 for matching facts older than ttl_s
  | "confidence"   // reduce confidence by half every half_life_s seconds; floor at min_confidence
  | "dry_run"      // same logic as retract/confidence but no writes; returns what would be changed
```

**Policy registry:** Nodes maintain a list of `DecayPolicy` objects configured via:
- Environment variable: `STIGMEM_DECAY_POLICIES` (JSON array of `DecayPolicy` objects).
- Admin API: `GET/POST/DELETE /v1/decay/policies` (management endpoint; not yet implemented; Phase 7).

**Default policy:** If no policies are configured, the decay sweeper is a no-op. Nodes do
not apply any automatic decay by default.

**Policy evaluation order:** Policies are evaluated most-specific-first: exact `relation`
match before `"*"`, exact `scope` match before `"*"`. The first matching policy wins.

**Exempt relations:** The `stigmem:` namespace (system-generated facts) and `rel:`
namespace (reification primitives) are always exempt from decay and MUST NOT be
retracted or confidence-reduced by the sweeper, regardless of policy configuration.
The `exempt_relations` field on individual policies may add further exemptions.

### 15.2 Decay Sweep Wire Format

#### Request

```
POST /v1/decay/sweep
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":    FactScope,    // required: which scope to sweep
  "mode":     DecayMode?,   // optional: override all policies' mode for this run (e.g. force "dry_run")
  "policy_id": string?      // optional: run only this named policy
}
```

#### Response

```
200 OK
{
  "swept_at":          string,   // ISO 8601 UTC
  "scope":             FactScope,
  "mode":              DecayMode,
  "facts_evaluated":   integer,
  "facts_retracted":   integer,  // 0 in dry_run mode
  "facts_reduced":     integer,  // confidence-reduced; 0 in dry_run mode
  "dry_run_would_retract": integer,  // populated in dry_run mode; 0 otherwise
  "dry_run_would_reduce":  integer,  // populated in dry_run mode; 0 otherwise
  "policies_applied":  string[]  // policy IDs that matched at least one fact
}
```

#### Error responses

| HTTP | Condition |
|---|---|
| 400 | `scope` missing or invalid; `policy_id` not found; invalid `mode` override |
| 403 | Caller's key lacks write access to the requested scope |
| 202 | Scope exceeds 100,000 facts (async path; same pattern as §14.5) |

#### Authorization

The caller's API key MUST have write access to the requested scope. The decay sweep
writes retractions (new facts with `confidence=0.0`) or confidence-update facts;
these are regular fact assertions subject to all normal write invariants.

### 15.3 Decay and Immutability

The decay sweeper does **not** mutate existing facts. All decay actions are expressed
as new immutable fact assertions:

- **Retraction:** A new fact `(entity, relation, scope, confidence=0.0, source="system:stigmem:decay")` is asserted. The original fact is retained.
- **Confidence reduction:** A new fact with `confidence = original_confidence * exp(-ln(2) / half_life_s * elapsed_s)` is asserted, floored at `min_confidence`. The `source` is `"system:stigmem:decay"`.

Both produce entries in the normal facts table and are visible in `GET /v1/facts` responses.
`source="system:stigmem:decay"` allows callers to distinguish sweep-induced retractions from
agent-authored retractions.

### 15.4 Performance Contract

- `POST /v1/decay/sweep` MUST respond synchronously within **60 seconds** for scopes
  with fewer than 100,000 facts. (Decay is more expensive than lint because it writes.)
- For scopes exceeding 100,000 facts, nodes MAY respond with HTTP 202 following the
  same async job pattern as §14.5.
- **Dry-run is always synchronous.** `mode="dry_run"` performs no writes and MUST
  respond within 30 seconds regardless of scope size.

### 15.5 MCP Tool: `decay_scope`

The `decay_scope` MCP tool exposes `POST /v1/decay/sweep` to any MCP-aware agent.

```json
{
  "name": "decay_scope",
  "description": "Apply configured decay policies to a Stigmem scope. Retracts or reduces confidence of stale/aged facts per operator-defined DecayPolicy. Use mode='dry_run' to preview what would change without writing. Complement to lint_scope — lint identifies decay candidates; decay_scope acts on them.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to sweep."
      },
      "mode": {
        "type": "string",
        "enum": ["retract", "confidence", "dry_run"],
        "description": "Optional. Override decay mode for this run. Omit to use configured policy modes."
      },
      "policy_id": {
        "type": "string",
        "description": "Optional. Run only the named decay policy."
      }
    },
    "required": ["scope"]
  }
}
```

### 15.6 Cron-Friendly Operation

The decay sweeper is designed for scheduled operation:

```bash
# Run decay sweep on company scope daily at 02:00
0 2 * * * curl -X POST $STIGMEM_URL/v1/decay/sweep \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope": "company"}'
```

The sweep is **idempotent**: running it twice in a row on the same data produces the
same result (the second run sees the retractions written by the first run and finds
no additional facts to retract at the same TTL threshold).

**Cron configuration pattern:**

```
STIGMEM_DECAY_POLICIES=[
  {
    "id": "memory-context-decay",
    "relation": "memory:*",
    "scope": "company",
    "mode": "confidence",
    "half_life_s": 604800,
    "min_confidence": 0.1
  },
  {
    "id": "stale-roadmap-retract",
    "relation": "roadmap:status",
    "scope": "company",
    "mode": "retract",
    "ttl_s": 2592000
  }
]
```

### 15.7 Conformance Test Vectors

`DECAY_VECTORS` are defined in `sdks/stigmem-py/tests/conformance_vectors.py`.

| Vector ID | Mode | Scenario | Expected outcome |
|---|---|---|---|
| `decay-confidence-reduction` | `confidence` | Fact with `half_life_s=3600`; assert 7200 s ago | New fact with `confidence ≈ 0.25` |
| `decay-retraction` | `retract` | Fact older than `ttl_s`; assert was 3601 s ago | New fact with `confidence=0.0`, `source="system:stigmem:decay"` |
| `decay-scope-filter` | `retract` | Stale fact in `public` scope; sweep `company` scope | No facts retracted (scope isolation) |
| `decay-dry-run` | `dry_run` | Fact older than `ttl_s` | `dry_run_would_retract=1`; no new facts in store |
| `decay-exempt` | `retract` | Fact with `relation="stigmem:received_from"` in scope | Fact not retracted (exempt namespace) |

All five vectors MUST pass for conformance.

---

## 16. Synthesis — v0.8 Draft

> **v0.8 status:** Draft. The `synthesize_scope` MCP tool and `POST /v1/synthesis` route
> are specified here. Implementation is the D4 deliverable. Conformance test
> vectors (`SYNTHESIS_VECTORS`) will be finalized with D4 implementation. This section
> will be promoted to normative in v0.9.

The **synthesis** operation produces a **confidence-weighted summary view** of the live
facts in a scope. Where lint reports raw health findings and decay sweeps apply remediation,
synthesis answers the question: *"given everything I know right now, what is the current
state of this scope?"*

Synthesis is designed for agent consumption at context injection time: an agent querying
`synthesize_scope("company")` gets a structured view of the most reliable current
knowledge without needing to manually filter contradictions, expired facts, or low-confidence noise.

### 16.1 SynthesisEntry Shape

```
SynthesisEntry {
  entity:        URI
  relation:      string
  scope:         FactScope
  value:         FactValue
  confidence:    float          // confidence of the winning fact
  hlc:           string         // HLC of the winning fact
  contradicted:  boolean        // true if unresolved contradiction exists for this (entity, relation, scope)
  alt_value:     FactValue?     // populated if contradicted=true: the other live value
  alt_confidence: float?        // populated if contradicted=true
}
```

### 16.2 Synthesis Algorithm

For each `(entity, relation, scope)` triple with at least one live fact (confidence > 0.0, not expired):

1. Apply contradiction resolution order (§3.3): higher confidence wins; equal confidence → higher HLC wins.
2. If an unresolved contradiction exists, set `contradicted=true` and populate `alt_value`/`alt_confidence` with the losing fact's value and confidence.
3. Filter by `min_confidence` (if provided): skip entries where the winning fact's confidence is below the threshold.
4. Include the entry in the response.

Expired facts (`valid_until < now`) and retracted facts (`confidence=0.0`) are excluded unless `include_expired=true` is passed.

### 16.3 Wire Format

#### Request

```
POST /v1/synthesis
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "scope":           FactScope,   // required
  "entity":          URI?,        // optional: restrict to one entity
  "min_confidence":  float?,      // optional: exclude entries below this confidence; default 0.0
  "include_expired": boolean?     // optional: include expired facts in synthesis; default false
}
```

#### Response

```
200 OK
{
  "summary":            SynthesisEntry[],
  "synthesized_at":     string,    // ISO 8601 UTC
  "scope":              FactScope,
  "fact_count":         integer,   // total live facts evaluated
  "contradiction_count": integer,  // number of entries with contradicted=true
  "filtered_count":     integer    // entries excluded by min_confidence filter
}
```

#### Error responses

| HTTP | Condition |
|---|---|
| 400 | `scope` missing or invalid; `min_confidence` out of [0.0, 1.0] range |
| 403 | Caller's key lacks read access to the requested scope |

### 16.4 MCP Tool: `synthesize_scope`

```json
{
  "name": "synthesize_scope",
  "description": "Produce a confidence-weighted summary of current knowledge in a Stigmem scope. Returns the best current value for each (entity, relation) pair, with contradiction flags where multiple live values exist. Ideal for agent context injection — surfaces reliable current state without requiring manual contradiction filtering.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {
        "type": "string",
        "enum": ["local", "team", "company", "public"],
        "description": "The fact scope to synthesize."
      },
      "entity": {
        "type": "string",
        "description": "Optional. Restrict synthesis to facts about a single entity URI."
      },
      "min_confidence": {
        "type": "number",
        "description": "Optional. Exclude entries with confidence below this threshold. Range [0.0, 1.0]. Default 0.0."
      }
    },
    "required": ["scope"]
  }
}
```

### 16.5 Relationship to Lint and Decay

The three Phase 6 operational tools form a pipeline:

| Tool | Question answered | Writes? |
|---|---|---|
| `lint_scope` | "What is wrong?" | No |
| `decay_scope` | "Apply configured remediation" | Yes (retractions/confidence updates) |
| `synthesize_scope` | "What do I currently know?" | No |

The typical agent workflow:
1. Boot: call `synthesize_scope` to get current reliable knowledge for context injection.
2. Background (periodic): call `lint_scope` to identify health issues; optionally call `decay_scope` to apply configured policies.
3. Resolution: call `POST /v1/conflicts/:id/resolve` for contradictions surfaced by lint.

---

*v0.8-draft — §§1–14 promoted to stable. §15 Decay Semantics and §16 Synthesis are draft, pending D4 implementation. §6.7–§6.8 N-node patterns are draft, pending D1 correctness test validation. Open for CTO review before promotion to stable.*
