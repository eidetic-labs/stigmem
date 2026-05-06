# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v1.0

**Status:** v1.0 — Stable. §1–§18 normative.
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v1.0 (2026-05-03): Promoted §17 Memory Garden and §18 Source Attestation from draft to normative. All sections stable.
- v0.9 (Phase 7 — substrate): §17 Memory Garden — named, ACL'd partition above scope with admin/writer/reader role model and entity membership. §18 Source Attestation — `entity_uri` bound to API key at creation (immutable); enforcement at write time via enforce/warn/off modes; auto-fill source from key's entity_uri when omitted; delegation via `allowed_source_entities`; key management API (`POST/GET/PATCH/DELETE /v1/auth/keys`); attestation audit log; migration 005 (api_keys, attestation_audit). §5.14–§5.20 garden + attestation wire routes. §2 `garden_id` and `attested` fields on FactRecord. §3.5 source attestation rules + updated Identity shape with `allowed_source_entities`. §9 `garden:` prefix reserved. §10 migrations 004–005.
- v0.8 (Phase 6 — public beta): §15 Decay Semantics; §16 Synthesis; §6.7–§6.8 N-node federation backpressure and scope propagation invariants. §§1–§14 promoted to stable.
- [Prior changelog in stigmem-spec-v0.8-draft.md]

> **Reading guide:** §1–§16 are unchanged from v0.8. §17–§18 are fully normative in v1.0. §2, §3.5, §5, §7, §8, §9, §10 carry v0.9 additions; all other content in those sections is stable from v0.8.

---

## 2. Atomic Fact Shape (v0.9 additions)

*Stable sections §2.1–§2.6 unchanged from v0.8. The following fields are added to the fact record.*

### 2.7 Garden Field

An optional `garden_id` field on a fact associates it with a Memory Garden (§17).

```
FactRecord (v0.9 extension):
  ...all v0.8 fields...
  garden_id: URI | null    // stigmem://authority/garden/{slug}; null = no garden
  attested:  boolean | null  // source attestation result (§18); null = not applicable
```

**`garden_id` invariant:** When `garden_id` is set:
1. The garden MUST exist on the local node.
2. The writing principal MUST hold `writer` or `admin` role in the garden.
3. The fact's `scope` MUST equal the garden's declared `scope`.
4. Garden-tagged facts are subject to garden ACL at read time (§17.3).

**`garden_id` on federation:** Garden membership is node-local. Facts with `garden_id` set MUST NOT be replicated to peers. Nodes MUST silently drop `garden_id` from federated facts they receive (so cross-node garden membership doesn't accidentally leak or create ghost associations).

**`attested` semantics:**

| Value  | Meaning |
|--------|---------|
| `true`  | Node verified that `source` equals the caller's authenticated `entity_uri`. |
| `false` | Source/identity mismatch detected; fact accepted in `warn` or `off` mode. |
| `null`  | Attestation not applicable: auth disabled, federation ingest, or system fact. |

---

## 3. Fact Semantics — v0.9 additions to §3.5

*§3.1–§3.4 unchanged. §3.5 is extended below.*

### 3.5 Identity and Auth — Source Attestation

*Prior content (API-key model, per-scope key restrictions, federation peer tokens) unchanged from v0.8.*

#### Source attestation

**Problem:** In v0.8, the `source` URI in a fact's request body is caller-declared. An authenticated principal can claim to be anyone by writing `"source": "stigmem://authority/user/someone-else"`. This breaks provenance guarantees — a fact's `source` field cannot be trusted as the actual write origin without an out-of-band verification.

**Solution (v0.9):** Source attestation binds the declared `source` to the caller's `entity_uri` registered on their API key at write time (§18.7). The `entity_uri` is immutable after key creation. The binding is enforced by the node in one of three modes:

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

| Mode      | Behavior |
|-----------|---------|
| `enforce` | Node rejects any `POST /v1/facts` where `source ∉ {identity.entity_uri} ∪ identity.allowed_source_entities`. Returns HTTP 403 `source_attestation_failed`. |
| `warn`    | Node accepts the fact; logs a warning; sets `attested: false` on the stored record. |
| `off`     | No attestation check. `attested: null` on all records. |

**Default mode:** `warn`. Single-operator deployments that trust all their callers do not need to change the default. Production multi-tenant deployments SHOULD set `enforce`.

**Node configuration:** `STIGMEM_SOURCE_ATTESTATION_MODE=enforce|warn|off`. Nodes expose the active mode at `/.well-known/stigmem` as `"source_attestation": "enforce" | "warn" | "off"`.

**Auth-disabled mode:** When `STIGMEM_AUTH_REQUIRED=false`, the caller identity is anonymous. Attestation cannot be performed; `attested` is `null` for all writes in this mode.

**Service agents writing on behalf of others:** Use `allowed_source_entities` (§18.9) to delegate specific source claims to an adapter key. This is the explicit delegation path — the v0.9 model does not support implicit delegation.

**Federated facts:** Source attestation is NOT re-applied to facts received via federation. The original `source` is preserved per §3.1. Federated facts MUST have `attested: null` on ingest.

---

## 5. Wire Format — v0.9 additions

*§5.1–§5.13 unchanged from v0.8.*

### 5.14 Create a garden

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

### 5.15 List gardens

```
GET /v1/gardens
Authorization: Bearer <api-key>
→ 200 { "gardens": [ ...GardenRecord... ] }
```

Returns only gardens where the caller holds any role (admin, writer, or reader). Admins of the node (callers with `write` permission) see all gardens.

### 5.16 Get a garden

```
GET /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 200 { ...GardenRecord with members... }
→ 403 if caller not a member
→ 404 if not found
```

### 5.17 Delete a garden

```
DELETE /v1/gardens/:garden_id_or_slug
Authorization: Bearer <api-key>
→ 204
→ 403 if caller is not garden admin
→ 404 if not found
```

Deleting a garden does NOT delete its associated facts. The `garden_id` field on orphaned facts becomes a dangling reference. Nodes SHOULD surface these in lint output (§14).

### 5.18 Garden membership

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

### 5.19 Assert a fact into a garden

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

### 5.20 Query facts with garden filter

```
GET /v1/facts?garden_id=stigmem://node.example.com/garden/project-atlas
→ 200 { "facts": [...], "total": N, "cursor": "..." }
→ 403 if caller is not a member of the garden
```

The `garden_id` query parameter is additive with other filters (`entity`, `relation`, `scope`, etc.). Garden ACL is enforced: non-members get 403, not an empty result, to prevent membership enumeration.

---

## 6. Federation — v0.9 addition to §6.8

**Garden isolation invariant:** Facts with `garden_id` set MUST NOT appear in federation pull or push payloads. Nodes MUST filter them before sending. This invariant is enforced independently of scope — a garden-tagged `public` fact is still garden-isolated from the federation perspective.

*All other §6 content unchanged from v0.8.*

---

## 7. Design Decisions Log (v0.9 additions)

| Decision | Rationale |
|---|---|
| Garden as partition above scope | Scope is coarse (4 values); gardens add named, member-gated segmentation without replacing the scope model. Gardens sit inside a scope, not in place of it. |
| Garden membership is node-local | Cross-node garden federation introduces complex identity delegation questions (who validates remote membership?). Deferred to Phase 8 when the federation model matures. |
| `garden_id` field on fact, not a separate collection | Facts remain the canonical storage primitive. `garden_id` is a tag that the node enforces at ACL time. No schema redesign needed. |
| Orphaned facts on garden delete | Deleting facts on garden delete would be a destructive non-reversible action. Facts are immutable; orphan detection via lint is the safer path. |
| Source attestation at node, not client | Attestation by client is trivially forgeable. Binding at the node, using the verified identity from the Bearer token, is the only trustworthy enforcement point. |
| Three attestation modes (`enforce`/`warn`/`off`) | Single-operator self-hosted deployments must not break when upgrading. `warn` default gives operators time to audit before enforcing. |
| No delegated attestation in v0.9 | Service-agent-writes-for-human is a real pattern, but the delegation chain (who authorized whom) requires a richer identity model. Track C of Phase 7 adds per-agent keypairs; delegation attestation follows in Track C. |
| `attested: null` for federation ingest | The receiving node is not the attestation authority for facts it relays. Re-attesting would silently alter provenance. |
| Garden slug must be unique per node | Gardens are addressed by `stigmem://authority/garden/{slug}`; collisions on slug would make the URI non-unique. |

---

## 8. Open Questions

1. **Cross-node garden membership.** A garden's members are resolved against the local node's `entity_uri` namespace. In a federated deployment, `stigmem://node-a/user/alice` may be unknown to `node-b`. How should guest membership work across nodes? *Deferred to Phase 8 federation design.*

2. **Garden-scoped contradiction detection.** Currently contradiction detection operates on `(entity, relation, scope)`. Should `garden_id` be a fourth dimension? Two facts could have the same `(entity, relation, scope)` but different `garden_id` values. *Proposing: contradiction detection remains scope-only; garden isolation means garden-A facts and garden-B facts about the same entity do not contradict each other by default. An opt-in cross-garden contradiction check is a Phase 8 concern.*

3. **`attested` field and retraction.** If a fact was written in `warn` mode with `attested: false`, should a retraction (same `entity/relation/scope` with `confidence=0.0`) require `enforce` mode to be trusted? *Recommendation: attestation is per-fact, not per-operation. A retraction with `attested: false` is still a valid immutable record; query consumers can filter on `attested`.*

4. **Garden capacity limits.** No current limit on number of gardens or members per garden. Operators should apply application-level limits; a future spec section may add advisory guidance.

---

## 9. Namespace Registry (v0.9 addition)

### 9.1 Reserved prefixes (v0.9 additions)

*Existing entries from v0.8 unchanged.*

| Prefix | Governed by | Purpose |
|---|---|---|
| `garden:` | Spec maintainers | Garden metadata facts: `garden:member`, `garden:role`, `garden:scope` |
| `stigmem:attest:` | Spec maintainers | Reserved for future per-entity attestation-policy facts (e.g. required-source assertions on a scope or garden). v0.9 source attestation is a pure API operation; this prefix is reserved to prevent squatting ahead of fact-based attestation policy extensions. |

### 9.2 Community-registered prefixes (v0.9 additions)

*(No new community prefixes in v0.9.)*

---

## 10. Schema and Migration (v0.9 addition)

*§10 content from v0.8 unchanged. Migration 004 is additive.*

### Migration 004 — gardens and source attestation

```sql
-- gardens table (§17)
CREATE TABLE IF NOT EXISTS gardens (
    id          TEXT PRIMARY KEY,
    slug        TEXT NOT NULL,           -- URL-safe identifier; e.g. "project-atlas"
    name        TEXT NOT NULL,
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public')),
    description TEXT,
    created_by  TEXT NOT NULL,           -- entity_uri of creator
    created_at  TEXT NOT NULL,
    UNIQUE(slug)
);

-- garden_members table (§17.2)
CREATE TABLE IF NOT EXISTS garden_members (
    garden_id   TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    entity_uri  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin','writer','reader')),
    added_by    TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    PRIMARY KEY (garden_id, entity_uri)
);

CREATE INDEX IF NOT EXISTS idx_garden_members_entity ON garden_members(entity_uri);

-- Add garden_id column to facts (NULL for pre-v0.9 facts)
ALTER TABLE facts ADD COLUMN garden_id TEXT;
CREATE INDEX IF NOT EXISTS idx_facts_garden ON facts(garden_id) WHERE garden_id IS NOT NULL;

-- Add attested column to facts (NULL for pre-v0.9 facts)
ALTER TABLE facts ADD COLUMN attested INTEGER;  -- 1=true, 0=false, NULL=not-applicable
```

**Backward compatibility:** Pre-v0.9 facts have `garden_id = NULL` (no garden) and `attested = NULL` (attestation not applicable). Both columns are nullable by design.

---

## 17. Memory Garden

### 17.1 Motivation

The existing scope model (`local | team | company | public`) is a coarse, operator-level boundary. There is no way to create a named partition shared among a specific set of principals (e.g. "Project Atlas team: Alice + CTO agent + Codex assistant") without either:
- Exposing all those facts to the entire `company` scope, or
- Running a separate node.

**Memory Gardens** fill this gap. A garden is a named, ACL'd logical partition that sits *inside* a scope. It adds fine-grained, membership-based read/write control on top of the existing scope model.

### 17.2 Garden Primitive

A garden is represented by two related structures: `Garden` (the container itself) and `GardenMember` (a principal's membership within it). The `Garden` record binds a human-readable slug to a fixed `FactScope`, ensuring all facts tagged with that garden share a single visibility tier. The `scope` field is set at creation time and cannot be changed — this invariant allows the ACL layer (§17.3) to reject scope-mismatched writes without consulting the facts table.

Membership uses a three-tier role model (`GardenRole`). Roles are coarse by design: fine-grained per-relation permissions would complicate the already-layered access control stack (scope + garden + federation), so the protocol defers to operators who need them to implement a proxy or plugin. The `added_by` field supports audit trails without requiring a separate history table.

```
Garden {
  id:          UUID              // internal primary key
  garden_id:   URI               // stigmem://{authority}/garden/{slug}
  slug:        string            // URL-safe name; unique per node; e.g. "project-atlas"
  name:        string            // display name
  scope:       FactScope         // all facts in this garden MUST have this scope
  description: string?           // optional human-readable description
  created_by:  URI               // entity_uri of creating principal; auto-added as admin
  created_at:  ISO 8601 UTC
}

GardenRole = "admin" | "writer" | "reader"

GardenMember {
  garden_id:  UUID               // references Garden.id
  entity_uri: URI                // the member principal (human, agent, or system)
  role:       GardenRole
  added_by:   URI
  added_at:   ISO 8601 UTC
}
```

**`garden_id` URI construction:** `stigmem://{node_authority}/garden/{slug}`, where `node_authority` is the node's authority component from its `node_id` setting. The slug is lowercased and validated on creation (see §5.14).

### 17.3 Access Control Rules

Garden ACL is checked at fact read and write time, in addition to (not instead of) existing scope enforcement.

**Write access:**

| Condition | Result |
|-----------|--------|
| `garden_id` not provided | Normal scope enforcement only; fact is not garden-tagged. |
| `garden_id` provided; caller is `admin` or `writer` in garden | Allowed. |
| `garden_id` provided; caller is `reader` in garden | `HTTP 403 write permission required` |
| `garden_id` provided; caller not a member | `HTTP 403 not a member of this garden` |
| `garden_id` provided; fact's `scope` ≠ garden's `scope` | `HTTP 422 scope mismatch` |
| `garden_id` provided; garden not found | `HTTP 404 garden not found` |

**Read access:**

A fact with `garden_id` set is returned in query results ONLY if the caller:
1. Passes normal scope enforcement (has `read` permission), AND
2. Holds at least `reader` role in the garden.

Non-member callers do not receive an empty result — they receive `HTTP 403` when querying by `garden_id` filter. If a non-member queries by entity/relation without a `garden_id` filter, garden-tagged facts are silently excluded from results (they cannot enumerate gardens they do not belong to).

**Admin operations:**

| Operation | Required role |
|-----------|--------------|
| Add member | `admin` |
| Change member role | `admin` |
| Remove member | `admin` (cannot remove the last admin) |
| Delete garden | `admin` |
| Read member roster | `reader` or above |
| List accessible gardens | Any valid API key |

### 17.4 Garden Lifecycle

1. **Create:** Any principal with `write` permission on the node can create a garden. Creator is automatically `admin`.
2. **Invite:** Garden admin adds members via `POST /v1/gardens/:id/members`.
3. **Write facts:** Members with `writer` or `admin` role include `garden_id` in `POST /v1/facts`.
4. **Query:** Members include `garden_id` query param in `GET /v1/facts`.
5. **Retract:** Garden writers/admins retract facts using the normal retraction pattern (assert with `confidence=0.0`); must include the same `garden_id`.
6. **Delete:** Garden admin deletes with `DELETE /v1/gardens/:id`. Associated facts become orphaned (garden_id becomes a dangling reference; surfaced by lint, §14).

### 17.5 Relationship to Scope

Gardens and scopes are orthogonal, layered controls:

```
Scope (coarse, node-global):  local | team | company | public
Garden (fine, named subset):  any subset of principals within a scope
```

A garden's `scope` field declares which scope its facts inhabit. This means:
- A `company`-scoped garden's facts are visible to all `company`-level readers... unless they are not members (garden ACL trumps scope for garden-tagged facts).
- A `public`-scoped garden's facts would normally federate, but garden isolation prevents federation (§6 garden isolation invariant). This is a deliberate constraint: gardens are local-first.
- Facts without `garden_id` are unaffected by garden ACL — they continue to use scope-only access control.

### 17.6 Conventions

**Relation namespace:** Garden membership metadata is stored as system facts using the `garden:` prefix. The node writes these automatically when callers add or remove members via the garden management endpoints; they use `source="system:stigmem"` so that attestation checks (§18) can distinguish operator-managed membership from agent-authored assertions. The `garden:member` relation links the garden to a member entity, while `garden:role:<entity_uri>` records the member's permission level (reader, writer, or admin).

```
(entity=<garden_id>, relation="garden:member",   value={type:"ref", v:<member_entity_uri>}, source="system:stigmem", ...)
(entity=<garden_id>, relation="garden:role:<entity_uri>", value={type:"string", v:"writer"}, ...)
```

These system facts are written automatically on membership changes and MUST NOT be modified directly by callers. The `garden:` prefix is reserved in the namespace registry (§9.1).

---

## 18. Source Attestation

### 18.1 Motivation

In v0.8, the `source` field in a fact request body is caller-declared:

```json
{ "entity": "...", "relation": "...", "source": "stigmem://node/user/alice", ... }
```

Nothing prevents an `agent:assistant` principal from writing `"source": "stigmem://node/user/bob"`. The stored fact will falsely attribute its origin to Bob. This undermines:
- Audit trails (who actually wrote this fact?)
- Trust scoring (confidence in a fact depends on who asserted it)
- Track C's keypair-signed attribution model

Source attestation closes this gap by binding `source` to the verified `entity_uri` from the auth principal at write time.

### 18.2 Attestation Model

When a fact is asserted with auth enabled, the node:

1. Resolves the key's registered `entity_uri` and `allowed_source_entities` (§18.7).
2. Normalizes `fact.source` and all entries in the authorized set using §2.6.3.
3. Checks:

```
attested = normalized(fact.source) ∈ { normalized(identity.entity_uri) } ∪ normalized(identity.allowed_source_entities)
```

If `source` is absent from the request and the key has a registered `entity_uri`, the node auto-fills `source` from `key.entity_uri` before the check (§18.8). The auto-filled value is returned in the response.

The result is stored as the `attested` column on the fact record (see §2.7). The behavior on mismatch depends on the node's configured `SourceAttestationMode`:

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

**`enforce` mode:**
- Any `source` outside `{entity_uri} ∪ allowed_source_entities` causes HTTP 403:
  ```json
  { "error": "source_attestation_failed",
    "detail": "source URI must equal the authenticated principal's entity_uri or delegation list" }
  ```
- `attested: true` on all accepted facts.

**`warn` mode (default):**
- Mismatch logged to stderr: `[stigmem] WARN: source attestation mismatch — declared source=X, identity=Y`.
- Fact accepted with `attested: false`.
- `attested: true` if source matches.

**`off` mode:**
- No check. `attested: null` on all facts.

### 18.3 Well-Known Advertisement

Nodes MUST advertise their attestation mode at `/.well-known/stigmem`:

```json
{
  ...existing fields...,
  "source_attestation": "enforce" | "warn" | "off"
}
```

Clients SHOULD read this before writing to understand whether their `source` claim will be enforced.

### 18.4 Attestation and Retraction

A retraction (fact with `confidence=0.0`) is subject to the same attestation rules as any other fact write. If the node is in `enforce` mode and the caller's identity differs from the `source` field in the retraction body, the retraction is rejected with `HTTP 403`.

**Implication:** A fact written by `agent:assistant` can only be retracted by `agent:assistant` in `enforce` mode (since the source must match the caller). If the original writer is no longer available, node admins must temporarily set `warn` or `off` mode to perform administrative retractions.

### 18.5 Integration with Track C (Per-Agent Keypairs)

Phase 7 Track C adds per-agent keypair registration. Once an agent's public key is registered on the node, a stronger form of attestation becomes possible: the agent signs the fact payload before submission, and the node verifies the signature against the registered public key. This moves attestation from "bearer-token-level" (who presented this API key?) to "fact-level" (who signed this specific fact payload?).

v0.9 source attestation is a first step. v0.9 `attested: true` means the bearer-token-level check passed. Track C extends this with a separate `signature_verified: true | false | null` field once keypairs are implemented.

### 18.6 Querying by Attestation

Facts can be filtered by attestation status:

```
GET /v1/facts?attested=true    // only source-attested facts
GET /v1/facts?attested=false   // only non-attested facts (warn/off mode)
```

The `attested` query parameter is optional. Omitting it returns all facts (default behavior, unchanged from v0.8).

### 18.7 Key Registration: Binding `entity_uri` to an API Key

Source attestation depends on the node knowing the caller's authorized `entity_uri`. This binding is established at **key creation time** and is immutable — a key's `entity_uri` cannot be changed after creation (to prevent retroactive provenance forgery).

#### `entity_uri` requirements

- MUST be a formal URI matching the `stigmem://` scheme (§2.5). Informal URIs are rejected at key creation.
- MUST be unique within the node's `api_keys` table (one key per entity).
- Stored in normalized form (§2.6.3) to align with ingest normalization.

#### Key creation

A key is created with a single POST that binds the `entity_uri`, scope
permissions, and optional delegation list at creation time. The node returns
the raw API key exactly once in the response; only its SHA-256 digest is
stored server-side. The `entity_uri` is immutable after creation to prevent
retroactive re-attribution of facts already written with this key.

```
POST /v1/auth/keys
Authorization: Bearer <admin-key>
{
  "description":             "CTO agent key",
  "entity_uri":              "stigmem://company.example/agent/cto",
  "allowed_scopes":          ["company", "public"],
  "allowed_source_entities": []
}
→ 201 {
    "key_id":                  "<uuid>",
    "raw_key":                 "<secret>",   // shown once; SHA-256 stored
    "entity_uri":              "stigmem://company.example/agent/cto",
    "allowed_scopes":          ["company","public"],
    "allowed_source_entities": [],
    "created_at":              "2026-05-03T00:00:00Z"
  }
```

The caller MUST store `raw_key` securely — it is not retrievable after creation. The node stores only the SHA-256 hex digest.

**Creating a key without `entity_uri`** is allowed for backward compatibility. Such a key can still write facts; in `enforce` mode it will be rejected (HTTP 400 `key_not_attested`); in `warn` mode writes are accepted with `attested: false`.

**Immutability:** Nodes MUST NOT allow `entity_uri` to be updated via `PATCH`. Attempting to update it returns HTTP 422:

```json
{ "error": "immutable_field",
  "detail": "entity_uri cannot be changed after creation; revoke and re-create the key" }
```

#### Updated `Identity` shape

The `Identity` shape extends the v0.8 shape with the `allowed_source_entities`
field needed for delegation (§18.9). This is the object the node constructs
from the API key record when authenticating a request — it drives every
attestation check in the write path.

```
Identity {
  entity_uri:              URI            // registered at key creation; enforced against fact.source
  credential:              string         // API key (SHA-256 stored server-side)
  node_url:                string
  allowed_scopes:          FactScope[]
  allowed_source_entities: URI[]          // additional source URIs this key may claim (see §18.9)
}
```

#### Updated attestation check (§18.2 with delegation)

The check in §18.2 is updated to include the delegation list:

```
attested = normalized(fact.source) ∈ { normalized(identity.entity_uri) } ∪ normalized(identity.allowed_source_entities)
```

All normalization uses §2.6.3. Delegation set entries are stored in normalized form at key creation.

### 18.8 Source Auto-fill

If the `source` field is absent from a `POST /v1/facts` request body and the presenting key has a registered `entity_uri`, the node MUST auto-fill `source` from `key.entity_uri`. The auto-filled value MUST appear in the response body.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value":  { "type": "string", "v": "CEO" },
  "confidence": 1.0, "scope": "company" }
  // source omitted

→ 201 { ..., "source": "stigmem://company.example/agent/cto", "attested": true }
```

If `source` is absent and the key has **no registered `entity_uri`**:

| Mode | Behaviour |
|---|---|
| `enforce` | HTTP 400: `{ "error": "source_required", "detail": "source is required when key has no entity_uri in enforce mode" }` |
| `warn` | Accept; include `X-Stigmem-Warn: source_unattested` in response; `attested: false`. |
| `off` | Accept; `attested: null`. |

### 18.9 Delegation via `allowed_source_entities`

Some adapters write facts on behalf of other principals. The Paperclip hook, for example, writes facts with `source="stigmem://company.example/agent/cto"` while running inside an agent's context — but the adapter's own key may be bound to `stigmem://company.example/adapter/paperclip`.

A key's `allowed_source_entities` is an explicit allowlist of additional URIs the key is authorized to claim as `source`:

```json
{
  "entity_uri":              "stigmem://company.example/adapter/paperclip",
  "allowed_source_entities": [
    "stigmem://company.example/agent/cto",
    "stigmem://company.example/agent/qa"
  ]
}
```

This key may write facts with `source` equal to any of: the adapter itself, the CTO agent, or the QA agent. Any other `source` claim is rejected (HTTP 403 `source_attestation_failed`).

**Delegation is not transitive.** If key K1 (entity E1) has E2 in `allowed_source_entities`, K1 can claim E1 or E2, but this grants K1 no rights to entities that E2's own key delegates.

**Default:** `allowed_source_entities` defaults to `[]`. Every delegation must be an explicit operator grant.

### 18.10 Full Key Management API

All key management routes require a key with `admin=true`. The key management
API covers the full lifecycle: creation, inspection, scope/delegation updates,
and revocation. Revocation is a soft delete — the key record is retained with a
`revoked_at` timestamp for audit purposes, but all subsequent authentication
attempts with the revoked key are rejected. A separate attestation-audit
endpoint provides a searchable event log of every attestation decision the node
has made, filterable by key, outcome, and time.

```
POST   /v1/auth/keys                             // create key
GET    /v1/auth/keys                             // list all keys
GET    /v1/auth/keys/:key_id                     // get key metadata
PATCH  /v1/auth/keys/:key_id                     // update description, allowed_scopes, allowed_source_entities
DELETE /v1/auth/keys/:key_id                     // revoke key (sets revoked_at; record retained for audit)

GET    /v1/auth/attestation-audit                // attestation event log (admin only)
```

`PATCH` request body may include `description`, `allowed_scopes`, `allowed_source_entities`. `entity_uri` and `admin` are immutable after creation.

The attestation audit endpoint returns a paginated log of every attestation
decision the node has made. Each event records the key that was used, the
`source` value the caller claimed, whether attestation passed, and — when it
failed — the specific rejection reason. This log is essential for operators
transitioning from `warn` to `enforce` mode: querying for `attested=false`
events surfaces all callers that would break under strict enforcement.

```
GET /v1/auth/attestation-audit?key_id=<id>&attested=false&limit=50
→ 200 {
    "events": [{
      "id":              "<uuid>",
      "key_id":          "...",
      "entity_uri":      "...",           // key's registered entity_uri; null for legacy keys
      "claimed_source":  "...",           // source value from the request
      "attested":        true | false,
      "rejection_reason": null | "source_attestation_failed" | "source_required" | "key_not_attested",
      "ts":              "2026-05-03T00:00:00Z"
    }],
    "cursor": "...", "has_more": false
  }
```

Filter params: `key_id`, `attested` (true/false), `after` (pagination cursor), `limit` (max 500).

### 18.11 Schema Migration (Migration 005)

Migration 005 adds two tables to support source attestation. The `api_keys`
table formalizes key storage that was previously external to the database,
binding each key to an `entity_uri` and carrying its scope permissions and
delegation list. The `attestation_audit` table provides the append-only event
log queried by the admin audit endpoint (§18.10). Both tables are additive and
do not alter the existing `facts` schema — the `attested` column on `facts`
was already added in §2.7.

```sql
-- API key management (spec §18.7)
CREATE TABLE IF NOT EXISTS api_keys (
  id                      TEXT PRIMARY KEY,
  description             TEXT,
  credential_hash         TEXT NOT NULL UNIQUE,     -- SHA-256 hex of raw key
  entity_uri              TEXT,                     -- formal URI; NULL for legacy keys
  allowed_scopes          TEXT NOT NULL DEFAULT '["local","team","company","public"]',
  allowed_source_entities TEXT NOT NULL DEFAULT '[]', -- JSON array; stored in normalized form
  admin                   INTEGER NOT NULL DEFAULT 0,
  created_at              TEXT NOT NULL,
  revoked_at              TEXT                      -- NULL if active
);

CREATE INDEX IF NOT EXISTS idx_api_keys_credential ON api_keys(credential_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_entity_uri ON api_keys(entity_uri);

-- Attestation audit log (spec §18.10)
CREATE TABLE IF NOT EXISTS attestation_audit (
  id               TEXT PRIMARY KEY,
  key_id           TEXT NOT NULL REFERENCES api_keys(id),
  entity_uri       TEXT,
  claimed_source   TEXT NOT NULL,
  attested         INTEGER NOT NULL,      -- 1=true, 0=false
  rejection_reason TEXT,
  ts               TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attestation_audit_key_ts   ON attestation_audit(key_id, ts);
CREATE INDEX IF NOT EXISTS idx_attestation_audit_attested ON attestation_audit(attested, ts);
```

**Migration note for existing deployments:** Pre-v0.9 nodes may manage API keys outside the database. Migration 005 formalizes key storage. Operators MUST:
1. Register existing keys via `POST /v1/auth/keys` using an `existing_credential` migration field (accepted for 30 days post-deploy).
2. Set `STIGMEM_SOURCE_ATTESTATION_MODE=warn` initially.
3. Register `entity_uri` for all keys, then switch to `enforce` after verifying the audit log shows no `attested=false` writes.

### 18.12 Error Reference

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `source_required` | `source` omitted; key has no `entity_uri`; `enforce` mode |
| 400 | `key_not_attested` | Key has no `entity_uri`; node requires attestation |
| 403 | `source_attestation_failed` | `source` not in `{entity_uri} ∪ allowed_source_entities` |
| 422 | `immutable_field` | Attempt to PATCH `entity_uri` or `admin` |

---

## 19. Security Policy

*This section is non-normative.*

The active security policy — supported versions, vulnerability reporting instructions, scope definitions, and the coordinated disclosure timeline — is maintained in [`SECURITY.md`](../SECURITY.md) at the root of the repository.

**Reporting:** Do not open a public GitHub issue for security vulnerabilities. Report via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories). We acknowledge within 48 hours and target a patch within 14 days for critical vulnerabilities.

**Disclosure timeline:** 90 days from the report date before public disclosure, except for vulnerabilities already being actively exploited in the wild.

For the current security posture and Dependabot alert triage covering v1.0-rc, see the [Security Posture section of SECURITY.md](../SECURITY.md#security-posture--v10-rc-2026-05-03).

---

*v1.0 — Stable. All sections normative. Apache-2.0.*
