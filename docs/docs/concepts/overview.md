---
title: Learn
sidebar_label: Learn
description: Understand Stigmem — the federated knowledge fabric, the seven-field fact, the scope model, and the v0.9.0a2 surface.
---

# Learn

<p className="stigmem-meta"><span>5 min read</span><span>For everyone</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll find here**

A tour of Stigmem from the outside in — what the federated knowledge
fabric is, the seven-field fact tuple every node speaks, the scope
model that decides what crosses organizational boundaries, and where
the v0.9.0a2 alpha stops being trustworthy.

</div>

<div className="stigmem-keypoint">

**Stigmergy + Memory.**

Agents don't communicate directly. They leave typed, provenance-tagged
traces in a shared substrate; other agents — later, elsewhere, in
different organizations — read those traces and act. The knowledge
environment carries the coordination signal.

</div>

## §1 · The fabric in one tuple

Every Stigmem record is the same immutable seven-field tuple. The
shape is the contract; everything else is policy on top of it.

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>Stable identifier for the subject — repo · person · project · deployment · artifact.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>Namespaced predicate. Reserved prefixes are protected; authors pick the rest.</dd>
</div>

<div>
<dt><code>value</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>The asserted content. Typed and validated against the relation's schema when one is registered.</dd>
</div>

<div>
<dt><code>source</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>Who wrote it — <code>agent:</code>, <code>user:</code>, <code>system:</code>. Signable; source-attestation can be enforced.</dd>
</div>

<div>
<dt><code>timestamp</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd>A hybrid logical clock stamp. Total order across the federation without a central authority.</dd>
</div>

<div>
<dt><code>confidence</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd><code>0.0–1.0</code> belief score, with attached trust class. Filterable at query time.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">always</span></dt>
<dd><code>local</code> · <code>team</code> · <code>company</code> · <code>public</code>. Replication crosses scope boundaries only under explicit signed permission.</dd>
</div>

</div>

## §2 · How the protocol composes

<div className="stigmem-grid">

<div>
<h4>Immutability</h4>
<p>Facts are append-only. Updates produce new facts; the prior fact stays queryable for audit and time-travel.</p>
</div>

<div>
<h4>Federation</h4>
<p>Nodes peer over a signed handshake. Facts replicate across scopes only under explicit permission — never silently.</p>
</div>

<div>
<h4>Hybrid logical clocks</h4>
<p>Each fact carries an HLC stamp. Bounded skew across the federation; total ordering without a central authority.</p>
</div>

<div>
<h4>Provenance</h4>
<p>Every fact records who wrote it and which signed source attested. Cryptographic chain back to the asserter.</p>
</div>

<div>
<h4>Contradictions, not overwrites</h4>
<p>When two facts assert incompatible values for the same <code>(entity, relation, scope)</code>, a conflict record opens. Both sources remain queryable. Resolution is explicit.</p>
</div>

<div>
<h4>Expiry &amp; decay</h4>
<p>Facts can carry an expiry. Stale facts age out of recall while remaining queryable for audit.</p>
</div>

</div>

## §3 · Where Stigmem sits

<div className="stigmem-keypoint">

**Above orchestration platforms, not next to them.**

Stigmem does not replace company orchestration platforms, agent
runtimes, or tool protocols like MCP. It sits above them — the shared
cognitive layer they all reason over.

</div>

## §4 · The v0.9.0a2 surface

The shipped alpha is a working reference node, a documented HTTP API,
conformance fixtures, and SDK stubs in three languages. Honest about
what's there and what's still in flight.

<div className="stigmem-decision">

<div>
<h4>Implemented</h4>
<ul>
<li>Reference node (Python) with HTTP API</li>
<li>OpenAPI spec + conformance fixtures</li>
<li>Python · TypeScript · Go SDK stubs</li>
<li>Signed peer handshake for federation</li>
<li>Conflict records as first-class</li>
<li>HLC timestamps with bounded skew</li>
</ul>
</div>

<div>
<h4>Future hardened-core work</h4>
<ul>
<li>mTLS-default federation peering</li>
<li>Full capability-level validation for cross-org instructions</li>
<li>Bounded HLC skew enforcement</li>
<li>Per-principal rate limits</li>
<li>Persistent audit log with retention</li>
<li>Operator hardening guide</li>
</ul>
</div>

</div>

<div className="stigmem-keypoint">

**Single-org, single-node is the only currently-supported pattern.**

Cross-organizational federation in adversarial settings is **not yet
safe**. See [LIMITATIONS](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md)
for the adopter-facing companion to the
[threat model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

</div>

## What's next

<div className="stigmem-next">

<a href="./">
<strong>Browse</strong>
<span>Concepts</span>
<small>The deeper concept pages — facts, federation, recall, lifecycle.</small>
</a>

<a href="../get-started/">
<strong>Hands-on</strong>
<span>Get Started</span>
<small>Install a local node, assert your first fact, run a conformance fixture.</small>
</a>

<a href="../security/">
<strong>Read</strong>
<span>Security</span>
<small>Risk register, threat model, hardening — the honest scope evaluators want first.</small>
</a>

</div>
