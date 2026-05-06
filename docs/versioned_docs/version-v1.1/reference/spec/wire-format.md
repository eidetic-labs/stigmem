---
title: §5. Wire Format
sidebar_label: §5 Wire Format
audience: Spec
description: "Stigmem spec section 5 — JSON/HTTP wire format for facts, peers, gardens, trust manifests, and capability tokens."
---

# §5. Wire Format {#section-5}

**Status:** Stable (v1.0; v1.1 §5.21–5.25)

JSON/HTTP wire format for facts, peers, gardens, trust manifests, and capability tokens.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

*§5.1–§5.20 unchanged from v1.0. The following routes are added.*

<details>
<summary>Revisions before v1.1-draft: v0.8-draft, v0.9-draft, v1.0</summary>

**From `stigmem-spec-v0.8-draft.md`:**

This section defines the HTTP endpoints that constitute the Stigmem REST API.
Every operation is expressed as a JSON-over-HTTP request so that any language
with an HTTP client can participate — no SDK is required. Endpoints are grouped
by function: fact CRUD (§5.1–§5.5), federation lifecycle (§5.6–§5.8, §5.11),
conflict management (§5.9–§5.10), and higher-order operations (§5.12–§5.13).

**From `stigmem-spec-v0.9-draft.md`:**

*§5.1–§5.13 unchanged from v0.8.*

**From `stigmem-spec-v1.0.md`:**

*§5.1–§5.13 unchanged from v0.8.*

</details>

### §5.1 Assert a fact {#section-5-1}

Asserting a fact is the primary write operation in Stigmem. The caller supplies
the full `(entity, relation, value, source, confidence, scope)` tuple and the
node stores it as an immutable record, stamping it with a server-generated `id`,
wall-clock `timestamp`, and hybrid logical clock (`hlc`) value. Because facts
are append-only, this endpoint never overwrites an existing record — every call
produces a new row, even if the same tuple was asserted before.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", "hlc": "...", ...fact... }
```

### §5.2 Query facts {#section-5-2}

Querying is the primary read path. Callers filter by any combination of the
fact dimensions — `entity`, `relation`, `source`, `scope` — and the node
returns the matching facts sorted by recency. The response is cursor-paginated
so that large result sets can be consumed incrementally without holding server
resources. By default the query excludes contradicted and expired facts; callers
can opt in to those via the `include_contradicted` and `include_expired` flags
when they need a full audit trail.

```
GET /v1/facts?entity=stigmem://company.example/user/alice&relation=memory:role
→ 200 { "facts": [...], "total": 1, "cursor": null }
```

Query params: `entity`, `relation`, `source`, `scope`, `min_confidence`,
`after`, `include_contradicted`, `include_expired`, `cursor`, `limit`.

### §5.3 Node metadata {#section-5-3}

Every Stigmem node exposes a discovery document at the well-known path so that
clients and peers can learn the node's capabilities before making any
authenticated call. The document advertises the spec version the node
implements, whether authentication is required, whether federation is enabled,
and — when federation is active — the node's public key, supported federation
version, and the concrete endpoint paths for peer management and replication.
This is the first endpoint a federation peer contacts during mutual discovery
(§6.1).

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

### §5.4 Retract a fact {#section-5-4}

To retract a fact, assert a new fact for the same `(entity, relation, scope)` with `confidence=0.0`.
The original fact is never deleted; the retraction is a new immutable entry.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 0.0, "scope": "company" }
→ 201 { ..., "confidence": 0.0 }
```

### §5.5 Get a single fact {#section-5-5}

Retrieve a single fact by its server-assigned UUID. This is useful for
dereferencing a fact ID obtained from another endpoint — for example, when
inspecting the two sides of a conflict (§5.9), following a `fact_refs` link
from a handoff payload (§4.6), or auditing a specific assertion.

```
GET /v1/facts/:id
→ 200 { ...fact... }
→ 404 if not found
```

### §5.6 Register a peer — v0.5 {#section-5-6}

Peer registration is the first step of the federation handshake. The calling
node presents a signed declaration containing its identity (`node_id`),
reachable URL, Ed25519 public key, and the scopes it is willing to share. The
receiving node stores the declaration in `pending_verification` status and then
runs the verification flow described below — fetching the caller's
`/.well-known/stigmem` document to confirm the public key matches. Federation
traffic (§5.8, §5.11) cannot begin until both sides have registered each other
and both declarations reach `active` status.

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

### §5.7 List peers — v0.5 {#section-5-7}

Returns the set of federation peers known to this node. Each entry includes the
peer's status (`active`, `pending_verification`, `rejected`, or `revoked`),
the scopes that peer is allowed to replicate, and the timestamp when the
relationship was established. Operators use this endpoint to audit federation
topology; automated tooling uses it to confirm mutual registration before
triggering replication.

```
GET /v1/federation/peers
→ 200 { "peers": [{ "peer_id": "...", "node_id": "...", "node_url": "...",
                     "status": "active" | "pending_verification" | "rejected" | "revoked",
                     "allowed_scopes": [...], "established_at": "..." }] }
```

### §5.8 Pull replication — v0.5 {#section-5-8}

Pull replication is the default mechanism for synchronising facts between
federated peers. The requesting node supplies an opaque cursor (received from
the previous pull, or `null` to start from the beginning) and a limit. The
responding node returns facts that were created or received after the cursor's
HLC position, filtered to the scopes the requesting peer is authorised to see.
Pull is idempotent: re-requesting the same cursor returns the same facts, and
ingesting a duplicate fact on the receiving side is a silent no-op.

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

### §5.9 List conflicts — v0.5 {#section-5-9}

When two facts for the same `(entity, relation, scope)` tuple arrive with
conflicting values — whether from local assertions or federated replication —
the node records them as a conflict (§7). This endpoint returns the set of
detected conflicts, filterable by status. Each conflict entry carries references
to both original facts so that a human operator or automated resolver can
inspect the competing claims and choose a winner (§5.10).

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

### §5.10 Resolve a conflict — v0.5 {#section-5-10}

Resolving a conflict is an explicit human- or agent-driven decision that picks
a winner, optionally supplies a fresh reconciliation value, and records the
rationale as auditable facts. The caller identifies which of the two competing
facts wins (or passes `null` to reject both in favour of a new value). The node
then asserts the resolution as a new fact, links it to the conflict via a
`stigmem:resolves` meta-fact (§2), and marks the conflict as resolved. Both
original competing facts remain immutable in the store — resolution is additive,
never destructive.

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

### §5.11 Push replication (optional) — v0.5 {#section-5-11}

Push replication is an opt-in, low-latency complement to pull (§5.8). Where
pull requires the consuming node to poll on a schedule, push lets the producing
node forward facts to a peer as soon as they are committed. This is useful for
time-sensitive federation scenarios — for example, when an agent on node A
asserts a fact that a workflow on node B needs within seconds. Push is guarded
by a feature flag (`STIGMEM_FEDERATION_PUSH_ENABLED`, default `false`) because
it adds outbound network traffic and requires the receiving node to expose an
ingestion endpoint. Nodes that advertise a non-null
`federation_endpoints.push` MUST accept:

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

### §5.12 Lint — v0.7 Normative {#section-5-12}

The lint endpoint runs a configurable set of data-quality checks against a
scope and returns machine-readable findings. It is the diagnostic counterpart
to the decay sweeper (§15): lint identifies problems (contradictions, stale
facts, low-confidence assertions); decay acts on them. The `checks` array lets
the caller select which analyses to run so that expensive checks can be skipped
in latency-sensitive contexts. See §14 for the full finding schema and check
catalogue.

```
POST /v1/lint
Authorization: Bearer <api-key>
{ "scope": "company", "checks": ["contradiction", "stale"] }
→ 200 { "findings": [...], "checked_at": "...", "scope": "company",
         "checks_run": ["contradiction","stale"], "fact_count": 142 }
```

### §5.13 Synthesize scope — v0.8 Draft {#section-5-13}

Synthesis produces a confidence-weighted summary of everything a scope knows
about a given entity (or the entire scope when no entity filter is supplied).
Where a raw query (§5.2) returns every historical assertion, synthesis collapses
the timeline: for each `(entity, relation)` pair it surfaces the single
highest-confidence live value, flags active contradictions, and reports the
total fact count. This makes synthesis the go-to read path when an agent needs
a consolidated world-view rather than a change log. See §16 for the full
summary-item schema and contradiction-handling rules.

```
POST /v1/synthesis
Authorization: Bearer <api-key>
{ "scope": "company", "entity": "<optional-uri>", "min_confidence": 0.5 }
→ 200 { "summary": [...], "synthesized_at": "...", "scope": "company",
         "fact_count": 142, "contradiction_count": 3 }
```

---

### §5.14 Create a garden {#section-5-14}

```
POST /v1/gardens
Authorization: Bearer <api-key with write permission>
{
  "slug":        "project-atlas",          // URL-safe identifier; unique within the node
  "name":        "Project Atlas",          // display name
  "scope":       "company",               // facts in this garden must have this scope
  "description": "Atlas project memory."  // optional
}
→ 201 {
    "id":          "<uuid>",
    "garden_id":   "stigmem://node.example.com/garden/project-atlas",
    "slug":        "project-atlas",
    "name":        "Project Atlas",
    "scope":       "company",
    "description": "Atlas project memory.",
    "created_by":  "stigmem://node.example.com/agent/cto",
    "created_at":  "2026-05-03T00:00:00Z",
    "members": [{
      "entity_uri": "stigmem://node.example.com/agent/cto",
      "role":       "admin",
      "added_by":   "stigmem://node.example.com/agent/cto",
      "added_at":   "2026-05-03T00:00:00Z"
    }]
  }
→ 409 if slug already exists
```

The creating principal is automatically added as `admin`.

**Slug rules:** Must match `^[a-z0-9][a-z0-9\-]{0,62}$`. Stored and matched case-insensitively.

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.14 Create a garden — v0.9

```
POST /v1/gardens
Authorization: Bearer <api-key with write permission>
{
  "slug":        "project-atlas",          // URL-safe identifier; unique within the node
  "name":        "Project Atlas",          // display name
  "scope":       "company",               // facts in this garden must have this scope
  "description": "Atlas project memory."  // optional
}
→ 201 {
    "id":          "<uuid>",
    "garden_id":   "stigmem://node.example.com/garden/project-atlas",
    "slug":        "project-atlas",
    "name":        "Project Atlas",
    "scope":       "company",
    "description": "Atlas project memory.",
    "created_by":  "stigmem://node.example.com/agent/cto",
    "created_at":  "2026-05-03T00:00:00Z",
    "members": [{
      "entity_uri": "stigmem://node.example.com/agent/cto",
      "role":       "admin",
      "added_by":   "stigmem://node.example.com/agent/cto",
      "added_at":   "2026-05-03T00:00:00Z"
    }]
  }
→ 409 if slug already exists
```

The creating principal is automatically added as `admin`.

**Slug rules:** Must match `^[a-z0-9][a-z0-9\-]{0,62}$`. Stored and matched case-insensitively.

</details>

### §5.15 List gardens {#section-5-15}

```
GET /v1/gardens
Authorization: Bearer <api-key>
→ 200 { "gardens": [ ...GardenRecord... ] }
```

Returns only gardens where the caller holds any role (admin, writer, or reader). Admins of the node (callers with `write` permission) see all gardens.

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.15 List gardens — v0.9

```
GET /v1/gardens
Authorization: Bearer <api-key>
→ 200 { "gardens": [ ...GardenRecord... ] }
```

Returns only gardens where the caller holds any role (admin, writer, or reader). Admins of the node (callers with `write` permission) see all gardens.

</details>

### §5.16 Get a garden {#section-5-16}

```
GET /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 200 { ...GardenRecord with members... }
→ 403 if caller not a member
→ 404 if not found
```

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.16 Get a garden — v0.9

```
GET /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 200 { ...GardenRecord with members... }
→ 403 if caller not a member
→ 404 if not found
```

</details>

### §5.17 Delete a garden {#section-5-17}

```
DELETE /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 204
→ 403 if caller is not garden admin
→ 404 if not found
```

Deleting a garden does NOT delete its associated facts. The `garden_id` field on orphaned facts becomes a dangling reference. Nodes SHOULD surface these in lint output (§14).

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.17 Delete a garden — v0.9

```
DELETE /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 204
→ 403 if caller is not garden admin
→ 404 if not found
```

Deleting a garden does NOT delete its associated facts. The `garden_id` field on orphaned facts becomes a dangling reference. Nodes SHOULD surface these in lint output (§14).

</details>

### §5.18 Garden membership {#section-5-18}

**Add member:**

```
POST /v1/gardens/:garden_id_or_slug/members
Authorization: Bearer <api-key> (must be garden admin)
{
  "entity_uri": "stigmem://node.example.com/user/alice",
  "role":       "writer"   // "admin" | "writer" | "reader"
}
→ 201 { ...GardenMemberRecord... }
→ 403 if caller is not garden admin
→ 404 if garden not found
→ 409 if entity already a member (use PATCH to change role)
```

**Update member role:**

```
PATCH /v1/gardens/:garden_id_or_slug/members/:entity_uri
Authorization: Bearer <api-key> (must be garden admin)
{ "role": "reader" }
→ 200 { ...GardenMemberRecord... }
→ 403 if caller is not garden admin or is demoting themselves (must retain at least one admin)
```

**Remove member:**

```
DELETE /v1/gardens/:garden_id_or_slug/members/:entity_uri
Authorization: Bearer <api-key> (must be garden admin)
→ 204
→ 403 if caller would remove the last admin
```

**List members:**

```
GET /v1/gardens/:garden_id_or_slug/members
Authorization: Bearer <api-key> (must be any member)
→ 200 { "members": [ ...GardenMemberRecord... ] }
```

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.18 Garden membership — v0.9

**Add member:**

```
POST /v1/gardens/:garden_id_or_slug/members
Authorization: Bearer <api-key> (must be garden admin)
{
  "entity_uri": "stigmem://node.example.com/user/alice",
  "role":       "writer"   // "admin" | "writer" | "reader"
}
→ 201 { ...GardenMemberRecord... }
→ 403 if caller is not garden admin
→ 404 if garden not found
→ 409 if entity already a member (use PATCH to change role)
```

**Update member role:**

```
PATCH /v1/gardens/:garden_id_or_slug/members/:entity_uri
Authorization: Bearer <api-key> (must be garden admin)
{ "role": "reader" }
→ 200 { ...GardenMemberRecord... }
→ 403 if caller is not garden admin or is demoting themselves (must retain at least one admin)
```

**Remove member:**

```
DELETE /v1/gardens/:garden_id_or_slug/members/:entity_uri
Authorization: Bearer <api-key> (must be garden admin)
→ 204
→ 403 if caller would remove the last admin
```

**List members:**

```
GET /v1/gardens/:garden_id_or_slug/members
Authorization: Bearer <api-key> (must be any member)
→ 200 { "members": [ ...GardenMemberRecord... ] }
```

</details>

### §5.19 Assert a fact into a garden {#section-5-19}

Facts are associated with a garden by including `garden_id` in the assert request:

```
POST /v1/facts
Authorization: Bearer <api-key with write permission>
{
  "entity":    "stigmem://node.example.com/project/atlas",
  "relation":  "roadmap:status",
  "value":     { "type": "string", "v": "in-flight" },
  "source":    "stigmem://node.example.com/agent/cto",
  "scope":     "company",
  "garden_id": "stigmem://node.example.com/garden/project-atlas"
}
→ 201 { ...FactRecord..., "garden_id": "...", "attested": true }
→ 403 if caller is not a writer or admin in the garden
→ 403 if scope does not match the garden's declared scope
→ 404 if garden not found
```

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.19 Assert a fact into a garden — v0.9

Facts are associated with a garden by including `garden_id` in the assert request:

```
POST /v1/facts
Authorization: Bearer <api-key with write permission>
{
  "entity":    "stigmem://node.example.com/project/atlas",
  "relation":  "roadmap:status",
  "value":     { "type": "string", "v": "in-flight" },
  "source":    "stigmem://node.example.com/agent/cto",
  "scope":     "company",
  "garden_id": "stigmem://node.example.com/garden/project-atlas"
}
→ 201 { ...FactRecord..., "garden_id": "...", "attested": true }
→ 403 if caller is not a writer or admin in the garden
→ 403 if scope does not match the garden's declared scope
→ 404 if garden not found
```

</details>

### §5.20 Query facts with garden filter {#section-5-20}

```
GET /v1/facts?garden_id=stigmem://node.example.com/garden/project-atlas
→ 200 { "facts": [...], "total": N, "cursor": "..." }
→ 403 if caller is not a member of the garden
```

The `garden_id` query parameter is additive with other filters (`entity`, `relation`, `scope`, etc.). Garden ACL is enforced: non-members get 403, not an empty result, to prevent membership enumeration.

---

<details>
<summary>Revisions before v1.0: v0.9-draft</summary>

**From `stigmem-spec-v0.9-draft.md`:**

### 5.20 Query facts with garden filter — v0.9

```
GET /v1/facts?garden_id=stigmem://node.example.com/garden/project-atlas
→ 200 { "facts": [...], "total": N, "cursor": "..." }
→ 403 if caller is not a member of the garden
```

The `garden_id` query parameter is additive with other filters (`entity`, `relation`, `scope`, etc.). Garden ACL is enforced: non-members get 403, not an empty result, to prevent membership enumeration.

---

</details>

### §5.21 Publish an org manifest {#section-5-21}

Publishing an org manifest is the bootstrap step for the federation trust model
(§19). The admin uploads a self-signed manifest that declares the node's public
key and the entity URIs it speaks for. The node verifies the signature against
the embedded public key, stores the manifest, and (if configured) submits it to
the transparency log (§19.2) for independent auditability. This endpoint
replaces manual key exchange — peers can now resolve the manifest dynamically
via §5.22.

```
PUT /v1/federation/manifest
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "manifest_version": 1,
  "entity_uri":       "stigmem://company.example",      // root entity URI for this node/org
  "public_key":       "<base64url Ed25519 public key>", // active signing key
  "key_id":           "<sha256 fingerprint of public key>",
  "entities":         [                                 // entity URIs this manifest is authoritative for
    "stigmem://company.example/agent/assistant",
    "stigmem://company.example/adapter/hook"
  ],
  "rotation_events":  [],   // see §19.1.4; empty on first publish
  "issued_at":        "2026-05-04T00:00:00Z",
  "expires_at":       "2027-05-04T00:00:00Z",
  "signature":        "<base64url Ed25519 sig over canonical JSON>"
}
→ 200 { "manifest_id": "...", "log_entry_url": "..." }
→ 400 if signature verification fails or required fields missing
→ 403 if caller not admin
```

### §5.22 Resolve an org manifest {#section-5-22}

Peers call this endpoint during the federation handshake to retrieve the
manifest for a given entity URI. The response contains the full manifest object
including the public key, entity list, rotation events, and signature — giving
the peer everything it needs to verify capability tokens (§19.3) issued by
this node.

```
GET /v1/federation/manifest/:entity_uri_encoded
→ 200 { ...manifest object... }
→ 404 if no manifest found for entity_uri
```

### §5.23 Issue a capability token {#section-5-23}

Capability tokens (§19.3) are short-lived, scoped credentials that replace
static API keys for inter-node operations. This endpoint mints a signed token
granting the named `subject` a specific `verb` on a specific `object` (scope or
garden URI). The token is self-contained — the receiving peer verifies it using
the issuer's manifest public key without calling back to the issuing node.

```
POST /v1/federation/capability-tokens
Authorization: Bearer <admin api-key>

{
  "issuer":   "stigmem://company.example",
  "subject":  "stigmem://company.example/agent/assistant",
  "verb":     "write",
  "object":   "stigmem://partner.example/scope/shared",
  "expiry":   "2026-06-01T00:00:00Z",
  "nonce":    "<32-byte hex random>"
}
→ 201 { "token": "<base64url-encoded signed JWT-like structure>", "token_id": "..." }
→ 403 if caller not admin
```

### §5.24 Revoke a capability token {#section-5-24}

Revocation invalidates a previously-issued token before its natural expiry. The
revocation event is recorded in the local revocation list and submitted to the
transparency log (§19.2.5) so that peers can independently verify the
revocation without trusting the issuing node's runtime state.

```
POST /v1/federation/capability-tokens/:token_id/revoke
Authorization: Bearer <admin api-key>

{} // empty body; revocation event is logged to transparency log
→ 204
→ 404 if token_id not found
```

### §5.25 Quarantine garden operations {#section-5-25}

Facts that arrive from untrusted or low-scoring federation sources land in a
quarantine garden (§19.7) rather than the target scope. These operations let a
moderator review quarantined facts and either promote them to the intended
destination or reject them permanently. Both actions are auditable — the
`promoted_by` / `rejected_by` field records who made the decision.

```
// Promote a fact from quarantine to a target garden
POST /v1/gardens/:quarantine_garden_id/promote
Authorization: Bearer <api-key> (must hold quarantine:moderator role)

{
  "fact_id":           "<uuid>",
  "target_garden_id":  "<uuid or null for no-garden>",
  "reason":            "Verified provenance."
}
→ 200 { "fact_id": "...", "promoted_at": "...", "promoted_by": "..." }
→ 403 if caller lacks quarantine:moderator
→ 404 if fact_id not found in quarantine garden
→ 409 if fact already promoted or rejected

// Reject a quarantined fact
POST /v1/gardens/:quarantine_garden_id/reject
Authorization: Bearer <api-key> (must hold quarantine:moderator role)

{
  "fact_id": "<uuid>",
  "reason":  "Failed source attestation; untrusted origin."
}
→ 200 { "fact_id": "...", "rejected_at": "...", "rejected_by": "..." }
→ 403 if caller lacks quarantine:moderator
→ 404 if fact_id not found in quarantine garden
→ 409 if fact already promoted or rejected
```

---
