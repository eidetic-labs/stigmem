# Architecture Decision Records (ADRs)

<p className="stigmem-meta"><span>4 min read</span><span>Reference</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll find here**

The full ADR index, the format Stigmem ADRs follow, the lifecycle
rules, and when to write a new one. ADRs are immutable after
acceptance — supersession is how the record evolves.

</div>

<div className="stigmem-keypoint">

**One decision per ADR. Immutable after acceptance.**

When circumstances change, write a new ADR that supersedes the old
one. Don't edit an accepted ADR — that breaks the institutional
memory the format exists to preserve.

</div>

## What is an ADR?

**ADR** stands for **Architecture Decision Record** (sometimes
"Architectural Decision Record" — the terms are interchangeable).

An ADR is a short, dated, immutable document that captures **a single
significant decision**, why we made it, what alternatives we
considered, and what the consequences are. ADRs live in the repo
under `docs/adr/`, are numbered sequentially (`ADR-001`, `ADR-002`,
...), and form a versioned record of how the project's architecture
evolved.

The format was popularized by Michael Nygard in a 2011 blog post and
has become standard practice in infrastructure and platform projects.

## Why we use them

<div className="stigmem-grid">

<div>
<h4>Decisions get re-litigated</h4>
<p>Six months from now someone will ask "why did we move tombstones to experimental?" Without an ADR the answer lives in chat history. With one it lives in a versioned document with the reasoning intact.</p>
</div>

<div>
<h4>Contract for scope discipline</h4>
<p>When <code>ADR-002</code> says "v1 critical-path scope is exactly this list," any proposal to add something must either accept the constraint or write an amendment. The amendment requirement is productive friction.</p>
</div>

<div>
<h4>External adopters read them</h4>
<p>Threat models tell evaluators what we're worried about; ADRs tell them what we've decided and why. The combination is what credibility looks like in infrastructure projects.</p>
</div>

</div>

## Standard structure

Every ADR follows the same template:

```markdown
# ADR-NNN: Short noun phrase

**Status:** Proposed | Accepted | Superseded by ADR-NNN | Deprecated
**Date:** YYYY-MM-DD
**Authors:** name(s)
**Supersedes:** (if applicable) ADR-NNN
**Related:** (if applicable) ADR-NNN, links to other artifacts

## Context

What is the situation? What forces are at play? Why are we deciding this now?
Be specific. Name the constraints, the prior art, the deadline if there is one.

## Decision

The call we made, in active voice. "We will..."
Be specific. "We will use a federated architecture" is a slogan, not a decision.
"We will use mTLS-default federation with capability tokens scoped to
verb+object pairs" is a decision.

## Alternatives considered

What else did we look at, and why didn't we pick it?
This section is the institutional memory; future maintainers will thank you.

## Consequences

What becomes easier? What becomes harder? What new risks emerge?
Be honest about the costs. ADRs that only list benefits are marketing docs.
```

## Rules

<ol className="stigmem-steps">
<li><strong>ADRs are immutable after acceptance.</strong> When circumstances change, write a new ADR that supersedes the old one. Don't edit an accepted ADR.</li>
<li><strong>One decision per ADR.</strong> Two related decisions get two ADRs that reference each other.</li>
<li><strong>Specific over abstract.</strong> ADRs that describe a <em>concrete</em> decision survive contact with implementation. ADRs that describe a <em>direction</em> don't.</li>
<li><strong>Numbered sequentially, never reused.</strong> If <code>ADR-005</code> is rejected, the number is still retired. Future ADRs are <code>ADR-006</code> onwards.</li>
<li><strong>Status changes are themselves a decision.</strong> When an ADR moves from <code>Accepted</code> to <code>Superseded</code>, the new ADR captures that change with a <code>Supersedes:</code> reference.</li>
<li><strong>Approval: two contributors or the founder alone.</strong> Founder solo-approval exists because the project has a small team. When the founder signs off alone, they take responsibility for the validation discipline that two-person review otherwise provides. See ADR-001 § <em>Contributor approval rule</em> for the full statement.</li>
</ol>

## Lifecycle

```text
Proposed → discussion/review → Accepted → (later) Superseded by ADR-NNN
 ↘ (rare) Deprecated
```

Most ADRs are merged in `Accepted` status after pair review.
`Proposed` is used when a decision is in flight and not yet committed
— useful for getting feedback before locking in.

## When to write an ADR

<div className="stigmem-decision">

<div>
<h4>Write one when</h4>
<ul>
<li><strong>Architectural blast radius</strong> — affects more than one module, surface, or team.</li>
<li><strong>Non-obvious</strong> — a future reader might reasonably ask "why did they do it this way?"</li>
<li><strong>Has alternatives</strong> — a real choice between two or more options existed.</li>
<li><strong>Affects external contracts</strong> — wire format, API surface, security model, deployment story.</li>
<li><strong>Closes a documented gap</strong> — resolves a specific issue from an audit, threat model, or operator report.</li>
</ul>
</div>

<div>
<h4>Don't write one for</h4>
<ul>
<li>Routine implementation choices ("we used a Python <code>dict</code> here").</li>
<li>Library version bumps.</li>
<li>Bug fixes.</li>
<li>Local style or naming preferences.</li>
</ul>
</div>

</div>

## Cross-references

Stigmem ADRs frequently reference:

<div className="stigmem-grid">

<div>
<h4>Threat model</h4>
<p><a href="../../spec/security/threat-model.md">spec/security/threat-model.md</a> — for security decisions.</p>
</div>

<div>
<h4>Strengthening plan</h4>
<p><a href="../plans/strengthening-plan.md">docs/plans/strengthening-plan.md</a> — for delivery-timeline decisions.</p>
</div>

<div>
<h4>Audit findings</h4>
<p>e.g. <code>stigmem/openclaw/audit.md</code> — for ADRs that close specific issues.</p>
</div>

<div>
<h4>Other ADRs</h4>
<p>For decisions that build on or supersede earlier ones.</p>
</div>

</div>

When referencing, use relative links from the ADR's location.

## Index

<div className="stigmem-adr-grid">

<a className="stigmem-adr-card" href="./001-versioning">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-001</span>
<strong>Versioning, phases, and stability commitments</strong>
<span>The phased delivery model and how stability commitments map onto pre-1.0 alpha / beta / RC labels.</span>
</a>

<a className="stigmem-adr-card" href="./002-v1-scope">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-002</span>
<strong>v1 critical-path scope</strong>
<span>The exact list of features on the v1 critical path. Any addition requires an amendment.</span>
</a>

<a className="stigmem-adr-card" href="./003-prompt-injection">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-003</span>
<strong>Capability-based prompt-injection handling</strong>
<span><code>interpret_as: content | instruction</code> at the storage layer, capability tokens for cross-org instructions.</span>
</a>

<a className="stigmem-adr-card" href="./004-federation-observability">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-004</span>
<strong>Federation observability and incident response</strong>
<span>Per-peer drift tracking, pull-loop visibility, and the incident-response surface federation operators need.</span>
</a>

<a className="stigmem-adr-card" href="./005-docs-ia">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-005</span>
<strong>Documentation information architecture</strong>
<span>Learn / Build / Operate / Secure as the top-level IA. Lead Secure with the risk register.</span>
</a>

<a className="stigmem-adr-card" href="./006-batch-assert">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-006</span>
<strong>Batch-assert API for transactional multi-fact writes</strong>
<span>Atomic multi-fact write semantics. All-or-nothing commit, single audit entry.</span>
</a>

<a className="stigmem-adr-card" href="./007-argon2id">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-007</span>
<strong>Argon2id migration for API key hashing</strong>
<span>Replacement of the legacy hash with Argon2id; transparent migration on next valid use.</span>
</a>

<a className="stigmem-adr-card" href="./008-experimental-gates">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-008</span>
<strong>Re-introduction gates for v2.0.0-experimental features</strong>
<span>The gates an experimental surface must pass before re-entering the supported core.</span>
</a>

<a className="stigmem-adr-card" href="./009-repo-structure">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-009</span>
<strong>Repository structure and execution flow</strong>
<span>The repo layout — <code>spec/</code>, <code>node/</code>, <code>experimental/</code>, <code>adapters/</code>, <code>sdks/</code>, <code>docs/</code>.</span>
</a>

<a className="stigmem-adr-card" href="./010-modular-specs">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-010</span>
<strong>Modular per-topic specs with independent versioning</strong>
<span>Per-topic spec modules version independently. Each module carries its own changelog and compatibility table.</span>
</a>

<a className="stigmem-adr-card" href="./011-cross-cutting-extraction">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-011</span>
<strong>Plugin architecture for cross-cutting features (C1)</strong>
<span>Multi-tenant, billing, source attestation, embeddings → extracted plugin packages with stable registration surface.</span>
</a>

<a className="stigmem-adr-card" href="./012-version-aware-feature-exposure">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-012</span>
<strong>Version-aware feature exposure</strong>
<span>Per-feature minimum version gates, surface manifest delegation, version-aware OpenAPI annotations.</span>
</a>

<a className="stigmem-adr-card" href="./013-deprecation-policy">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-013</span>
<strong>Deprecation policy</strong>
<span>How features deprecate — warning windows, supported-version overlap, and the removal gate.</span>
</a>

<a className="stigmem-adr-card" href="./014-compatibility-matrix">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-014</span>
<strong>Compatibility matrix</strong>
<span><code>docs/compatibility-matrix.yaml</code> as the canonical compatibility table. Node × SDK × adapter version pairs.</span>
</a>

<a className="stigmem-adr-card" href="./015-adversarial-conformance-and-model-certification">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-015</span>
<strong>Adversarial conformance corpus and model certification</strong>
<span>The adversarial fixture suite plus model-certification framework that gates pre-stable releases.</span>
</a>

<a className="stigmem-adr-card" href="./016-storage-immutability-enforcement">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-016</span>
<strong>Storage immutability enforcement</strong>
<span>L1–L5 stack (append-only journal · SQLite triggers · CIDs · local hash chain · Sigstore Rekor) to mitigate admin-level tampering.</span>
</a>

<a className="stigmem-adr-card" href="./017-amendment-to-adr-011-cids-as-core">
<span className="stigmem-adr-card__status">Accepted · Amendment</span>
<span className="stigmem-adr-card__id">ADR-017</span>
<strong>Amendment: CIDs as core (not plugin)</strong>
<span>Content-addressable identifiers move out of the plugin layer and into the core fact surface.</span>
</a>

<a className="stigmem-adr-card" href="./018-security-documentation-colocation">
<span className="stigmem-adr-card__status">Accepted</span>
<span className="stigmem-adr-card__id">ADR-018</span>
<strong>Per-feature security documentation colocation</strong>
<span>Security notes ship next to the feature they describe — not in a single security appendix.</span>
</a>

<a className="stigmem-adr-card" href="./019-amendment-to-adr-001-prerelease-version-strings">
<span className="stigmem-adr-card__status">Accepted · Amendment</span>
<span className="stigmem-adr-card__id">ADR-019</span>
<strong>Amendment: PEP 440 / semver alpha-beta-rc convention</strong>
<span>Per-ecosystem spelling of pre-release labels; surface-manifest delegation; supersedes the original v1 → v0.9.0a1 reset.</span>
</a>

</div>

---

*Reference: Michael Nygard, "Documenting Architecture Decisions"
(2011). The format has been refined by many open-source projects; we
use the standard five-section variant with a sixth "Alternatives
considered" section because it materially improves institutional
memory.*
