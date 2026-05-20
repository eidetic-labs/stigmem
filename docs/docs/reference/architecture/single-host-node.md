---
title: "Single-Host Node"
sidebar_label: "Single-Host Node"
sidebar_position: 1
description: "Architecture diagram of a single Stigmem node — FastAPI server, SQLite storage, HLC, auth, and background tasks."
audience: Spec
---

# Single-Host Node

<p className="stigmem-meta"><span>2 min read</span><span>Engineer</span><span>Reference architecture</span></p>

<div className="stigmem-lead">

**What this page covers**

A single Stigmem node is a self-contained FastAPI process backed by
SQLite (or libSQL/Postgres). This diagram shows the internal
component layout and request flow.

</div>

**Audience:** engineers deploying or contributing to the Stigmem reference node.

```mermaid
graph TB
    Client["Client\n(Agent, Adapter, SDK)"]

    subgraph Node["Stigmem Node (single host)"]
        direction TB
        API["FastAPI Router\n/v1/facts, /v1/gardens,\n/v1/recall, /v1/conflicts"]
        Auth["Auth Middleware\nAPI key -> identity\n(Spec-02)"]
        Attest["Source Attestation\nenforce | warn | off\n(Spec-X6)"]
        HLC["HLC Clock\nthreading.Lock-protected\n(Spec-12)"]
        Ingest["Fact Ingest\nidempotent, CID-checked"]
        Conflict["Conflict Detector\nsame (entity, relation, scope)\n-> contradiction record\n(Spec-15)"]
        Decay["Decay Sweeper\nbackground task\n(Spec-X9)"]
        FedPull["Federation Pull\nbackground task\nHLC-cursor replication\n(Spec-05)"]

        subgraph Storage["Storage Layer"]
            DB[("facts\nconflicts\npeers\ngardens\napi_keys")]
            Vec[("vec_facts\nembedding index\n(Spec-X11)")]
            Edges[("entity_edges\ngraph index\n(Spec-X11)")]
        end
    end

    Client -- "HTTP/JSON\nBearer token" --> API
    API --> Auth
    Auth --> Attest
    Attest --> HLC
    HLC --> Ingest
    Ingest --> DB
    Ingest --> Conflict
    Conflict --> DB
    Ingest --> Vec
    Ingest --> Edges
    Decay --> DB
    Decay --> Vec
    FedPull --> Ingest
```

## Key components

<div className="stigmem-fields">

<div>
<dt>Component</dt>
<dt><span className="stigmem-fields__type">File</span></dt>
<dd>Responsibility</dd>
</div>

<div>
<dt>FastAPI Router</dt>
<dt><span className="stigmem-fields__type"><code>main.py</code>, <code>routes/</code></span></dt>
<dd>HTTP endpoint registration, lifespan management.</dd>
</div>

<div>
<dt>Auth Middleware</dt>
<dt><span className="stigmem-fields__type"><code>auth.py</code></span></dt>
<dd>Resolves <code>Authorization: Bearer</code> to an identity with scopes and permissions.</dd>
</div>

<div>
<dt>Source Attestation</dt>
<dt><span className="stigmem-fields__type"><code>auth.py</code></span></dt>
<dd>Validates <code>source</code> URI against caller's <code>entity_uri</code> (<code>Spec-X6</code>).</dd>
</div>

<div>
<dt>HLC Clock</dt>
<dt><span className="stigmem-fields__type"><code>hlc.py</code></span></dt>
<dd>Thread-safe hybrid logical clock; advances on local writes and federated receives.</dd>
</div>

<div>
<dt>Fact Ingest</dt>
<dt><span className="stigmem-fields__type"><code>routes/facts.py</code></span></dt>
<dd>Idempotent fact insertion, CID computation, scope enforcement.</dd>
</div>

<div>
<dt>Conflict Detector</dt>
<dt><span className="stigmem-fields__type"><code>routes/facts.py</code></span></dt>
<dd>Detects <code>(entity, relation, scope)</code> value divergence; creates contradiction records.</dd>
</div>

<div>
<dt>Decay Sweeper</dt>
<dt><span className="stigmem-fields__type"><code>decay.py</code></span></dt>
<dd>Background task that expires facts past <code>valid_until</code> or low confidence.</dd>
</div>

<div>
<dt>Federation Pull</dt>
<dt><span className="stigmem-fields__type"><code>federation_pull.py</code></span></dt>
<dd>Periodically fetches new facts from registered peers using HLC cursor.</dd>
</div>

<div>
<dt>Storage</dt>
<dt><span className="stigmem-fields__type"><code>db.py</code></span></dt>
<dd>SQLite/libSQL/Postgres with migration support; <code>vec_facts</code> and <code>entity_edges</code> for recall.</dd>
</div>

</div>
