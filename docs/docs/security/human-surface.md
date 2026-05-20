---
title: Human Surface (Web UI)
sidebar_label: Human Surface (Web UI)
audience: Integrator
---

# Human Surface (Web UI)

<p className="stigmem-meta"><span>3 min read</span><span>Curator · Contributor · Consumer</span><span>Served at <code>/ui</code></span></p>

<div className="stigmem-lead">

**What this page is**

The Web UI is a single-page application served by the node at `/ui`.
Built with Alpine.js and Tailwind CSS (both loaded from CDN — no
separate build step or install required). All actions map directly
to the REST API; anything you do in the UI you can reproduce with
`curl`.

</div>

## Quick start

<ol className="stigmem-steps">
<li>Navigate to <code>http://&lt;node-host&gt;:8000/ui</code>.</li>
<li>Enter your node's base URL and your API key in the <strong>Connection</strong> bar at the top, then click <strong>Connect</strong>.</li>
<li>The header confirms your identity (<code>Signed in as &lt;entity_uri&gt;</code>) and shows your permission badges.</li>
</ol>

Your credentials are saved in `localStorage` (`sm_url` / `sm_key`) so
you do not need to re-enter them on reload.

:::info Obtaining an API key
Use the [OIDC / SSO](https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso)
exchange flow if your organisation runs an IdP, or ask your node
operator to provision a static key. See [Authentication](./authentication)
for the full key model.
:::

## Personas and roles

<div className="stigmem-fields">

<div>
<dt>Role</dt>
<dt><span className="stigmem-fields__type">Access</span></dt>
<dd>What they can do in the UI</dd>
</div>

<div>
<dt><strong>Curator</strong></dt>
<dt><span className="stigmem-fields__type">garden admin</span></dt>
<dd>All tabs; retract any fact; manage garden members and roles. Approves contested facts.</dd>
</div>

<div>
<dt><strong>Contributor</strong></dt>
<dt><span className="stigmem-fields__type">write access to one or more gardens</span></dt>
<dd>Facts, Assert, Audit Log tabs; retract own facts.</dd>
</div>

<div>
<dt><strong>Consumer</strong></dt>
<dt><span className="stigmem-fields__type">read-only</span></dt>
<dd>Facts and Audit Log tabs; no Assert or retract.</dd>
</div>

</div>

The UI detects your role from `GET /v1/me` — write controls are
hidden or disabled if your key lacks the `write` permission.

## Tabs

### Facts

Browse and search the fact store.

**Filters:**

<div className="stigmem-fields">

<div>
<dt>Filter</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt>Entity URI</dt>
<dt><span className="stigmem-fields__type">exact / prefix</span></dt>
<dd>Match on <code>entity</code>.</dd>
</div>

<div>
<dt>Relation</dt>
<dt><span className="stigmem-fields__type">exact</span></dt>
<dd>Match on <code>relation</code>.</dd>
</div>

<div>
<dt>Scope</dt>
<dt><span className="stigmem-fields__type">dropdown</span></dt>
<dd><code>local</code>, <code>team</code>, <code>company</code>, <code>public</code>.</dd>
</div>

<div>
<dt>Source</dt>
<dt><span className="stigmem-fields__type">exact</span></dt>
<dd>Match on <code>source</code>.</dd>
</div>

<div>
<dt>Min confidence</dt>
<dt><span className="stigmem-fields__type">numeric 0–1</span></dt>
<dd>Default: no filter.</dd>
</div>

<div>
<dt>Include contradicted</dt>
<dt><span className="stigmem-fields__type">checkbox</span></dt>
<dd>Off by default.</dd>
</div>

</div>

Results are paginated. The **Load more** button appends the next page.

**Columns:** Entity, Relation, Value, Scope (badge), Confidence,
Timestamp, Status (conflicted / retracted), Actions.

**Actions per row:**

<div className="stigmem-grid">

<div><h4>Detail</h4><p>Opens a modal with all fields including <code>id</code>, <code>valid_until</code>, and HLC.</p></div>
<div><h4>Retract</h4><p>Opens a confirmation modal with an optional reason field. Sends <code>POST /v1/facts</code> with <code>confidence: 0</code>; the reason is stored as a <code>stigmem:retract:reason</code> fact keyed on the retracted fact's ID.</p></div>

</div>

### Assert

Create new facts manually.

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Entity URI</dt>
<dt><span className="stigmem-fields__type">required, free-text</span></dt>
<dd></dd>
</div>

<div>
<dt>Relation</dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Should follow namespace registry (Spec-16-Namespace-Registry).</dd>
</div>

<div>
<dt>Value type</dt>
<dt><span className="stigmem-fields__type">selector</span></dt>
<dd><code>string</code>, <code>text</code>, <code>number</code>, <code>boolean</code>, <code>datetime</code>, <code>ref</code>, <code>null</code>.</dd>
</div>

<div>
<dt>Value</dt>
<dt><span className="stigmem-fields__type">type-driven</span></dt>
<dd>Input adapts to the selected type.</dd>
</div>

<div>
<dt>Source URI</dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Pre-filled from <code>GET /v1/me</code> if you are authenticated.</dd>
</div>

<div>
<dt>Scope</dt>
<dt><span className="stigmem-fields__type">selector</span></dt>
<dd><code>local</code>, <code>team</code>, <code>company</code>, <code>public</code>.</dd>
</div>

<div>
<dt>Confidence</dt>
<dt><span className="stigmem-fields__type">slider 0–1</span></dt>
<dd>Default: 1.0.</dd>
</div>

<div>
<dt>Valid until</dt>
<dt><span className="stigmem-fields__type">optional ISO 8601</span></dt>
<dd></dd>
</div>

</div>

On submit, the response shows the new fact ID and warns if the
assertion contradicts an existing fact.

### Audit Log

A chronological view of all fact mutations, including retractions and
contradictions.

**Filters:** Source URI (`My assertions` pre-fill button), Entity,
Scope, Include contradicted.

Useful for compliance reviews and debugging — equivalent to
`GET /v1/facts?include_contradicted=true&order=hlc_desc`.

### Gardens

Manage memory gardens (named, ACL-controlled partitions above scope —
see Spec-02-Scopes-and-ACL).

**List view:** Cards show slug, display name, scope badge, and
creation time. Click a card to open the detail view.

**Detail view:**

<div className="stigmem-fields">

<div>
<dt>Section</dt>
<dt><span className="stigmem-fields__type">Contents</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Garden info</dt>
<dt><span className="stigmem-fields__type">metadata</span></dt>
<dd>slug, display name, description, <code>garden_id</code> (UUID), <code>created_by</code>.</dd>
</div>

<div>
<dt>Members table</dt>
<dt><span className="stigmem-fields__type">membership</span></dt>
<dd>Entity URI, Role (editable dropdown for admins), Added by, Added at, Remove button.</dd>
</div>

<div>
<dt>Add Member button</dt>
<dt><span className="stigmem-fields__type">modal</span></dt>
<dd>Entity URI + role selector (<code>admin</code>, <code>writer</code>, <code>reader</code>).</dd>
</div>

<div>
<dt>Browse facts link</dt>
<dt><span className="stigmem-fields__type">navigation</span></dt>
<dd>Opens Facts tab pre-filtered to this garden's scope.</dd>
</div>

</div>

**Create garden:** Click **+ New Garden**. Provide a slug (lowercase
alphanumeric + hyphens, 1–64 chars), display name, scope, and
optional description. The creator is automatically added as `admin`.

**Role management:** Admins can change any member's role via the
dropdown in the members table. The last admin cannot be demoted or
removed (the node returns `403`).

## API endpoints called

Every UI action maps to a REST endpoint.

<div className="stigmem-fields">

<div>
<dt>UI action</dt>
<dt><span className="stigmem-fields__type">Method</span></dt>
<dd>Endpoint</dd>
</div>

<div>
<dt>Connect / check identity</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/me</code></dd>
</div>

<div>
<dt>Facts tab query</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/facts?{`{filters}`}</code></dd>
</div>

<div>
<dt>Assert a fact</dt>
<dt><span className="stigmem-fields__type">POST</span></dt>
<dd><code>/v1/facts</code></dd>
</div>

<div>
<dt>Retract a fact</dt>
<dt><span className="stigmem-fields__type">POST</span></dt>
<dd><code>/v1/facts</code> with <code>confidence: 0</code> + reason fact.</dd>
</div>

<div>
<dt>Audit Log query</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/facts?include_contradicted=true</code></dd>
</div>

<div>
<dt>List gardens</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/gardens</code></dd>
</div>

<div>
<dt>Garden detail</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/gardens/{`{slug}`}</code></dd>
</div>

<div>
<dt>Create garden</dt>
<dt><span className="stigmem-fields__type">POST</span></dt>
<dd><code>/v1/gardens</code></dd>
</div>

<div>
<dt>Delete garden</dt>
<dt><span className="stigmem-fields__type">DELETE</span></dt>
<dd><code>/v1/gardens/{`{slug}`}</code></dd>
</div>

<div>
<dt>List members</dt>
<dt><span className="stigmem-fields__type">GET</span></dt>
<dd><code>/v1/gardens/{`{slug}`}/members</code></dd>
</div>

<div>
<dt>Add member</dt>
<dt><span className="stigmem-fields__type">POST</span></dt>
<dd><code>/v1/gardens/{`{slug}`}/members</code></dd>
</div>

<div>
<dt>Change role</dt>
<dt><span className="stigmem-fields__type">PATCH</span></dt>
<dd><code>/v1/gardens/{`{slug}`}/members/{`{entity_uri}`}</code></dd>
</div>

<div>
<dt>Remove member</dt>
<dt><span className="stigmem-fields__type">DELETE</span></dt>
<dd><code>/v1/gardens/{`{slug}`}/members/{`{entity_uri}`}</code></dd>
</div>

</div>

## See also

<div className="stigmem-next">

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso">
<strong>Experimental</strong>
<span>OIDC / SSO integration</span>
<small>Sign in via your organisation's IdP instead of a static key.</small>
</a>

<a href="./authentication">
<strong>Security</strong>
<span>Authentication</span>
<small>Full API key and permission model.</small>
</a>

<a href="../concepts/facts/asserting-facts">
<strong>Concepts</strong>
<span>Asserting facts</span>
<small><code>curl</code> examples for the same operations.</small>
</a>

</div>
