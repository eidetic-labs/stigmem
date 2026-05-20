---
title: Concepts
sidebar_position: 2
---

# Concepts

<p className="stigmem-meta"><span>3 min read</span><span>For everyone</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll find here**

The core ideas behind the Stigmem protocol — how facts, scopes,
federation, recall, and lifecycle work together. Start here when you
want to understand the protocol from the inside out.

</div>

<div className="stigmem-keypoint">

**The protocol is the contract.**

Every Stigmem node speaks the same seven-field fact tuple, the same
HLC time, the same scope boundary, and the same conflict semantics.
Implementations differ; the contract does not.

</div>

## Sections

<div className="stigmem-grid">

<div>
<h4><a href="./facts/immutable-typed-facts">Facts</a></h4>
<p>The atomic unit of knowledge — entity · relation · value · source · timestamp · confidence · scope. Immutable, append-only, audit-traceable.</p>
</div>

<div>
<h4><a href="./federation/federation-handshake">Federation</a></h4>
<p>How peer nodes exchange facts across trust boundaries. Signed handshake, scope-aware replication, conflict reporting.</p>
</div>

<div>
<h4><a href="./hybrid-logical-clocks">Hybrid logical clocks</a></h4>
<p>Total ordering across the federation without a central authority. Bounded skew, mergeable timestamps.</p>
</div>

<div>
<h4><a href="./memory-garden">Memory garden</a></h4>
<p>The opinionated curation surface — what to keep, what to let decay, what to surface in recall.</p>
</div>

<div>
<h4><a href="./security-model">Security model</a></h4>
<p>Capability tokens, prompt-injection boundary, source attestation, and the threat surface adopters need to reason about.</p>
</div>

<div>
<h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/recall-graph">Recall</a></h4>
<p><em>Experimental.</em> Retrieving relevant facts at query time via embeddings, subscriptions, and memory cards.</p>
</div>

<div>
<h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/decay">Lifecycle</a></h4>
<p><em>Experimental.</em> Decay, synthesis, time-travel queries, and the right to be forgotten.</p>
</div>

</div>

## What's next

<div className="stigmem-next">

<a href="./overview">
<strong>Read</strong>
<span>Learn</span>
<small>The end-to-end tour from outside in — fabric, fact tuple, scope, v0.9.0a2 surface.</small>
</a>

<a href="../get-started/">
<strong>Hands-on</strong>
<span>Get Started</span>
<small>Install a node, assert your first fact, connect an SDK.</small>
</a>

<a href="../spec/">
<strong>Reference</strong>
<span>Specification</span>
<small>The protocol-level text every implementation conforms to.</small>
</a>

</div>
