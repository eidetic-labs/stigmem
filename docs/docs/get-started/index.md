---
title: Get Started
sidebar_position: 1
---

# Get Started

<p className="stigmem-meta"><span>4 min read</span><span>For first-time operators</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll do**

Install a local Stigmem node, assert your first fact, query it back,
and connect an SDK. Roughly five minutes end-to-end. Everything below
runs locally — no federation peering required.

</div>

<div className="stigmem-keypoint">

**Single-org, single-node is the supported pattern.**

The alpha is safe for local development, conformance testing, and
single-organization deployments. Cross-organizational federation is
**not yet safe** — read
[LIMITATIONS](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md)
before integrating against any cross-org boundary.

</div>

## The path

<ol className="stigmem-steps">
<li><a href="./installation"><strong>Install</strong></a> — set up a local Stigmem node with the package manager you already use (<code>pipx</code> · <code>pip</code> · Docker).</li>
<li><a href="./quickstart-tutorial"><strong>Quickstart tutorial</strong></a> — assert your first fact, query it back, watch a conflict open, resolve it explicitly.</li>
<li><a href="./sdk-quickstart"><strong>SDK quickstart</strong></a> — connect from Python, TypeScript, or Go using the generated client.</li>
<li><a href="./upgrade-v1"><strong>Pre-v0.9.0a1 notes</strong></a> — only relevant if you have older local checkouts or pinned dependencies from before the alpha reset.</li>
</ol>

## What you'll need

<div className="stigmem-fields">

<div>
<dt>Requirement</dt>
<dt><span className="stigmem-fields__type">Version</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Python</dt>
<dt><span className="stigmem-fields__type">≥ 3.11</span></dt>
<dd>For the reference node and the Python SDK.</dd>
</div>

<div>
<dt>Operating system</dt>
<dt><span className="stigmem-fields__type">macOS · Linux · WSL2</span></dt>
<dd>Container path is identical across all three.</dd>
</div>

<div>
<dt>Disk</dt>
<dt><span className="stigmem-fields__type">~200 MB</span></dt>
<dd>For the node binary and the SQLite store backing local development.</dd>
</div>

<div>
<dt>Network</dt>
<dt><span className="stigmem-fields__type">localhost</span></dt>
<dd>No outbound network access required for the local-only quickstart path.</dd>
</div>

</div>

## What's next

<div className="stigmem-next">

<a href="./installation">
<strong>Step 1</strong>
<span>Install the reference node</span>
<small>The CLI, the SDK stub, and the local SQLite store.</small>
</a>

<a href="../concepts/overview">
<strong>Read</strong>
<span>Learn</span>
<small>The protocol tour — fact tuple, scopes, HLC, conflicts.</small>
</a>

<a href="../security/">
<strong>Read</strong>
<span>Security</span>
<small>The honest scope evaluators want to see before adopting.</small>
</a>

</div>
