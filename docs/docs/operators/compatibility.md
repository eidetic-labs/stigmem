---
title: Compatibility
sidebar_label: Compatibility
audience: Operator
description: Cross-package compatibility matrix per ADR-014.
---

# Compatibility

<p className="stigmem-meta"><span>4 min read</span><span>Node operator</span><span>v0.9.0a1</span></p>

<div className="stigmem-lead">

**What this page covers**

The cross-package compatibility matrix per [ADR-014](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md).
The source-of-truth YAML is at
[`docs/compatibility-matrix.yaml`](https://github.com/eidetic-labs/stigmem/blob/main/docs/compatibility-matrix.yaml).
This page renders the YAML as human-readable tables.

</div>

> **Initial population at v0.9.0a1 baseline.** The full Docusaurus plugin that auto-renders the YAML at build time is acknowledged as a follow-up; this page is the hand-maintained equivalent for v0.9.0a1 → first publish. Updates ship with every release.

## Package versions

<div className="stigmem-fields">

<div>
<dt>Package</dt>
<dt><span className="stigmem-fields__type">Latest</span></dt>
<dd>Distribution</dd>
</div>

<div>
<dt><code>stigmem-node</code></dt>
<dt><span className="stigmem-fields__type">0.9.0a1</span></dt>
<dd>PyPI</dd>
</div>

<div>
<dt><code>stigmem-py</code></dt>
<dt><span className="stigmem-fields__type">0.9.0a1</span></dt>
<dd>PyPI</dd>
</div>

<div>
<dt><code>stigmem</code> (meta-package)</dt>
<dt><span className="stigmem-fields__type">0.9.0a1</span></dt>
<dd>PyPI</dd>
</div>

<div>
<dt><code>stigmem-openclaw</code> (adapter)</dt>
<dt><span className="stigmem-fields__type">0.9.0a1</span></dt>
<dd>PyPI</dd>
</div>

<div>
<dt><code>@eidetic-labs/stigmem-ts</code> (SDK)</dt>
<dt><span className="stigmem-fields__type">0.9.0-alpha.2</span></dt>
<dd>npm</dd>
</div>

<div>
<dt><code>stigmem-go</code> (SDK)</dt>
<dt><span className="stigmem-fields__type">deferred</span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/sdk-go"><code>experimental/sdk-go/</code></a></dd>
</div>

<div>
<dt><code>stigmem-mcp</code> (adapter)</dt>
<dt><span className="stigmem-fields__type">deferred at 0.4.0</span></dt>
<dd><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/mcp-adapter"><code>experimental/mcp-adapter/</code></a></dd>
</div>

</div>

## Connector compatibility

<div className="stigmem-fields">

<div>
<dt>Connector</dt>
<dt><span className="stigmem-fields__type">Stigmem-side</span></dt>
<dd>Host-side</dd>
</div>

<div>
<dt>OpenClaw</dt>
<dt><span className="stigmem-fields__type">openclaw≥0.9.0a1, py≥0.9.0a1,&lt;1.0.0</span></dt>
<dd>OpenClaw runtime ≥1.2. Experimental alpha connector only; public copy/framing corrections queued for v0.9.0a2.</dd>
</div>

</div>

## Feature compatibility (v0.9.0a1)

<div className="stigmem-fields">

<div>
<dt>Feature</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Spec / Required versions</dd>
</div>

<div>
<dt>Immutable typed facts</dt>
<dt><span className="stigmem-fields__type">Stable</span></dt>
<dd><code>Spec-01-Fact-Model</code>, <code>Spec-15-Fact-Semantics</code>; <code>node≥0.9.0a1</code>, <code>py≥0.9.0a1</code>.</dd>
</div>

<div>
<dt>Scope enforcement</dt>
<dt><span className="stigmem-fields__type">Stable</span></dt>
<dd><code>Spec-02-Scopes-and-ACL</code>; <code>node≥0.9.0a1</code>.</dd>
</div>

<div>
<dt>Two-node mTLS federation</dt>
<dt><span className="stigmem-fields__type">Stable</span></dt>
<dd><code>Spec-10-Hardening</code>, <code>Spec-05-Federation-Trust</code>; <code>node≥0.9.0a1</code>.</dd>
</div>

<div>
<dt>CIDs</dt>
<dt><span className="stigmem-fields__type">Stable in core</span></dt>
<dd>Per <a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md">ADR-017</a>; <code>Spec-21-Content-Addressed-IDs</code>; <code>node≥0.9.0a1</code>.</dd>
</div>

<div>
<dt><code>Stigmem-Version</code> header</dt>
<dt><span className="stigmem-fields__type">Documented; future hardened-core work</span></dt>
<dd><code>Spec-03-HTTP-API</code>; implementation planned for a future hardened-core line.</dd>
</div>

<div>
<dt>Argon2id API key hashing</dt>
<dt><span className="stigmem-fields__type">Current alpha line</span></dt>
<dd>Per <a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/007-argon2id.md">ADR-007</a>; new API keys use Argon2id in the current alpha implementation.</dd>
</div>

<div>
<dt>Lazy instruction discovery</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd><code>Spec-X1</code>; targeted v0.9.0a2.</dd>
</div>

<div>
<dt>RTBF tombstones</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd><code>Spec-X2</code>; source-only on <code>main</code>; no released plugin artifact yet.</dd>
</div>

<div>
<dt>Time-travel queries</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd><code>Spec-X3</code>; targeted v0.9.0a4.</dd>
</div>

<div>
<dt>Memory garden advanced ACL</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd><code>Spec-X5</code>; source-only.</dd>
</div>

<div>
<dt>Source attestation</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd><code>Spec-X6</code>; source-only.</dd>
</div>

<div>
<dt>Multi-tenant isolation</dt>
<dt><span className="stigmem-fields__type">Experimental</span></dt>
<dd>Cross-cutting; source-only.</dd>
</div>

</div>

## Protocol release composition

<div className="stigmem-keypoint">

**`v0.9.0a2`** — `stigmem-node@0.9.0a2`, `stigmem-py@0.9.0a2`,
`stigmem-openclaw@0.9.0a2`, `stigmem@0.9.0a2` (PyPI) +
`@eidetic-labs/stigmem-ts@0.9.0-alpha.2` (npm).

Default install matches v1.0 critical-path scope per ADR-002
(single-tenant; no tombstones, time-travel, memory cards, source
attestation, or lazy instruction discovery in default behavior).
OpenClaw/ClawHub is available for alpha evaluation only and remains
subject to [LIMITATIONS.md §9](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md#9-running-the-openclaw-bundled-adapter-as-is).
See [LIMITATIONS.md §11](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md)
for the architectural-gap acknowledgment.

</div>

## Cross-references

<div className="stigmem-grid">

<div><h4>Source-of-truth YAML</h4><p><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/compatibility-matrix.yaml"><code>docs/compatibility-matrix.yaml</code></a></p></div>
<div><h4>ADR-014</h4><p><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/014-compatibility-matrix.md">Compatibility matrix</a></p></div>
<div><h4>ADR-013</h4><p><a href="https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md">Deprecation policy</a></p></div>
<div><h4>Commitment</h4><p><a href="../security/compatibility-commitment.md">Compatibility commitment</a> — written commitment scaled to v0.9.0a1.</p></div>

</div>
