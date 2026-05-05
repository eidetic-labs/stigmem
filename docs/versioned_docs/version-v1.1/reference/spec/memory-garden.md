---
title: §17. Memory Garden
sidebar_label: §17 Memory Garden
audience: Spec
description: "Stigmem spec section 17 — Named, ACL'd partitions of the fact store with admin/writer/reader role model."
---

# §17. Memory Garden {#section-17}

**Status:** Normative (v1.0)

Named, ACL'd partitions of the fact store with admin/writer/reader role model.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

### §17.1 Motivation {#section-17-1}

The existing scope model (`local | team | company | public`) is a coarse, operator-level boundary. There is no way to create a named partition shared among a specific set of principals (e.g. "Project Atlas team: Alice + CTO agent + Codex assistant") without either:
- Exposing all those facts to the entire `company` scope, or
- Running a separate node.

**Memory Gardens** fill this gap. A garden is a named, ACL'd logical partition that sits *inside* a scope. It adds fine-grained, membership-based read/write control on top of the existing scope model.

### §17.2 Garden Primitive {#section-17-2}

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

### §17.3 Access Control Rules {#section-17-3}

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

### §17.4 Garden Lifecycle {#section-17-4}

1. **Create:** Any principal with `write` permission on the node can create a garden. Creator is automatically `admin`.
2. **Invite:** Garden admin adds members via `POST /v1/gardens/:id/members`.
3. **Write facts:** Members with `writer` or `admin` role include `garden_id` in `POST /v1/facts`.
4. **Query:** Members include `garden_id` query param in `GET /v1/facts`.
5. **Retract:** Garden writers/admins retract facts using the normal retraction pattern (assert with `confidence=0.0`); must include the same `garden_id`.
6. **Delete:** Garden admin deletes with `DELETE /v1/gardens/:id`. Associated facts become orphaned (garden_id becomes a dangling reference; surfaced by lint, §14).

### §17.5 Relationship to Scope {#section-17-5}

Gardens and scopes are orthogonal, layered controls:

```
Scope (coarse, node-global):  local | team | company | public
Garden (fine, named subset):  any subset of principals within a scope
```

A garden's `scope` field declares which scope its facts inhabit. This means:
- A `company`-scoped garden's facts are visible to all `company`-level readers... unless they are not members (garden ACL trumps scope for garden-tagged facts).
- A `public`-scoped garden's facts would normally federate, but garden isolation prevents federation (§6 garden isolation invariant). This is a deliberate constraint: gardens are local-first.
- Facts without `garden_id` are unaffected by garden ACL — they continue to use scope-only access control.

### §17.6 Conventions {#section-17-6}

**Relation namespace:** Garden membership metadata is stored as system facts using the `garden:` prefix:
```
(entity=<garden_id>, relation="garden:member",   value={type:"ref", v:<member_entity_uri>}, source="system:stigmem", ...)
(entity=<garden_id>, relation="garden:role:<entity_uri>", value={type:"string", v:"writer"}, ...)
```

These system facts are written automatically on membership changes and MUST NOT be modified directly by callers. The `garden:` prefix is reserved in the namespace registry (§9.1).

---
