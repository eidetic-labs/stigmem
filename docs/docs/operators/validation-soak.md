---
title: Operator Validation Soak
sidebar_label: Operator Validation Soak
description: How external operators run the Phase B validation soak and report findings.
audience: Operator
---

# Operator Validation Soak

<p className="stigmem-meta"><span>3 min read</span><span>External operator · Maintainer</span><span>Phase B gate</span></p>

<div className="stigmem-lead">

**What this page covers**

The Phase B operator validation soak is the public evidence gate
before Stigmem can declare the `v1.0.0rcN` line. At least one
external operator must run the hardened core for 30 days, report
findings publicly when safe, and confirm that P0 findings are fixed
or explicitly carried forward.

</div>

## What the operator runs

<div className="stigmem-grid">

<div><h4>Reference node</h4><p>Deployment using the current <code>main</code> branch or the release tag named by maintainers.</p></div>
<div><h4>Same-org federation</h4><p>Local or same-organization federation using documented peer setup.</p></div>
<div><h4>Hardened surfaces</h4><p>mTLS, key rotation, audit log, observability, and runbook surfaces exercised where applicable.</p></div>
<div><h4>No experimental plugins</h4><p>Unless the issue explicitly says the operator is validating that plugin as a separate ADR-008 gate.</p></div>

</div>

<div className="stigmem-keypoint">

**Cross-organization production federation remains pre-stable until the soak finishes and the project declares the release-candidate line.**

</div>

## Before the soak starts

<div className="stigmem-fields">

<div>
<dt>Item</dt>
<dt><span className="stigmem-fields__type">Evidence</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Deployment shape</dt>
<dt><span className="stigmem-fields__type">public issue</span></dt>
<dd>Operator-candidate issue with non-sensitive context.</dd>
</div>

<div>
<dt>Version under test</dt>
<dt><span className="stigmem-fields__type">SHA / tag</span></dt>
<dd>Commit SHA or release tag.</dd>
</div>

<div>
<dt>Topology</dt>
<dt><span className="stigmem-fields__type">shape</span></dt>
<dd>Single node, same-org federation, or limited cross-org test.</dd>
</div>

<div>
<dt>Reporting path</dt>
<dt><span className="stigmem-fields__type">public + advisory</span></dt>
<dd>Public issues for non-sensitive findings; private advisory path for vulnerabilities.</dd>
</div>

<div>
<dt>Weekly cadence</dt>
<dt><span className="stigmem-fields__type">LOG.md</span></dt>
<dd>Digest entry or GitHub Discussion link.</dd>
</div>

<div>
<dt>Stop conditions</dt>
<dt><span className="stigmem-fields__type">P0 / risk</span></dt>
<dd>P0 finding, secret exposure, unsafe deployment pattern, or operator request.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Do not put secrets, private topology diagrams, private customer data, exploit details, or unpublished vulnerability details in public issues.**

</div>

## Weekly digest

Each week, maintainers should add a short digest to `LOG.md` or link a public Discussion:

```md
## YYYY-MM-DD — Operator Soak Digest, Week N

- Operator context: <public non-sensitive summary>
- Version under test: <commit or release tag>
- Deployment shape: <single node / same-org federation / limited federation>
- Findings opened: #NN, #NN
- Findings closed: #NN
- P0 status: none / #NN
- ADR-004 observability notes: <signals that helped or were missing>
- Next week: <planned validation focus>
```

## Finding triage

Open public findings with the **Operator finding** issue template whenever the report can be shared safely. Maintainers apply:

<div className="stigmem-grid">

<div><h4><code>type/operator-finding</code></h4><p>For all soak findings.</p></div>
<div><h4><code>operator-soak-finding</code></h4><p>For findings produced during the 30-day soak.</p></div>
<div><h4><code>severity/P0</code></h4><p>When the finding blocks safe continuation.</p></div>

</div>

P0 findings stop the soak until the operator and maintainers agree it is safe to continue. Fix PRs should reference the finding issue and include the validation that proves the fix.

## ADR-004 feedback

Operator feedback should explicitly name which observability signals helped and which were missing. When the feedback changes incident-response expectations, open an ADR-004 amendment issue or PR and link the operator finding.

## Exit evidence

Phase B exit requires:

<ol className="stigmem-steps">
<li>One external operator completed 30 days of validation.</li>
<li>All P0 soak findings are closed or explicitly carried forward with a release blocker label.</li>
<li>Weekly digests are linked from <code>LOG.md</code>.</li>
<li>Relevant ADR-004 amendments are opened or merged.</li>
<li>Roadmap and checklist state are updated in the same PR that records exit evidence.</li>
</ol>
