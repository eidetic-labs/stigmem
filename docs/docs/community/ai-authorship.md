---
id: ai-authorship
title: AI Authorship Disclosure
sidebar_label: AI Authorship
description: How Stigmem discloses AI-assisted work and calibrates review expectations.
---

# AI Authorship Disclosure

<p className="stigmem-meta"><span>2 min read</span><span>Contributor · Reviewer · Operator</span><span>Calibration</span></p>

<div className="stigmem-lead">

**What this page covers**

Stigmem is built by two contributors with heavy AI-coding
assistance. We disclose this because a category whose product is
trust should not quietly hide where the work came from.

</div>

<div className="stigmem-keypoint">

**This is a calibration aid, not a defect notice.**

It helps readers decide where to apply extra verification before
relying on Stigmem in their own workload.

</div>

## Deeper human review

These paths receive line-by-line human review:

<div className="stigmem-grid">

<div><h4><code>spec/</code></h4><p>Protocol specification text.</p></div>
<div><h4><code>docs/adr/</code></h4><p>Architecture Decision Records.</p></div>
<div><h4>Top-level repo docs</h4><p><code>LIMITATIONS.md</code>, <code>SECURITY.md</code>, <code>MAINTAINERS.md</code>, and the root <code>README.md</code>.</p></div>
<div><h4>Threat-model entries</h4><p>In <code>spec/security/</code> and rendered security docs.</p></div>

</div>

## Lighter human review

These paths receive high-level direction and spot checks:

<div className="stigmem-grid">

<div><h4><code>node/src/</code></h4><p>Reference node implementation.</p></div>
<div><h4><code>adapters/</code></h4><p>Adapter implementations.</p></div>
<div><h4><code>sdks/</code></h4><p>SDK stubs.</p></div>
<div><h4>UI scaffolding</h4><p>And experimental surfaces.</p></div>
<div><h4>Test suites</h4></div>
<div><h4>Non-spec docs</h4><p>Outside spec, ADRs, and security posture.</p></div>

</div>

## Contributor expectation

<div className="stigmem-keypoint">

**When a PR includes AI-generated code or prose, say so in the PR description.**

The project does not reject AI-assisted contributions; it calibrates
review effort. Reviewers should verify behavior against the spec,
run the relevant conformance or test suite, and audit higher-risk
paths before merging.

</div>

The canonical source copy for this disclosure is also maintained in [`README.md`](https://github.com/eidetic-labs/stigmem/blob/main/README.md#ai-authorship-disclosure) and [`CONTRIBUTING.md`](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md#ai-authorship-disclosure).
