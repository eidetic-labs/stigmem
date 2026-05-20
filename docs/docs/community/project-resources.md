---
title: Project Resources
sidebar_label: Project Resources
description: Community engagement paths for the Stigmem project — how to contribute, review, or run a validation node.
audience: Evaluator
---

# Project Resources

<p className="stigmem-meta"><span>3 min read</span><span>Contributor · Operator candidate</span><span>v0.9.0aN alpha</span></p>

<div className="stigmem-lead">

**What this page covers**

Stigmem is in the `v0.9.0aN` alpha line: useful for review, adapter
work, single-organization experiments, and external validation, but
not yet recommended for production cross-organization federation.

</div>

<div className="stigmem-keypoint">

**The most valuable contributions right now are small, evidence-producing improvements.**

That make the protocol more testable, auditable, and easier to
adopt.

</div>

**Audience:** potential contributors, engineers, security researchers, applied researchers, and candidate operators.

## Contributor entry points

<div className="stigmem-fields">

<div>
<dt>Path</dt>
<dt><span className="stigmem-fields__type">Start here</span></dt>
<dd>Good first work</dd>
</div>

<div>
<dt>Reference node</dt>
<dt><span className="stigmem-fields__type"><a href="../reference/architecture/">Architecture</a></span></dt>
<dd>Focused tests, docs corrections, small route/CLI fixes.</dd>
</div>

<div>
<dt>Federation</dt>
<dt><span className="stigmem-fields__type"><a href="../reference/architecture/federated-network">Federated network</a></span></dt>
<dd>Scope/audit examples, demo polish, conformance gaps.</dd>
</div>

<div>
<dt>Security review</dt>
<dt><span className="stigmem-fields__type"><a href="../security/">Security architecture</a></span></dt>
<dd>Evidence links, runbook clarity, safe test cases.</dd>
</div>

<div>
<dt>Plugin ecosystem</dt>
<dt><span className="stigmem-fields__type"><a href="../guides/plugins/author-guide">Plugin author guide</a></span></dt>
<dd>Plugin docs examples, lifecycle tests, fixture improvements.</dd>
</div>

<div>
<dt>Docs and onboarding</dt>
<dt><span className="stigmem-fields__type"><a href="https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md">Contributing</a></span></dt>
<dd>Glossary entries, quickstart troubleshooting, issue-template polish.</dd>
</div>

</div>

Starter work is labeled [`good first issue`](https://github.com/eidetic-labs/stigmem/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22good%20first%20issue%22). Pick one issue, keep the PR narrow, and include the focused validation you ran.

## Demos to run first

From a repository checkout:

```bash
make demo
make demo-attack
```

<div className="stigmem-fields">

<div>
<dt>Command</dt>
<dt><span className="stigmem-fields__type">Demonstrates</span></dt>
<dd>What you'll see</dd>
</div>

<div>
<dt><code>make demo</code></dt>
<dt><span className="stigmem-fields__type">happy path</span></dt>
<dd>Starts two local nodes, registers them as peers, asserts a fact on node A, verifies replication on node B, prints federation audit entries, and tears the cluster down.</dd>
</div>

<div>
<dt><code>make demo-attack</code></dt>
<dt><span className="stigmem-fields__type">adversarial</span></dt>
<dd>Demonstrates malicious-peer rejection: unauthorized scope writes and source-forged facts are rejected, audited, and not stored.</dd>
</div>

</div>

## Operator validation

Teams interested in running a node during external validation should open an [operator candidate issue](https://github.com/eidetic-labs/stigmem/issues/new?template=operator_candidate.yml).

<div className="stigmem-keypoint">

**Keep infrastructure details, secrets, and private organization data out of the public issue.**

The public thread should describe the validation shape and the
questions you want to answer.

</div>

## Security research

Security researchers should read [SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) before filing anything.

<div className="stigmem-grid">

<div><h4>Public OK</h4><p>Security documentation, safe-harbor questions, or already-public advisory follow-up.</p></div>
<div><h4>Private only</h4><p>Active vulnerabilities, exploit details, secrets, and private operator findings.</p></div>

</div>

## Community norms

Stigmem is an open protocol project. All contributors and collaborators are expected to follow the [Code of Conduct](https://github.com/eidetic-labs/stigmem/blob/main/CODE_OF_CONDUCT.md).

**Key principles:**

<div className="stigmem-grid">

<div><h4>Spec changes go through RFC</h4><p>Wire format, namespace, and federation semantics changes require review before merging.</p></div>
<div><h4>Evidence beats claims</h4><p>Prototypes, tests, reproducible demos, and conformance vectors are more persuasive than prose alone.</p></div>
<div><h4>Protocol-layer focus</h4><p>Stigmem provides a shared substrate; adapters and agent tools build on top of it.</p></div>

</div>
