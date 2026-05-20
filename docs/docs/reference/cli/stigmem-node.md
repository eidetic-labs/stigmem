---
title: "stigmem-node"
sidebar_label: "stigmem-node"
sidebar_position: 2
description: "CLI reference for the stigmem-node command — starts the Stigmem HTTP server."
audience: Operator
---

# stigmem-node CLI

<p className="stigmem-meta"><span>1 min read</span><span>Operator</span><span>Server CLI</span></p>

<div className="stigmem-lead">

**What this page covers**

The `stigmem-node` command starts the Stigmem reference node HTTP
server.

</div>

Auto-generated from `stigmem-node --help`. Regenerate with `make gen-cli-docs`.

## Usage

```
stigmem-node [--host HOST] [--port PORT]
```

## Environment Variables

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_HOST</code></dt>
<dt><span className="stigmem-fields__type">0.0.0.0</span></dt>
<dd>Bind address.</dd>
</div>

<div>
<dt><code>STIGMEM_PORT</code></dt>
<dt><span className="stigmem-fields__type">8765</span></dt>
<dd>Listen port.</dd>
</div>

<div>
<dt><code>STIGMEM_DB_PATH</code></dt>
<dt><span className="stigmem-fields__type">stigmem.db</span></dt>
<dd>SQLite database path.</dd>
</div>

<div>
<dt><code>STIGMEM_AUTH_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Require API key authentication.</dd>
</div>

<div>
<dt><code>STIGMEM_SOURCE_ATTESTATION_MODE</code></dt>
<dt><span className="stigmem-fields__type">off</span></dt>
<dd>Legacy source-attestation mode field; runtime enforcement is plugin-gated.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_INTERVAL</code></dt>
<dt><span className="stigmem-fields__type">30</span></dt>
<dd>Seconds between federation pull cycles.</dd>
</div>

<div>
<dt><code>STIGMEM_EMBED_DIMENSIONS</code></dt>
<dt><span className="stigmem-fields__type">768</span></dt>
<dd>Embedding dimensions (Matryoshka truncation).</dd>
</div>

<div>
<dt><code>STIGMEM_CARD_MAX_AGE_S</code></dt>
<dt><span className="stigmem-fields__type">86400</span></dt>
<dd>Memory card staleness threshold (seconds).</dd>
</div>

</div>
