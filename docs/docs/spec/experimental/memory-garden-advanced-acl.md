---
spec_id: Spec-X5-Memory-Garden-Advanced-ACL
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-14
supersedes: pre-reset §17 advanced Memory Garden ACL material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-02-Scopes-and-ACL >= 0.1.0-alpha.0
title: §17. Memory Garden
sidebar_label: §17 Memory Garden
audience: Spec
description: "Stigmem spec section 17 — Named, ACL'd partitions of the fact store with admin/writer/reader role model."
stability: experimental
since: 0.9.0a1
---

# §17. Memory Garden {#section-17}

<p className="stigmem-meta"><span>4 min read</span><span>Spec contributor · Operator</span><span>Experimental · future plugin line</span></p>

<div className="stigmem-lead">

**What this section covers**

Named, ACL'd logical partitions of the fact store that sit *inside* a
scope. Memory Gardens add fine-grained, membership-based read/write
control on top of the coarse `local | team | company | public`
boundary. Basic ACL is owned by `Spec-02-Scopes-and-ACL`; advanced
behavior is staged here.

</div>

**Status:** Experimental / opt-in source package on `main`

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for advanced Memory Garden ACL semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

### §17.1 Motivation {#section-17-1}

The existing scope model (`local | team | company | public`) is a coarse, operator-level boundary. There is no way to create a named partition shared among a specific set of principals (e.g. "Project Atlas team: Alice + CTO agent + Codex assistant") without either:

<div className="stigmem-grid">

<div><h4>Exposing facts</h4><p>To the entire <code>company</code> scope.</p></div>
<div><h4>Running a separate node</h4><p>One node per partition is operationally expensive.</p></div>

</div>

<div className="stigmem-keypoint">

**Memory Gardens fill this gap.**

A garden is a named, ACL'd logical partition that sits *inside* a
scope. It adds fine-grained, membership-based read/write control on
top of the existing scope model.

</div>

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

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Result</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>garden_id</code> not provided</dt>
<dt><span className="stigmem-fields__type">scope-only</span></dt>
<dd>Normal scope enforcement only; fact is not garden-tagged.</dd>
</div>

<div>
<dt>caller is <code>admin</code>/<code>writer</code></dt>
<dt><span className="stigmem-fields__type">allowed</span></dt>
<dd>Write succeeds if scopes match.</dd>
</div>

<div>
<dt>caller is <code>reader</code></dt>
<dt><span className="stigmem-fields__type">HTTP 403</span></dt>
<dd>Write permission required.</dd>
</div>

<div>
<dt>caller not a member</dt>
<dt><span className="stigmem-fields__type">HTTP 403</span></dt>
<dd>Not a member of this garden.</dd>
</div>

<div>
<dt>fact scope ≠ garden scope</dt>
<dt><span className="stigmem-fields__type">HTTP 422</span></dt>
<dd>Scope mismatch.</dd>
</div>

<div>
<dt>garden not found</dt>
<dt><span className="stigmem-fields__type">HTTP 404</span></dt>
<dd>—</dd>
</div>

</div>

**Read access:**

A fact with `garden_id` set is returned in query results ONLY if the caller:

<ol className="stigmem-steps">
<li>Passes normal scope enforcement (has <code>read</code> permission).</li>
<li>Holds at least <code>reader</code> role in the garden.</li>
</ol>

<div className="stigmem-keypoint">

**Non-members cannot enumerate gardens they do not belong to.**

When querying by `garden_id` filter, non-members receive `HTTP 403`.
When querying by entity/relation without a `garden_id` filter,
garden-tagged facts are silently excluded.

</div>

**Admin operations:**

<div className="stigmem-fields">

<div>
<dt>Operation</dt>
<dt><span className="stigmem-fields__type">Required role</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Add member</dt>
<dt><span className="stigmem-fields__type">admin</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Change member role</dt>
<dt><span className="stigmem-fields__type">admin</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Remove member</dt>
<dt><span className="stigmem-fields__type">admin</span></dt>
<dd>Cannot remove the last admin.</dd>
</div>

<div>
<dt>Delete garden</dt>
<dt><span className="stigmem-fields__type">admin</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Read member roster</dt>
<dt><span className="stigmem-fields__type">reader or above</span></dt>
<dd>—</dd>
</div>

<div>
<dt>List accessible gardens</dt>
<dt><span className="stigmem-fields__type">any valid API key</span></dt>
<dd>Non-admin callers see only gardens where they are members.</dd>
</div>

</div>

### §17.4 Garden Lifecycle {#section-17-4}

<ol className="stigmem-steps">
<li><strong>Create:</strong> Any principal with <code>write</code> permission on the node can create a garden. Creator is automatically <code>admin</code>.</li>
<li><strong>Invite:</strong> Garden admin adds members via <code>POST /v1/gardens/:id/members</code>.</li>
<li><strong>Write facts:</strong> Members with <code>writer</code> or <code>admin</code> role include <code>garden_id</code> in <code>POST /v1/facts</code>.</li>
<li><strong>Query:</strong> Members include <code>garden_id</code> query param in <code>GET /v1/facts</code>.</li>
<li><strong>Retract:</strong> Garden writers/admins retract facts using the normal retraction pattern (assert with <code>confidence=0.0</code>); must include the same <code>garden_id</code>.</li>
<li><strong>Delete:</strong> Garden admin deletes with <code>DELETE /v1/gardens/:id</code>. Associated facts become orphaned (garden_id becomes a dangling reference; surfaced by lint, §14).</li>
</ol>

### §17.5 Relationship to Scope {#section-17-5}

Gardens and scopes are orthogonal, layered controls:

```
Scope (coarse, node-global):  local | team | company | public
Garden (fine, named subset):  any subset of principals within a scope
```

A garden's `scope` field declares which scope its facts inhabit. This means:

<div className="stigmem-grid">

<div><h4>Garden ACL trumps scope</h4><p>A <code>company</code>-scoped garden's facts are not visible to every company-level reader; non-members are excluded.</p></div>
<div><h4>Garden isolation prevents federation</h4><p>A <code>public</code>-scoped garden's facts would normally federate, but garden isolation prevents federation (§6 invariant). Gardens are local-first by design.</p></div>
<div><h4>Untagged facts unaffected</h4><p>Facts without <code>garden_id</code> continue to use scope-only access control.</p></div>

</div>

### §17.6 Conventions {#section-17-6}

**Relation namespace:** Garden membership metadata is stored as system facts using the `garden:` prefix. The node writes these automatically when callers add or remove members via the garden management endpoints; they use `source="system:stigmem"` so that attestation checks (§18) can distinguish operator-managed membership from agent-authored assertions. The `garden:member` relation links the garden to a member entity, while `garden:role:<entity_uri>` records the member's permission level (reader, writer, or admin).

```
(entity=<garden_id>, relation="garden:member",   value={type:"ref", v:<member_entity_uri>}, source="system:stigmem", ...)
(entity=<garden_id>, relation="garden:role:<entity_uri>", value={type:"string", v:"writer"}, ...)
```

<div className="stigmem-keypoint">

**System facts in `garden:` MUST NOT be modified directly by callers.**

These system facts are written automatically on membership changes.
The `garden:` prefix is reserved in the namespace registry (§9.1).

</div>

---
