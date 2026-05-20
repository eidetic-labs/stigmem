---
title: Spec-03 HTTP API
sidebar_label: Spec-03 HTTP API
audience: Spec
description: "Spec-03-HTTP-API rendered entry point — JSON/HTTP API surface and route contracts."
---

# Spec-03-HTTP-API \{#section-5\}

<p className="stigmem-meta"><span>14 min read</span><span>Spec contributor · SDK author · Adapter author</span><span>25 HTTP routes</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-03-HTTP-API`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/03-http-api.md).
JSON/HTTP wire format for facts, peers, gardens, trust manifests,
and capability tokens — every operation is JSON-over-HTTP so any
language with an HTTP client can participate. No SDK required.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Legacy §5 anchors are retained for existing links while the
maintained route contract lives in `Spec-03-HTTP-API`.
:::

## Endpoint groups

<div className="stigmem-fields">

<div>
<dt>Group</dt>
<dt><span className="stigmem-fields__type">Sections</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt>Fact CRUD</dt>
<dt><span className="stigmem-fields__type">§5.1–§5.5</span></dt>
<dd>Assert, query, retract, point lookup, node metadata.</dd>
</div>

<div>
<dt>Federation lifecycle</dt>
<dt><span className="stigmem-fields__type">§5.6–§5.8, §5.11</span></dt>
<dd>Peer register, list, pull, push.</dd>
</div>

<div>
<dt>Conflict management</dt>
<dt><span className="stigmem-fields__type">§5.9–§5.10</span></dt>
<dd>List + resolve.</dd>
</div>

<div>
<dt>Higher-order operations</dt>
<dt><span className="stigmem-fields__type">§5.12–§5.13</span></dt>
<dd>Lint + synthesis.</dd>
</div>

<div>
<dt>Gardens</dt>
<dt><span className="stigmem-fields__type">§5.14–§5.20</span></dt>
<dd>CRUD, membership, garden-filtered assert/query.</dd>
</div>

<div>
<dt>Federation trust</dt>
<dt><span className="stigmem-fields__type">§5.21–§5.25</span></dt>
<dd>Manifests, capability tokens, quarantine.</dd>
</div>

</div>

<details>
<summary>Revisions before pre-reset draft: the pre-reset spec-draft, pre-reset draft, v1.0</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

This section defines the HTTP endpoints that constitute the Stigmem REST API.
Every operation is expressed as a JSON-over-HTTP request so that any language
with an HTTP client can participate — no SDK is required. Endpoints are grouped
by function: fact CRUD (§5.1–§5.5), federation lifecycle (§5.6–§5.8, §5.11),
conflict management (§5.9–§5.10), and higher-order operations (§5.12–§5.13).

**From `stigmem-spec-pre-reset draft.md`:**

*§5.1–§5.13 unchanged from the pre-reset spec.*

**From `stigmem-spec-v1.0.md`:**

*§5.1–§5.13 unchanged from the pre-reset spec.*

</details>

### §5.1 Assert a fact \{#section-5-1\}

The primary write operation. Caller supplies the full
`(entity, relation, value, source, confidence, scope)` tuple; the
node stores it as an immutable record, stamping it with a
server-generated `id`, wall-clock `timestamp`, and HLC value.

<div className="stigmem-keypoint">

**Facts are append-only.**

This endpoint never overwrites an existing record — every call
produces a new row, even if the same tuple was asserted before.

</div>

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 1.0, "scope": "company" }
→ 201 { "id": "<uuid>", "timestamp": "...", "hlc": "...", ...fact... }
```

### §5.2 Query facts \{#section-5-2\}

The primary read path. Filter by any combination of `entity`,
`relation`, `source`, `scope`; the node returns matching facts
sorted by recency. Cursor-paginated for large result sets. By
default excludes contradicted and expired facts.

```
GET /v1/facts?entity=stigmem://company.example/user/alice&relation=memory:role
→ 200 { "facts": [...], "total": 1, "cursor": null }
```

**Query params:** `entity`, `relation`, `source`, `scope`,
`min_confidence`, `after`, `include_contradicted`, `include_expired`,
`cursor`, `limit`.

### §5.3 Node metadata \{#section-5-3\}

Every node exposes a discovery document at the well-known path so
clients and peers can learn the node's capabilities before any
authenticated call. This is the first endpoint a federation peer
contacts during mutual discovery (§6.1).

```
GET /.well-known/stigmem
→ 200 {
    "version":            "0.8",
    "node_id":            URI,
    "node_url":           string,
    "auth":               "none" | "required",
    "federation":         "disabled" | "enabled",
    "federation_pubkey":  string,   // pre-reset: base64url Ed25519 public key; omit if federation disabled
    "federation_version": string,   // pre-reset: semver range this node speaks, e.g. "0.8"
    "federation_endpoints": {       // pre-reset: advertised federation routes
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

### §5.4 Retract a fact \{#section-5-4\}

To retract a fact, assert a new fact for the same
`(entity, relation, scope)` with `confidence=0.0`. The original
fact is never deleted; the retraction is a new immutable entry.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value": { "type": "string", "v": "CEO" },
  "source": "stigmem://company.example/agent/assistant", "confidence": 0.0, "scope": "company" }
→ 201 { ..., "confidence": 0.0 }
```

### §5.5 Get a single fact \{#section-5-5\}

Retrieve a single fact by its server-assigned UUID. Useful for
dereferencing fact IDs from other endpoints — inspecting conflict
sides (§5.9), following `fact_refs` from a handoff payload (§4.6),
or auditing a specific assertion.

```
GET /v1/facts/:id
→ 200 { ...fact... }
→ 404 if not found
```

### §5.6 Register a peer — pre-reset \{#section-5-6\}

First step of the federation handshake. The calling node presents
a signed declaration containing its identity (`node_id`), reachable
URL, Ed25519 public key, and shared scopes.

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

<ol className="stigmem-steps">
<li>Receiving node fetches <code>{`{node_url}`}/.well-known/stigmem</code> to retrieve the peer's <code>federation_pubkey</code>.</li>
<li>Node verifies <code>declaration_sig</code> over the canonical JSON payload.</li>
<li>If valid, peer status transitions to <code>"active"</code>. If <code>federation_pubkey</code> mismatches the one at <code>/.well-known/stigmem</code>, status becomes <code>"rejected"</code>.</li>
<li>Mutual federation requires both sides to register each other. A node MAY auto-register a reciprocal peer declaration; it MUST NOT begin replicating until both sides are <code>"active"</code>.</li>
</ol>

### §5.7 List peers — pre-reset \{#section-5-7\}

Returns the set of federation peers known to this node. Operators
audit federation topology; tooling confirms mutual registration
before triggering replication.

```
GET /v1/federation/peers
→ 200 { "peers": [{ "peer_id": "...", "node_id": "...", "node_url": "...",
                     "status": "active" | "pending_verification" | "rejected" | "revoked",
                     "allowed_scopes": [...], "established_at": "..." }] }
```

### §5.8 Pull replication — pre-reset \{#section-5-8\}

Default mechanism for synchronising facts between federated peers.
Opaque cursor + limit; response returns facts created or received
after the cursor's HLC position, filtered to authorised scopes.

```
GET /v1/federation/facts?scope=public&cursor=<cursor>&limit=100
Authorization: Bearer <peer-token>
→ 200 {
    "facts":      [...],          // facts since cursor; max limit=500
    "cursor":     "<opaque>",     // new cursor; persist this for next call
    "has_more":   true | false
  }
```

<div className="stigmem-grid">

<div><h4>Cursor semantics</h4><p>An opaque string encoding the HLC of the last fact returned. Stable: re-requesting the same cursor returns the same facts (idempotent). <code>null</code> requests from the beginning.</p></div>
<div><h4>Scope filtering</h4><p>The peer token's <code>scopes</code> claim restricts which scopes can be returned. Nodes MUST NOT return facts outside the intersection of <code>allowed_scopes</code> in the PeerDeclaration and the token's <code>scopes</code> claim.</p></div>
<div><h4>Idempotency</h4><p>Nodes MUST deduplicate by fact <code>id</code>. Re-ingesting a fact that already exists locally is a silent no-op.</p></div>

</div>

### §5.9 List conflicts — pre-reset \{#section-5-9\}

When two facts for the same `(entity, relation, scope)` tuple
arrive with conflicting values (whether local or federated), the
node records them as a conflict (§7). Filterable by status; each
entry carries references to both original facts.

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

### §5.10 Resolve a conflict — pre-reset \{#section-5-10\}

Explicit human- or agent-driven decision that picks a winner,
optionally supplies a fresh reconciliation value, and records the
rationale as auditable facts.

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

<ol className="stigmem-steps">
<li>A new fact for <code>(entity, relation, scope)</code> with the winning or new value and <code>confidence=1.0</code>.</li>
<li>A <code>stigmem:resolves</code> meta-fact: <code>(entity=&lt;resolution-fact-id&gt;, relation="stigmem:resolves", value={`{type:"ref", v:"<conflict_id>"}`}, source=&lt;caller's entity_uri&gt;, ...)</code>.</li>
<li>Updates the conflict's <code>stigmem:conflict:status</code> to <code>"resolved"</code>.</li>
</ol>

Both original conflicting facts remain immutable in the store.

### §5.11 Push replication (optional) — pre-reset \{#section-5-11\}

Opt-in, low-latency complement to pull. The producing node forwards
facts to a peer as soon as they are committed. Guarded by
`STIGMEM_FEDERATION_PUSH_ENABLED` (default `false`).

```
POST /v1/federation/facts/push
Authorization: Bearer <peer-token>
{ "facts": [...],   // array of FactObject as they would appear in GET /v1/facts responses
  "sender_hlc": "<hlc>" }
→ 202 { "accepted": <int>, "rejected": <int>, "errors": [...] }
```

Push is opt-in. Nodes that do not support push SHOULD return 405.
Implementations SHOULD prefer pull; push is provided for
low-latency delivery behind a feature flag.

### §5.12 Lint — pre-reset normative \{#section-5-12\}

The lint endpoint runs a configurable set of data-quality checks
against a scope and returns machine-readable findings. Diagnostic
counterpart to the decay sweeper (§15). See §14 for the full
finding schema and check catalogue.

```
POST /v1/lint
Authorization: Bearer <api-key>
{ "scope": "company", "checks": ["contradiction", "stale"] }
→ 200 { "findings": [...], "checked_at": "...", "scope": "company",
         "checks_run": ["contradiction","stale"], "fact_count": 142 }
```

### §5.13 Synthesize scope — pre-reset draft \{#section-5-13\}

Produces a confidence-weighted summary of everything a scope knows
about a given entity (or the entire scope when no entity filter is
supplied). Collapses the timeline: for each `(entity, relation)`
pair, surfaces the single highest-confidence live value, flags
active contradictions, reports total fact count.

```
POST /v1/synthesis
Authorization: Bearer <api-key>
{ "scope": "company", "entity": "<optional-uri>", "min_confidence": 0.5 }
→ 200 { "summary": [...], "synthesized_at": "...", "scope": "company",
         "fact_count": 142, "contradiction_count": 3 }
```

### §5.14 Create a garden \{#section-5-14\}

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

**Slug rules:** Must match `^[a-z0-9][a-z0-9\-]{0,62}$`. Stored and
matched case-insensitively.

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.14 Create a garden — the pre-reset spec

```
POST /v1/gardens
Authorization: Bearer <api-key with write permission>
{
  "slug":        "project-atlas",
  "name":        "Project Atlas",
  "scope":       "company",
  "description": "Atlas project memory."
}
→ 201 { ...GardenRecord with members... }
→ 409 if slug already exists
```

The creating principal is automatically added as `admin`. **Slug rules:** Must match `^[a-z0-9][a-z0-9\-]{0,62}$`. Stored and matched case-insensitively.

</details>

### §5.15 List gardens \{#section-5-15\}

```
GET /v1/gardens
Authorization: Bearer <api-key>
→ 200 { "gardens": [ ...GardenRecord... ] }
```

Returns only gardens where the caller holds any role (admin,
writer, or reader). Admins of the node (callers with `write`
permission) see all gardens.

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.15 List gardens — the pre-reset spec

```
GET /v1/gardens
Authorization: Bearer <api-key>
→ 200 { "gardens": [ ...GardenRecord... ] }
```

Returns only gardens where the caller holds any role (admin, writer, or reader). Admins of the node (callers with `write` permission) see all gardens.

</details>

### §5.16 Get a garden \{#section-5-16\}

```
GET /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 200 { ...GardenRecord with members... }
→ 403 if caller not a member
→ 404 if not found
```

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.16 Get a garden — the pre-reset spec

```
GET /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 200 { ...GardenRecord with members... }
→ 403 if caller not a member
→ 404 if not found
```

</details>

### §5.17 Delete a garden \{#section-5-17\}

```
DELETE /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 204
→ 403 if caller is not garden admin
→ 404 if not found
```

<div className="stigmem-keypoint">

**Deleting a garden does NOT delete its associated facts.**

The <code>garden_id</code> field on orphaned facts becomes a
dangling reference. Nodes SHOULD surface these in lint output (§14).

</div>

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.17 Delete a garden — the pre-reset spec

```
DELETE /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 204
→ 403 if caller is not garden admin
→ 404 if not found
```

Deleting a garden does NOT delete its associated facts. The `garden_id` field on orphaned facts becomes a dangling reference. Nodes SHOULD surface these in lint output (§14).

</details>

### §5.18 Garden membership \{#section-5-18\}

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
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.18 Garden membership — the pre-reset spec

(Same as above — identical request/response shapes for add/update/remove/list.)

</details>

### §5.19 Assert a fact into a garden \{#section-5-19\}

Facts are associated with a garden by including `garden_id` in the
assert request.

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
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.19 Assert a fact into a garden — the pre-reset spec

(Same shape as above.)

</details>

### §5.20 Query facts with garden filter \{#section-5-20\}

```
GET /v1/facts?garden_id=stigmem://node.example.com/garden/project-atlas
→ 200 { "facts": [...], "total": N, "cursor": "..." }
→ 403 if caller is not a member of the garden
```

<div className="stigmem-keypoint">

**Garden ACL is enforced.**

The <code>garden_id</code> query parameter is additive with other
filters (<code>entity</code>, <code>relation</code>, <code>scope</code>,
etc.). Non-members get 403, not an empty result, to prevent
membership enumeration.

</div>

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 5.20 Query facts with garden filter — the pre-reset spec

(Same shape as above; garden ACL is enforced — non-members get 403 not empty result.)

</details>

### §5.21 Publish an org manifest \{#section-5-21\}

Bootstrap step for the federation trust model (§19). The admin
uploads a self-signed manifest that declares the node's public key
and the entity URIs it speaks for. The node verifies the signature
against the embedded public key, stores the manifest, and (if
configured) submits it to the transparency log (§19.2).

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

### §5.22 Resolve an org manifest \{#section-5-22\}

Peers call this endpoint during the federation handshake to
retrieve the manifest for a given entity URI. The response contains
the full manifest object — giving the peer everything it needs to
verify capability tokens (§19.3) issued by this node.

```
GET /v1/federation/manifest/:entity_uri_encoded
→ 200 { ...manifest object... }
→ 404 if no manifest found for entity_uri
```

### §5.23 Issue a capability token \{#section-5-23\}

Capability tokens (§19.3) are short-lived, scoped credentials that
replace static API keys for inter-node operations. This endpoint
mints a signed token granting the named `subject` a specific `verb`
on a specific `object`. Self-contained — the receiving peer
verifies it using the issuer's manifest public key without calling
back.

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

### §5.24 Revoke a capability token \{#section-5-24\}

Revocation invalidates a previously-issued token before its natural
expiry. Recorded in the local revocation list and submitted to the
transparency log (§19.2.5) so peers can independently verify the
revocation without trusting the issuing node's runtime state.

```
POST /v1/federation/capability-tokens/:token_id/revoke
Authorization: Bearer <admin api-key>

{} // empty body; revocation event is logged to transparency log
→ 204
→ 404 if token_id not found
```

### §5.25 Quarantine garden operations \{#section-5-25\}

Facts that arrive from untrusted or low-scoring federation sources
land in a quarantine garden (§19.7) rather than the target scope.
These operations let a moderator review quarantined facts and
either promote them or reject them permanently. Both actions are
auditable.

**Promote a fact from quarantine to a target garden:**

```
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
```

**Reject a quarantined fact:**

```
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
