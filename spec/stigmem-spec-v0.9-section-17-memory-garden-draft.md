# Stigmem §17 — Memory Garden Primitive (v0.9 Draft)

> **Draft status:** A1 deliverable for Track A. Spec section only.
> Full v0.9 spec file will be assembled when A2 (Source Attestation) is also complete.
> Implementation is the A3 deliverable.

---

## 17. Memory Garden Primitive — v0.9 Draft

> **v0.9 status:** Draft. The Memory Garden primitive adds named, ACL-enforced partitions
> above the scope layer. Defines the `Garden` data shape, `GardenMember` shape, role model
> (admin / writer / reader), membership API surface, and read/write ACL enforcement points.
> §17.6 covers interactions with lint, decay, and synthesis. §17.8 specifies migration 005.
> Implementation is the A3 deliverable ().
> Conformance test vectors (`GARDEN_VECTORS`) will be finalized with A3 implementation.
> This section will be promoted to normative in v0.9 once conformance tests pass.

### 17.1 Motivation

The existing `FactScope` enum (`local`, `team`, `company`, `public`) provides coarse,
node-wide visibility buckets. Scope alone cannot express:

- "This sprint's facts are writable by agents A and B but readable by everyone on the project."
- "This audit trail is isolated to a named working group of two humans and one QA agent."
- "These project-alpha notes are shared only with members I explicitly invited."

A **Memory Garden** is a named, ACL-enforced partition that layers fine-grained,
membership-based access control on top of scope. Facts written into a garden are visible
only to garden members; the underlying scope continues to govern federation behavior.
Gardens do not replace scopes — they refine them.

**Key properties:**

- **Named:** every garden has a human-readable slug (e.g. `sprint-42`, `project-alpha-audit`).
- **ACL-enforced:** members hold a role (`admin`, `writer`, `reader`). Non-members are denied
  access to garden facts regardless of their API key's scope allowances.
- **Above scope:** a garden has a `scope` floor. The garden's scope is the least-restrictive
  scope its facts may carry. The scope continues to govern federation; see §17.5 for the
  interaction between garden ACL and federation.
- **Heterogeneous membership:** member entities are any valid `stigmem://` entity URI —
  human users, agents, or other well-known entity types. Mixed membership is explicitly
  supported.

### 17.2 Garden Data Shape

```
Garden {
  id:           UUID
  uri:          "stigmem:garden:{id}"    // canonical entity URI for this garden
  name:         string                   // slug: unique per node; see constraints below
  scope:        FactScope                // scope floor for all facts in this garden
  description:  string?                  // optional; ≤ 1 KB
  created_by:   URI                      // entity URI of the creating principal
  created_at:   ISO 8601 UTC
  member_count: integer                  // derived field; populated on reads
}
```

**Name constraints:**

- MUST match `[a-z0-9][a-z0-9-]*[a-z0-9]` or be a single `[a-z0-9]` character.
- Length: 1–64 characters.
- Unique per node. Attempting to create a garden with a duplicate name MUST return HTTP 409.

**`uri` field:** The canonical entity URI `stigmem:garden:{id}` is a first-class entity in
the fact store. Nodes MAY assert system-generated facts about the garden via this URI at
creation time (see §17.9).

### 17.3 Role Model

Three roles, strictly ordered by privilege: **admin > writer > reader**.

| Role | Read facts | Write facts | Add/remove members | Change roles | Delete garden |
|------|:---:|:---:|:---:|:---:|:---:|
| `admin`  | ✓ | ✓ | ✓ | ✓ | ✓ |
| `writer` | ✓ | ✓ | — | — | — |
| `reader` | ✓ | — | — | — | — |

**Last-admin invariant:** A garden MUST always have at least one `admin`. Any operation that
would leave the garden with zero admins MUST be rejected with HTTP 409 and
`"error": "last_admin_cannot_be_removed"`.

**Bootstrap:** The `created_by` principal is automatically enrolled as the first `admin`
member at garden creation. The garden is immediately usable with one member.

**Role promotion/demotion:** An `admin` may change any member's role, including their own.
An admin may not demote themselves below `admin` if they are the only admin (last-admin
invariant applies).

### 17.4 Member Shape

```
GardenMember {
  member_uri:  URI                           // entity URI; any type (human, agent, ...)
  role:        "admin" | "writer" | "reader"
  granted_by:  URI                           // entity URI of the granting admin
  granted_at:  ISO 8601 UTC
}
```

**Member types:** Any `stigmem://` entity URI is a valid member entity. The role model is
identical for `user/` and `agent/` types — there is no special-casing by entity type.
Concrete examples:
- `stigmem://company.example/user/alice`  → human
- `stigmem://company.example/agent/cto`  → agent

**No cross-garden inheritance:** Membership in garden A does not imply any access to
garden B. Roles do not propagate across gardens.

**No wildcard membership:** There is no "all principals" membership shortcut. Access is
always via an explicit `GardenMember` record.

### 17.5 Facts in a Garden

The `FactShape` (§2) gains one optional field in v0.9:

```
FactShape (v0.9 addition)
  ...existing fields (entity, relation, value, source, timestamp, hlc,
     valid_until, confidence, scope)...
  garden_id:  UUID?  // optional; if present, this fact belongs to the named garden
```

A fact with `garden_id` set is a **garden fact**. A fact without `garden_id` is a
**scope fact** and subject only to the existing scope enforcement (§3.4). These two
paths are strictly separate at every enforcement point.

#### ACL enforcement — write

Enforcement order at `POST /v1/facts`:

1. **Scope auth** (§3.5): reject if API key lacks write access to the fact's `scope`.
2. **Garden existence**: if `garden_id` is present, reject with HTTP 404 if the garden
   does not exist.
3. **Garden write role**: if `garden_id` is present, reject with HTTP 403 if the caller's
   `entity_uri` is not a garden `writer` or `admin`.
4. **Scope floor check**: the fact's `scope` MUST be the same as or more restrictive than
   the garden's `scope`. A `public`-scoped fact MUST NOT be written into a `company`-scoped
   garden; return HTTP 422 with `"error": "scope_exceeds_garden_floor"`.
5. **Write proceeds** normally.

Summary:

```
write path: scope-auth → garden-existence → garden-role-check → scope-floor-check → write
```

#### ACL enforcement — read

At `GET /v1/facts` (and all other fact-returning routes):

1. **Scope auth**: apply normal scope filtering.
2. **Garden visibility**: facts with `garden_id` MUST be excluded from responses unless the
   caller's `entity_uri` is a member of that garden (any role). This applies even when the
   caller holds API key scope rights for the parent scope.
3. **Explicit garden filter**: callers MAY pass `garden_id=<uuid>` as a query parameter to
   restrict results to a specific garden. Non-member callers receive HTTP 403 for this query.

```
read path: scope-auth → garden-membership-check (per fact) → return
```

**Non-member visibility guarantee:** Garden facts are fully invisible to non-members — they
do not appear in paginated result sets, synthesis, lint, or conflict lists. Non-members
receive the same response as if those facts did not exist.

#### Federation and gardens

Garden ACL is a **node-local construct**. Garden membership records are not federated.

Facts with `garden_id` in a `public`-scoped garden MAY be federated per §6.4 scope rules,
but the receiving node has no knowledge of the originating garden's membership list and
cannot enforce garden ACL on the received fact.

**Ingest rule:** Nodes MUST strip `garden_id` from all incoming federated facts at ingest
time. The stripped fact is stored as a plain scope fact. The originating `garden_id` is
preserved in a `stigmem:garden_origin` meta-fact for audit purposes only and is never
used for ACL enforcement at the receiving node.

```
(entity=<fact-id>, relation="stigmem:garden_origin",
 value={type:"string", v:"<garden_id>"},
 source="system:stigmem", ...)
```

`stigmem:garden_origin` meta-facts MUST NOT be re-replicated.

**Design rationale:** The originating node is the authoritative ACL enforcer for its gardens.
Propagating garden ACL to peers would require distributed membership synchronization, which
is a Phase 8+ problem. Stripping `garden_id` on federation preserves correctness: the
receiving node never incorrectly enforces a garden ACL it does not own.

#### Garden deletion and orphaned facts

Deleting a garden does NOT delete the facts in it. Facts with the deleted garden's
`garden_id` become **orphaned garden facts**: they retain the `garden_id` column value
for audit, but the garden record no longer exists.

Orphaned garden facts MUST be treated as plain scope facts at all enforcement points:
ACL check falls through to normal scope auth; `garden_id` is preserved in the store but
has no effect on access control.

**Rationale:** Facts are immutable (§2). Cascade-deleting facts on garden deletion would
violate the immutability invariant and destroy provenance. Orphaned facts degrade
gracefully to scope-enforced access.

### 17.6 Interactions with Lint, Decay, and Synthesis

All three Phase 6 operational tools (§14–§16) honor garden ACL when the caller specifies
a `garden_id` filter. Without a `garden_id` filter, tool results omit garden facts for
non-members as per §17.5 read enforcement.

| Operation | Garden interaction |
|-----------|-------------------|
| `POST /v1/lint` | Add optional `garden_id` field to the lint request body to restrict sweep to one garden. Caller must be a member (any role). Without `garden_id`, garden facts are excluded for non-members. |
| `POST /v1/decay/sweep` | Add optional `garden_id` to restrict sweep. Caller must be a garden `writer` or `admin` (sweep writes retractions). Without `garden_id`, non-member's garden facts are excluded. |
| `POST /v1/synthesis` | Add optional `garden_id` to synthesize only that garden's facts. Caller must be a member (any role). Without `garden_id`, synthesis output excludes garden facts the caller cannot read. |

**Wire additions (v0.9 extension fields):**

```
POST /v1/lint        → body may include "garden_id": UUID?
POST /v1/decay/sweep → body may include "garden_id": UUID?
POST /v1/synthesis   → body may include "garden_id": UUID?
```

These fields are optional and backward-compatible; nodes receiving a v0.8 request without
`garden_id` behave identically to v0.8.

**Lint — `broken_ref` across gardens:** A `broken_ref` finding MUST NOT cross garden
boundaries. A `ref`-type fact in garden A pointing to an entity that exists only as a
garden fact in garden B is NOT reported as broken if the caller cannot see garden B — the
target is invisible, not missing. This is consistent with non-member visibility guarantee:
from the caller's perspective, the entity may exist in a scope or garden they cannot read.

### 17.7 Wire Format: Garden Management

All garden management routes require `Authorization: Bearer <api-key>`. The `entity_uri`
associated with the API key is used as the principal identity for role checks and
`created_by` / `granted_by` fields.

#### Create garden

```
POST /v1/gardens
Authorization: Bearer <api-key>
{
  "name":        string,      // required; slug constraints per §17.2
  "scope":       FactScope,   // required
  "description": string?      // optional; ≤ 1 KB
}

→ 201 {
    "id":           "<uuid>",
    "uri":          "stigmem:garden:<uuid>",
    "name":         "<slug>",
    "scope":        "<scope>",
    "description":  "<string>" | null,
    "created_by":   "<entity-uri>",
    "created_at":   "<ISO8601>",
    "member_count": 1
  }

→ 400  name constraint violation (pattern, length)
→ 409  name already exists on this node
→ 422  invalid scope value
```

The calling principal is automatically enrolled as the first `admin` member.

#### Get garden

```
GET /v1/gardens/:garden_id
Authorization: Bearer <api-key>

→ 200 { ...Garden... }
→ 403 caller is not a member of this garden
→ 404 garden not found
```

#### List accessible gardens

```
GET /v1/gardens[?cursor=<opaque>&limit=<int>]
Authorization: Bearer <api-key>

→ 200 {
    "gardens":  [ { ...Garden... } ],
    "cursor":   "<opaque>" | null,
    "has_more": boolean
  }
```

Returns only gardens where the calling principal is a member (any role). Default `limit` is
50; maximum is 200. Cursor is opaque and stable.

#### Delete garden

```
DELETE /v1/gardens/:garden_id
Authorization: Bearer <api-key>    // caller must be admin

→ 204  No Content
→ 403  caller is not an admin
→ 404  garden not found
```

Garden facts become orphaned (§17.5). Member records are cascade-deleted (§17.8 schema).

#### Add member

```
POST /v1/gardens/:garden_id/members
Authorization: Bearer <api-key>    // caller must be admin
{
  "member_uri": URI,                              // required
  "role":       "admin" | "writer" | "reader"    // required
}

→ 201 { ...GardenMember... }
→ 403 caller is not an admin
→ 404 garden not found
→ 409 member_uri is already a member (use PATCH to change role)
```

#### List members

```
GET /v1/gardens/:garden_id/members
Authorization: Bearer <api-key>    // caller must be a member (any role)

→ 200 { "members": [ { ...GardenMember... } ] }
→ 403 caller is not a member
→ 404 garden not found
```

#### Change member role

```
PATCH /v1/gardens/:garden_id/members/:member_uri
Authorization: Bearer <api-key>    // caller must be admin
{ "role": "admin" | "writer" | "reader" }

→ 200 { ...GardenMember... }
→ 403 caller is not an admin
→ 404 garden not found, or member_uri is not a member of this garden
→ 409 change would leave garden with no admins (last-admin invariant)
```

#### Remove member

```
DELETE /v1/gardens/:garden_id/members/:member_uri
Authorization: Bearer <api-key>    // caller must be admin

→ 204  No Content
→ 403  caller is not an admin
→ 404  garden not found, or member_uri is not a member of this garden
→ 409  removing member_uri would leave the garden with no admins
```

#### Error responses summary

| HTTP | Condition |
|------|-----------|
| 400 | Name constraint violation; invalid scope; malformed `member_uri` |
| 403 | Insufficient role for operation |
| 404 | Garden or member not found |
| 409 | Duplicate garden name; duplicate member; last-admin invariant |
| 422 | Fact `scope` exceeds garden's `scope` floor on write |

### 17.8 Schema: Migration 005 (v0.9)

```sql
-- Gardens table
CREATE TABLE IF NOT EXISTS gardens (
  id          TEXT PRIMARY KEY,         -- UUID
  uri         TEXT NOT NULL UNIQUE,     -- "stigmem:garden:{id}"
  name        TEXT NOT NULL UNIQUE,     -- slug; node-scoped uniqueness
  scope       TEXT NOT NULL,            -- FactScope floor
  description TEXT,                     -- optional; ≤ 1 KB
  created_by  TEXT NOT NULL,            -- entity URI of creating principal
  created_at  TEXT NOT NULL             -- ISO 8601 UTC
);

-- Garden membership table
CREATE TABLE IF NOT EXISTS garden_members (
  garden_id  TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
  member_uri TEXT NOT NULL,             -- entity URI of human or agent
  role       TEXT NOT NULL,             -- "admin" | "writer" | "reader"
  granted_by TEXT NOT NULL,             -- entity URI of granting admin
  granted_at TEXT NOT NULL,             -- ISO 8601 UTC
  PRIMARY KEY (garden_id, member_uri)
);

-- New column on facts table (migration 005)
ALTER TABLE facts ADD COLUMN garden_id TEXT;  -- FK: gardens(id); NULL = scope fact

-- Indexes
CREATE INDEX IF NOT EXISTS idx_garden_members_uri
  ON garden_members(member_uri);

CREATE INDEX IF NOT EXISTS idx_garden_members_garden_role
  ON garden_members(garden_id, role);

CREATE INDEX IF NOT EXISTS idx_facts_garden
  ON facts(garden_id) WHERE garden_id IS NOT NULL;
```

**FK note:** `garden_members(garden_id)` cascades on DELETE so member records are
cleaned up when a garden is deleted. `facts.garden_id` intentionally does NOT cascade
(facts are immutable; orphaned garden facts retain their `garden_id` for audit — §17.5).

**`garden_id` column:** NULL for all pre-v0.9 facts and all scope facts. Nodes upgrading
to v0.9 run this migration; existing facts are unaffected.

### 17.9 Namespace and Entity URI

The following prefixes are added to §9 in v0.9:

| Prefix | Governed by | Purpose |
|--------|-------------|---------|
| `stigmem:garden:` | Spec maintainers | Canonical entity URIs for garden objects: `stigmem:garden:{uuid}` |
| `stigmem:garden_origin` | Spec maintainers | Meta-fact relation recording originating `garden_id` for federated facts that had `garden_id` stripped at ingest |
| `garden:` | Spec maintainers | System-generated facts about a garden entity: `garden:name`, `garden:scope`, `garden:description` |

**System-generated garden facts:** At creation time nodes SHOULD assert the following
facts using the garden's own URI as the entity:

```
(entity="stigmem:garden:{id}", relation="garden:name",
 value={type:"string", v:"<name>"},
 source="system:stigmem", scope=<garden.scope>, confidence=1.0)

(entity="stigmem:garden:{id}", relation="garden:scope",
 value={type:"string", v:"<scope>"},
 source="system:stigmem", scope=<garden.scope>, confidence=1.0)

(entity="stigmem:garden:{id}", relation="garden:description",
 value={type:"string", v:"<description>"},
 source="system:stigmem", scope=<garden.scope>, confidence=1.0)  // omit if description is null
```

These system-generated facts are exempt from decay (§15.1 exempt-relations rule applies
to all `stigmem:` and `garden:` namespace facts). They enable querying garden metadata via
the standard `GET /v1/facts?entity=stigmem:garden:{id}` interface without requiring a
separate garden API call.

**Garden entities as fact subjects:** Agents MAY assert additional facts about a garden
entity using the `stigmem:garden:{id}` URI. For example:

```
(entity="stigmem:garden:abc123", relation="memory:status",
 value={type:"string", v:"active"},
 source="stigmem://company.example/agent/cto", scope="company")
```

Such facts follow normal garden ACL: if the asserting agent is a member of the garden,
the `garden_id` field should be set so the fact is only visible to other members.

### 17.10 Design Decisions

| Decision | Rationale |
|----------|-----------|
| Garden as ACL layer above scope, not replacing scope | Scope governs federation; gardens govern intra-node access. Keeping them orthogonal avoids redesigning federation semantics. |
| Three roles (admin / writer / reader) | Sufficient for the "one owner, multiple contributors, read-only observers" pattern common in project and sprint contexts. Plugin roles would add complexity without a concrete use case today. |
| No cross-garden inheritance | Prevents accidental cross-garden ACL bypass. Each garden is an independent trust boundary. |
| Orphaned facts on garden delete (not cascade delete) | Facts are immutable (§2). Cascade-deleting facts on garden deletion would violate the immutability invariant and destroy provenance. Orphaned facts degrade gracefully to scope-enforced access. |
| `garden_id` stripped from federated facts | Garden membership is node-local; receiving nodes cannot enforce an originating garden's ACL. Stripping `garden_id` at ingest prevents false security assumptions at the receiving node. The `stigmem:garden_origin` meta-fact preserves the audit trail. |
| Mixed human + agent membership | Agents and humans are both entity URIs of different types; the role model is type-agnostic. No separate membership hierarchy needed. |
| Single `garden_id` FK on facts (not junction table) | A fact belongs to at most one garden. Cross-garden sharing can be achieved by asserting the same (entity, relation) in multiple gardens with distinct `garden_id` values — each assertion is an independent immutable fact. |
| `GET /v1/gardens` returns member-visible gardens only | No public garden discovery by default. An operator who wants a discoverable catalog can publish `garden:name` facts at `public` scope; the registry pattern is opt-in. |
| `member_count` as derived field | Avoids a cached count that can drift from the `garden_members` table. Computed at read time from a `COUNT(*)` join. Acceptable at low membership cardinality; caching is an implementation optimization. |

### 17.11 Open Questions (v0.9 draft)

1. **Garden-scoped synthesis.** `POST /v1/synthesis` currently operates on a `FactScope`.
   Should it also accept `garden_id` directly? The §17.6 extension field covers this but the
   full synthesis algorithm for a garden-scoped request is not yet specified. Deferred to A3
   implementation ().

2. **Garden discovery / public registry.** Should `GET /v1/gardens` expose `public`-scoped
   gardens to all callers (with read-only visibility), or remain member-only? The current
   design is member-only; public garden discovery is deferred to v0.9 final.

3. **Cross-garden `broken_ref` lint.** A `ref` in garden A may point to an entity that
   only exists as a garden fact in garden B. The current rule (§17.6) says this is NOT a
   lint error for callers who cannot see garden B. Whether a privileged admin caller should
   see cross-garden broken refs is an open question for Phase 7.

4. **Guest / time-limited roles.** Should gardens support a `guest` role with rate-limited
   read access, or role expiry timestamps? No concrete use case yet; deferred.

5. **Garden-to-garden ACL delegation.** Can garden A grant read access to all members of
   garden B? This would require inter-garden references and adds complexity. Deferred.

---

*Drafted by CTO — A1 deliverable for . Part of Track A ().*
*Source Attestation (A2) draft pending before full v0.9 spec file is assembled.*
