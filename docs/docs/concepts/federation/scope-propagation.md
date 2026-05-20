---
title: Scope Propagation Invariants
sidebar_label: Scope Propagation
audience: Integrator
---

# Scope Propagation Invariants

<p className="stigmem-meta"><span>3 min read</span><span>Node operator · Federation architect</span><span>Spec-05-Federation-Trust</span></p>

<div className="stigmem-lead">

**What this page is**

How Stigmem enforces non-escalation of scope at every relay hop —
and why <code>company</code>-scoped facts cannot be re-federated to
third nodes by default.

</div>

:::info Modular spec
Scope propagation invariants are covered by Spec-05-Federation-Trust
scope-propagation invariants. These close the pre-reset open
question about `company`-scoped fact re-federation. **All conforming
nodes MUST implement the transitive scope non-escalation and
company-scope re-federation invariants.**
:::

## The core principle · scope cannot escalate at relay hops

A fact's scope is an **authorization grant**, not a label. When a
`team`-scoped fact enters node B from node A, it means "A permits B
to see this fact as a team fact." Node B cannot widen that grant —
it cannot re-federate the fact to node C as if C had the same
authorization A gave to B.

<div className="stigmem-keypoint">

**Invariant 6.8.1 — Transitive Scope Non-Escalation.**

A fact's scope MUST NOT be escalated at any relay hop. Each relay
node intersects the fact's scope against its own PeerDeclaration
<code>allowed_scopes</code> before including the fact in a pull
response. **The narrower scope wins.**

</div>

## How scope propagation works in practice

When node B ingests a federated fact from node A, it records two
internal metadata fields (never re-replicated).

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Records</span></dt>
<dd>Use</dd>
</div>

<div>
<dt><code>origin_node_id</code></dt>
<dt><span className="stigmem-fields__type">originating node</span></dt>
<dd>The node that originally asserted the fact.</dd>
</div>

<div>
<dt><code>origin_allowed_scopes</code></dt>
<dt><span className="stigmem-fields__type">A's grant to B</span></dt>
<dd>The scope grant A's PeerDeclaration extended to B.</dd>
</div>

</div>

When C later pulls from B, B intersects:

```
fact.scope ∩ origin_allowed_scopes ∩ C's PeerDeclaration allowed_scopes
```

If the intersection is empty (e.g., A granted B `team` scope but C's
PeerDeclaration only has `local`), the fact is excluded from B's
pull response to C — not an error, just a scope filter.

## Company-scoped facts · no re-federation

This invariant resolves the pre-reset company-scope re-federation
question directly.

<div className="stigmem-keypoint">

**Invariant 6.8.2.**

A node that receives a <code>company</code>-scoped fact MUST NOT
re-federate it to any third node, regardless of the third node's
PeerDeclaration.

</div>

**Why:** `company` scope is an authorization grant to a specific
peer (node B), not to B's entire downstream network. If node A
shares a company fact with B, A is trusting B — not B's federation
partners.

**Implementation:** ingested company-scoped facts are tagged
`re_federation_blocked=true` at ingest time. These facts are
excluded from all outgoing federation pull responses.

**Exception:** Set `STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=true`
to lift this restriction. Use with care — this must be agreed
bilaterally with the origin node, and all re-federation events are
written to the federation audit log.

```bash
# Only enable if origin node has explicitly consented
STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=false  # default; recommended
```

## Edge cases

### Mixed-scope batches

When a push batch contains facts with different scopes, scope
violations on individual facts **do not reject the entire batch**.
Each fact is evaluated independently. Violating facts are rejected
(HTTP 403 per-fact, `event_type="scope_violation"` in audit log);
valid facts in the batch proceed normally.

### Scope of contradiction meta-facts

`stigmem:conflict:between` meta-facts inherit the scope of the
conflicting source facts. When two facts with different scopes
conflict, the narrower scope wins.

<div className="stigmem-fields">

<div>
<dt>Fact A scope</dt>
<dt><span className="stigmem-fields__type">Fact B scope</span></dt>
<dd>Conflict meta-fact scope</dd>
</div>

<div>
<dt><code>company</code></dt>
<dt><span className="stigmem-fields__type"><code>team</code></span></dt>
<dd><code>team</code></dd>
</div>

<div>
<dt><code>public</code></dt>
<dt><span className="stigmem-fields__type"><code>local</code></span></dt>
<dd><code>local</code></dd>
</div>

<div>
<dt><code>team</code></dt>
<dt><span className="stigmem-fields__type"><code>team</code></span></dt>
<dd><code>team</code></dd>
</div>

</div>

This prevents contradiction meta-facts from escalating scope beyond
what the narrower source fact permitted.

### Out-of-scope fact from peer

If a peer pushes a `team`-scoped fact but the receiving node's
PeerDeclaration for that peer does not include `"team"` in
`allowed_scopes`:

<ol className="stigmem-steps">
<li>Node returns HTTP 403 on the specific fact.</li>
<li><code>event_type="scope_violation"</code> is written to the federation audit log.</li>
<li>The PeerDeclaration is authoritative — local environment flags cannot override it.</li>
</ol>

<div className="stigmem-keypoint">

**`STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION` controls re-federation policy, not what scopes a peer is permitted to send.**

Peer scope grants are in the PeerDeclaration, not environment flags.

</div>

## Audit log entries

Scope violations produce structured entries in the federation audit
log:

```json
{
  "event_type": "scope_violation",
  "fact_id": "...",
  "peer_id": "node-b-peer-id",
  "claimed_scope": "team",
  "allowed_scopes": ["local"],
  "timestamp": "2026-05-02T18:10:00Z"
}
```

Monitor these entries to detect misconfigured PeerDeclarations before
they cause silent data loss.

## Invariant summary

<div className="stigmem-fields">

<div>
<dt>Invariant</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Requirement</dd>
</div>

<div>
<dt>6.8.1 — Transitive scope non-escalation</dt>
<dt><span className="stigmem-fields__type">always enforced</span></dt>
<dd>MUST: intersect scopes at each relay hop.</dd>
</div>

<div>
<dt>6.8.2 — Company re-federation restriction</dt>
<dt><span className="stigmem-fields__type">enforced; opt-out via env var</span></dt>
<dd>MUST: block re-federation of company-scoped facts.</dd>
</div>

<div>
<dt>6.8.3 — Mixed-scope batches</dt>
<dt><span className="stigmem-fields__type">always enforced</span></dt>
<dd>MUST: per-fact evaluation, not all-or-nothing.</dd>
</div>

<div>
<dt>6.8.3 — Conflict meta-fact scope</dt>
<dt><span className="stigmem-fields__type">always enforced</span></dt>
<dd>MUST: inherit narrower scope of conflicting facts.</dd>
</div>

</div>

## See also

<div className="stigmem-next">

<a href="./federation">
<strong>Concepts</strong>
<span>Federation overview</span>
<small>PeerDeclaration registration and pull protocol.</small>
</a>

<a href="./relay-backpressure">
<strong>Concepts</strong>
<span>Relay backpressure</span>
<small>Lag signals in N-node topologies.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md">
<strong>Spec-05.8</strong>
<span>Scope propagation invariants</span>
<small>Normative invariant text.</small>
</a>

</div>
