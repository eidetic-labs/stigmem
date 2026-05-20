# ADR-008: Re-introduction gates for v2.0.0-experimental features

<p className="stigmem-meta"><span>4 min read</span><span>Accepted</span><span>Recorded 2026-05-06</span></p>

<div className="stigmem-lead">

**What this ADR decides**

A feature in `experimental/` returns to a default-on, supported state
only after passing five sequential gates: threat-model delta, ADR,
conformance vectors, 30-day external operator soak, documentation
parity across the four tabs.

</div>

<div className="stigmem-keypoint">

**Status: Accepted.**

The process is costly enough that scope-creep is real friction, but
not so costly that legitimately-ready features get permanently stuck.

</div>

**Date:** 2026-05-06 · **Authors:** Eidetic Labs · **Related:** [ADR-001](./001-versioning), [ADR-002](./002-v1-scope), `stigmem/plans/version-prioritization.md`

## Context

ADR-002 cuts the v1.0 critical-path scope to a defensible minimum and
moves the rest of the codebase to `experimental/`. The cut features
are not deleted — they are in the codebase, importable with explicit
opt-in, ready to return.

The question this ADR answers: **what does it take for an experimental
feature to come back?**

<div className="stigmem-keypoint">

**Without a structured process, one well-meaning PR away from v1.0 redux.**

Without structure, the project is one well-meaning PR away from
re-creating the retracted v1.0 — surface area accumulating faster
than correctness can keep up. With a structured process, every
feature's return is a deliberate decision with measurable gates, and
the v1.0 critical-path stability is preserved.

</div>

The five gates below are calibrated to that balance: each produces a
concrete artifact, none requires more than ~1 week of focused work,
and all five together represent the cost of bringing a feature to v1.x
quality.

## Decision

A feature in `experimental/` returns to a default-on, supported state
only after passing all five gates in order.

### Gate 1 · Threat-model delta

The feature's author writes a delta document at
`spec/security/deltas/<feature>-threat-model.md` that addresses:

<div className="stigmem-grid">

<div><h4>New trust boundaries</h4><p>Introduced or modified by the feature.</p></div>
<div><h4>New STRIDE entries</h4><p>Per affected boundary.</p></div>
<div><h4>New risks</h4><p>R-XX entries · likelihood · impact · priority · mitigations.</p></div>
<div><h4>Existing risks affected</h4><p>e.g. does it widen R-05 prompt-injection surface?</p></div>

</div>

The delta is reviewed and accepted (two contributors or the founder
alone, per ADR-001 §Contributor approval rule), then merged into the
threat model. A feature without a threat-model delta does not pass
Gate 1.

### Gate 2 · ADR drafted and merged

A new ADR captures:

<div className="stigmem-grid">

<div><h4>Design decision</h4><p>The feature's shape in v1.x.</p></div>
<div><h4>Migration story</h4><p>Which APIs change · which deprecations apply.</p></div>
<div><h4>Alternatives considered</h4></div>
<div><h4>Consequences</h4><p>Including new risks.</p></div>

</div>

The ADR may explicitly supersede or amend earlier ADRs (most often
ADR-002, the scope contract). Amendments follow the ADR-001
§Contributor approval rule.

### Gate 3 · Conformance vectors

The feature's wire-format and behavioral contract are encoded at
`data/conformance/<feature>/`:

<div className="stigmem-fields">

<div>
<dt>Vector kind</dt>
<dt><span className="stigmem-fields__type">Path</span></dt>
<dd>What it covers</dd>
</div>

<div>
<dt>Positive</dt>
<dt><span className="stigmem-fields__type"><code>data/conformance/&lt;feature&gt;/</code></span></dt>
<dd>Correct behavior.</dd>
</div>

<div>
<dt>Negative</dt>
<dt><span className="stigmem-fields__type"><code>data/conformance/&lt;feature&gt;/</code></span></dt>
<dd>Validation failures, error responses.</dd>
</div>

<div>
<dt>Adversarial</dt>
<dt><span className="stigmem-fields__type"><code>data/conformance/&lt;feature&gt;/adversarial/</code></span></dt>
<dd>Malformed inputs, injected payloads, edge cases the threat-model delta identified.</dd>
</div>

</div>

Vectors are wired into CI as a blocking job. PRs that break the
conformance suite fail to merge.

### Gate 4 · 30-day external operator soak

At least one external operator runs the feature in a real workload
for 30 days, with public bug reporting in the stigmem GitHub issues.

<div className="stigmem-keypoint">

**Operator must not be the feature author.**

Can be a community contributor, partner organization, or paid soak
partner — the only requirement is independence from the original
author.

</div>

The soak produces:

<div className="stigmem-grid">

<div><h4>Public <code>LOG.md</code> entry</h4><p>Summarizing what was found, what was fixed, what remains open.</p></div>
<div><h4>At least one closed issue</h4><p>Tagged <code>&lt;feature&gt;-soak-finding</code>. Soaks that produce zero findings are suspect — Gate 4 fails.</p></div>

</div>

### Gate 5 · Documentation parity

The feature has documentation across all four tabs (per
[ADR-005](./005-docs-ia)).

<div className="stigmem-fields">

<div>
<dt>Tab</dt>
<dt><span className="stigmem-fields__type">Required content</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Learn</dt>
<dt><span className="stigmem-fields__type">conceptual</span></dt>
<dd>If the feature affects the conceptual model, an explanation appears under Key Concepts.</dd>
</div>

<div>
<dt>Build</dt>
<dt><span className="stigmem-fields__type">integration</span></dt>
<dd>API reference · SDK examples · integration patterns.</dd>
</div>

<div>
<dt>Operate</dt>
<dt><span className="stigmem-fields__type">production</span></dt>
<dd>Configuration reference · hardening guidance · runbook updates if observability is affected.</dd>
</div>

<div>
<dt>Secure</dt>
<dt><span className="stigmem-fields__type">trust</span></dt>
<dd>Scenarios under <code>docs/security/scenarios.md</code> covering the feature's risks · threat-model delta linked.</dd>
</div>

</div>

If the feature doesn't need a presence in a given tab (e.g., a backend
driver doesn't need Learn coverage), that's documented in the ADR
(Gate 2).

### Order matters

<div className="stigmem-keypoint">

**Sequential, not parallel.**

Gate 1 (threat model) before Gate 2 (ADR), because the design decision
should be informed by the security analysis. Gate 3 (conformance)
before Gate 4 (soak), because the operator should soak against a
behaviorally-defined contract, not a moving target. Gate 5 (docs) at
the end, because docs against a still-changing implementation rot
before they ship.

</div>

### Reduced-gate paths

Some experimental features may not warrant the full process — for
example, a build-tooling improvement that's experimental only because
it wasn't tested on enough operating systems.

<ol className="stigmem-steps">
<li>The author proposes a reduced-gate path in their ADR (Gate 2).</li>
<li>Two contributors sign off explicitly on which gates are skipped and why.</li>
<li>The reduced-gate path is documented in the ADR for institutional memory.</li>
</ol>

**The default is all five gates. Skipping is exception, not rule.**

## Alternatives considered

<div className="stigmem-fields">

<div>
<dt>Alternative</dt>
<dt><span className="stigmem-fields__type">Disposition</span></dt>
<dd>Why</dd>
</div>

<div>
<dt>No gates; let maintainer judgment decide</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Maintainer judgment is exactly what produced the retracted v1.0. The gates exist precisely to provide structure that survives the temptation to "just include this one feature."</dd>
</div>

<div>
<dt>Fewer gates (drop the 30-day soak; rely on internal testing)</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>The 30-day external operator soak is the single highest-value gate. Internal testing finds bugs the authors anticipated; external soak finds bugs the authors didn't think to test for.</dd>
</div>

<div>
<dt>More gates (add an external auditor review)</dt>
<dt><span className="stigmem-fields__type">considered for v1.0.0 GA, not per feature</span></dt>
<dd>External auditing is a fit for major version releases; individual features get the threat-model delta plus conformance suite plus soak.</dd>
</div>

<div>
<dt>Time-based gates ("a feature can re-enter after 6 months")</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Time alone proves nothing; a feature that sat untouched for 6 months is no closer to ready. The gates are about evidence of readiness, not duration of waiting.</dd>
</div>

<div>
<dt>Combine all gates into a single "feature readiness review"</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Five distinct gates each produce a distinct artifact. A combined review tends to compress into a single conversation that ends in "looks good" — which is what we're trying to avoid.</dd>
</div>

</div>

## Consequences

### What gets easier

<div className="stigmem-grid">

<div><h4>Adopter clarity</h4><p>"Is feature X supported?" has a clean answer: either it has passed all five gates (supported) or it hasn't (experimental). No middle ground.</p></div>
<div><h4>Maintainer focus</h4><p>Re-introduction work is a known process with known artifacts. Authors of experimental features have a roadmap.</p></div>
<div><h4>Trust accumulation</h4><p>Each feature that passes the gates demonstrates the project's discipline. Over time, the gate process itself becomes a credibility signal.</p></div>
<div><h4>Resistance to scope-creep</h4><p>When someone proposes "let's just turn on §23 tombstones," the answer is "great, here are the five artifacts you need to produce." Most proposals don't survive Gate 1.</p></div>

</div>

### What gets harder

<div className="stigmem-grid">

<div><h4>Per-feature re-introduction is real work</h4><p>Authors who shipped quickly into experimental will find the path to v1.x slower. This is a feature.</p></div>
<div><h4>Some features may never pass</h4><p>If a feature can't produce a credible threat-model delta, or no operator wants to soak it, that's information. Some experimental features will live in <code>experimental/</code> indefinitely.</p></div>
<div><h4>PR review overhead</h4><p>Every feature-promotion PR triggers gate-checking. Mitigation: gate status tracked in <code>experimental/&lt;feature&gt;/STATUS.md</code>; PR templates ask "does this PR change gate status?"</p></div>

</div>

### New risks

<div className="stigmem-fields">

<div>
<dt>Risk</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Mitigation</dd>
</div>

<div>
<dt><code>R-GATE-1</code> · gate gaming</dt>
<dt><span className="stigmem-fields__type">tracked</span></dt>
<dd>An author who wants to ship faster might produce a perfunctory threat-model delta or a soak with one cooperative operator. Mitigation: contributors' sign-off on each gate; community can call out perfunctory artifacts publicly.</dd>
</div>

<div>
<dt><code>R-GATE-2</code> · features stuck behind one gate</dt>
<dt><span className="stigmem-fields__type">tracked</span></dt>
<dd>A feature with clear threat model and ADR but no available soak operator can't progress. Mitigation: contributors can act as soak operators in extreme cases (with soak duration extended to 60 days to compensate for existing familiarity).</dd>
</div>

<div>
<dt><code>R-GATE-3</code> · gate inflation</dt>
<dt><span className="stigmem-fields__type">mitigated</span></dt>
<dd>Future ADRs might add more gates, making the process unsustainable. This ADR fixes the gates at five; adding requires an ADR-008 amendment with contributors' sign-off.</dd>
</div>

</div>

## Implementation plan

This ADR takes effect immediately on acceptance. No code changes are
required for v0.9.x — the gates apply to features attempting
re-introduction, of which there are none until at least v1.0.0 GA.

After v1.0.0 GA, the first feature to attempt re-introduction will
road-test the process. Lessons learned from that road-test feed an
ADR-008 amendment if needed.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor
approval rule (founder solo-approval; second contributor sign-off
welcome but not required).*
