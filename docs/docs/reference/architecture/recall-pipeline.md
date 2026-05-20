---
title: "Recall Pipeline"
sidebar_label: "Recall Pipeline"
sidebar_position: 3
description: "Architecture diagram of the three-stage hybrid recall pipeline — lexical, dense vector, and graph expansion with MMR packing."
audience: Spec
---

# Recall Pipeline

<p className="stigmem-meta"><span>2 min read</span><span>Recall engineer</span><span>Spec-X11</span></p>

<div className="stigmem-lead">

**What this page covers**

The recall pipeline retrieves semantically relevant facts for agent
queries. It runs three independent retrieval stages, fuses their
results with salience signals, and packs the output within a
caller-specified token budget using Maximal Marginal Relevance (MMR).

</div>

**Audience:** engineers building recall-capable agents or contributing to the recall subsystem (`Spec-X11-Recall-Graph`).

## Pipeline overview

```mermaid
flowchart TB
    Q["POST /v1/recall\n{query, scope, token_budget}"]

    subgraph Retrieval["Three-stage retrieval"]
        direction LR
        L["Stage 1 — Lexical\nFTS5 / BM25\nExact relation-namespace\nmatching"]
        V["Stage 2 — Dense\nsqlite-vec ANN\nSemantic similarity\n(cosine)"]
        G["Stage 3 — Graph\nBFS on entity_edges\ndepth ≤ 2\nhub-bias: ÷ log(1+degree)"]
    end

    subgraph Fusion["Score fusion"]
        F["Weighted combination\nBM25 × 0.30\ncosine × 0.50\ngraph × 0.20\n× salience signals"]
    end

    subgraph Packing["Token-budget packing"]
        MMR["MMR selection\nλ = 0.7\ndiversity vs relevance\ntoken cost: 40 + ⌈len/4⌉"]
    end

    Q --> L & V
    L --> Seeds["Seed entities\nunion(L ∪ V)"]
    V --> Seeds
    Seeds --> G
    L & V & G --> F
    F --> MMR
    MMR --> R["Scored result set\n≤ token_budget"]
```

## Salience signals

Applied during the fusion step to adjust raw retrieval scores:

<div className="stigmem-fields">

<div>
<dt>Signal</dt>
<dt><span className="stigmem-fields__type">Range</span></dt>
<dd>Formula</dd>
</div>

<div>
<dt>Recency</dt>
<dt><span className="stigmem-fields__type">(0, 1]</span></dt>
<dd><code>exp(-0.01 × age_days)</code></dd>
</div>

<div>
<dt>Confidence</dt>
<dt><span className="stigmem-fields__type">[0, 1]</span></dt>
<dd><code>fact.confidence</code></dd>
</div>

<div>
<dt>Access frequency</dt>
<dt><span className="stigmem-fields__type">[0, 1]</span></dt>
<dd><code>log(1 + access_count) / log(1 + max_access_count)</code></dd>
</div>

<div>
<dt>Contradiction penalty</dt>
<dt><span className="stigmem-fields__type">&#123;0.7, 1.0&#125;</span></dt>
<dd>1.0 if no unresolved contradiction; 0.7 otherwise.</dd>
</div>

<div>
<dt>Garden tier</dt>
<dt><span className="stigmem-fields__type">[0, 1]</span></dt>
<dd>Configurable per garden; quarantine default 0.2.</dd>
</div>

<div>
<dt>Source-trust multiplier</dt>
<dt><span className="stigmem-fields__type">[0.5, 1]</span></dt>
<dd><code>0.5 + 0.5 × t</code> (maps [0,1] → [0.5,1.0]).</dd>
</div>

</div>

## Security: ANN scope filter

<div className="stigmem-keypoint">

**Stage 2 ANN results MUST be joined back against `facts` and filtered by the caller's scope and garden ACL before fusion.**

`vec_facts` holds embeddings for all scopes with no `scope` column.
Without this filter, facts from unauthorized gardens could leak into
the response.

</div>

## Example

```bash
curl -X POST http://localhost:8765/v1/recall \
  -H "Authorization: Bearer $KEY" \
  -d '{
    "query": "What is Alice'\''s current role?",
    "scope": "company",
    "token_budget": 2000,
    "weights": {"lexical": 0.3, "vector": 0.5, "graph": 0.2}
  }'
```
