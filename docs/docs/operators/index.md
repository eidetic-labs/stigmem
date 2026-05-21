---
title: Operators
sidebar_label: Overview
description: Self-hosting handbook for Stigmem node operators — backend selection, deploy recipes, federation, backup, monitoring, and cost planning.
audience: Operator
sidebar_position: 4
---

# Operators

<p className="stigmem-meta"><span>3 min read</span><span>Self-hosting operators · SREs</span><span>Handbook overview</span></p>

<div className="stigmem-lead">

**What this handbook covers**

Everything you need to run a Stigmem node in production: picking a
storage backend, deploying, federating with peers, backing up,
monitoring, and debugging recall latency.

</div>

**Audience:** self-hosting operators, infrastructure engineers, SREs.

---

## In this section

<div className="stigmem-fields">

<div>
<dt>Page</dt>
<dt><span className="stigmem-fields__type">Topic</span></dt>
<dd>What you'll find</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/storage-backends">Choose your backend (experimental)</a></dt>
<dt><span className="stigmem-fields__type">storage</span></dt>
<dd>Decision tree: SQLite vs libSQL vs Postgres.</dd>
</div>

<div>
<dt><a href="./runbooks/deploy-runbooks">Deploy runbooks</a></dt>
<dt><span className="stigmem-fields__type">deploy</span></dt>
<dd>Step-by-step runbooks for Fly, Compose, Helm, systemd, and PaaS.</dd>
</div>

<div>
<dt><a href="./runbooks/federation-setup">Federation peer setup</a></dt>
<dt><span className="stigmem-fields__type">federation</span></dt>
<dd>Key generation, pinning, and source-trust tuning.</dd>
</div>

<div>
<dt><a href="./validation-soak">Operator validation soak</a></dt>
<dt><span className="stigmem-fields__type">validation</span></dt>
<dd>30-day external validation checklist, weekly digest shape, and finding triage.</dd>
</div>

<div>
<dt><a href="./runbooks/backup-restore">Backup &amp; restore</a></dt>
<dt><span className="stigmem-fields__type">DR</span></dt>
<dd>Signed snapshot workflow and cloud PITR.</dd>
</div>

<div>
<dt><a href="./observability/monitoring">Monitoring &amp; debugging</a></dt>
<dt><span className="stigmem-fields__type">observability</span></dt>
<dd>Health checks, metrics, and recall-latency diagnosis.</dd>
</div>

<div>
<dt><a href="./runbooks/r-peer-compromise">Peer compromise response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>Containment and recovery when a federation peer is suspicious or compromised.</dd>
</div>

<div>
<dt><a href="./runbooks/r-worm-detected">Worm detection response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>Response path for automated cross-peer or agent-to-agent propagation.</dd>
</div>

<div>
<dt><a href="./runbooks/r-manifest-failure">Manifest failure response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>What to do when peer manifest or key-rotation verification fails.</dd>
</div>

<div>
<dt><a href="./runbooks/r-rekor-unavailable">Rekor unavailable response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>How to handle delayed fact-chain transparency-log checkpoints.</dd>
</div>

<div>
<dt><a href="./runbooks/r-hlc-drift">HLC drift response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>How to handle peers sending timestamps outside allowed skew.</dd>
</div>

<div>
<dt><a href="./runbooks/r-key-expiry">Key expiry response</a></dt>
<dt><span className="stigmem-fields__type">incident</span></dt>
<dd>Recovery from expired API, federation, issuer, or encryption keys.</dd>
</div>

<div>
<dt><a href="../security/immutability-and-attestation">Immutability &amp; attestation</a></dt>
<dt><span className="stigmem-fields__type">hardening</span></dt>
<dd>R-23 hardening stack, WORM evidence, and TEE deployment options.</dd>
</div>

</div>

---

## Operator helper scripts

The public repo keeps reusable operator helpers in [`scripts/`](https://github.com/eidetic-labs/stigmem/tree/main/scripts):

<div className="stigmem-grid">

<div><h4><code>import_markdown_tree.py</code></h4><p>Imports a markdown index and linked markdown files into a Stigmem node as facts. Useful for bootstrapping runbooks, team wikis, or personal knowledge bases.</p></div>
<div><h4><code>stigmem-snapshot.sh</code></h4><p>Creates a human-readable markdown export of selected facts and contradiction metrics. Complements (but does not replace) the signed <code>stigmem snapshot</code> backup format.</p></div>

</div>

---

## Quick orientation

A production Stigmem node has four operational concerns:

```
┌─────────────────────────────────────────────────────┐
│              Stigmem reference node                 │
│                                                     │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Storage   │  │  Federation  │  │  Recall /  │  │
│  │  backend   │  │  peer mesh   │  │  embedding │  │
│  └────────────┘  └──────────────┘  └────────────┘  │
│            ↕               ↕               ↕        │
│  ┌──────────────────────────────────────────────┐   │
│  │            Operational layer                 │   │
│  │  backup/restore · key rotation · monitoring  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Start here** if you haven't deployed yet:

<ol className="stigmem-steps">
<li><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/storage-backends">Choose your backend</a> — picks your persistence strategy.</li>
<li><a href="./runbooks/deploy-runbooks">Deploy runbooks</a> — gets the node running in your environment.</li>
<li><a href="./runbooks/federation-setup">Federation peer setup</a> — connects your node to peers.</li>
</ol>

**Day-two operations:**

<div className="stigmem-grid">

<div><h4>Backup &amp; restore</h4><p><a href="./runbooks/backup-restore">protect against data loss</a>.</p></div>
<div><h4>Monitoring &amp; debugging</h4><p><a href="./observability/monitoring">observe and diagnose</a>.</p></div>
<div><h4>Incident runbooks</h4><p><a href="./runbooks/r-peer-compromise">respond to critical alerts</a>: federation, manifest, HLC, worm, key-expiry.</p></div>

</div>

<div className="stigmem-keypoint">

**Planning a deployment?** The [cost calculator](https://github.com/eidetic-labs/stigmem/tree/main/experimental/billing) helps you estimate storage growth, egress, embedding spend, and operator time before you commit to infrastructure.

**Joining external validation?** Start with the [Operator validation soak](./validation-soak) checklist so public findings, weekly digests, and future hardened-core exit evidence are traceable from the first day.

</div>
