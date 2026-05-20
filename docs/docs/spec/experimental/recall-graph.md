---
spec_id: Spec-X11-Recall-Graph
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: pre-reset §20 advanced recall and graph material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-07-Recall-Pipeline >= 0.1.0-alpha.0
  - Spec-X5-Memory-Garden-Advanced-ACL >= 0.1.0-alpha.0
  - Spec-X6-Source-Attestation >= 0.1.0-alpha.0
title: §20. Recall & Graph
sidebar_label: §20 Recall & Graph
audience: Spec
description: "Stigmem spec section 20 — Graph adjacency index, vector embeddings, hybrid recall pipeline, memory cards, and causal links."
stability: experimental
since: 0.9.0a1
---

# §20. Recall & Graph {#section-20}

<p className="stigmem-meta"><span>10 min read</span><span>Spec contributor · Recall implementer</span><span>Experimental · v0.9.0bN</span></p>

<div className="stigmem-lead">

**What this section covers**

Graph adjacency index, embedding storage, recall API, memory cards,
and causal/derivation link lifecycle. The subscription primitive
that previously lived in §20.5 is now colocated under
[`Spec-X7-Subscriptions`](./subscriptions).

</div>

**Status:** Experimental / dormant source package. Archived source material was drafted as normative, but this spec is deferred from the supported v0.9.0aN surface and must pass ADR-008 gates before reintroduction.

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for recall graph semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Depends on:** §2 (fact shape), §5 (wire format), §17 (memory garden), §18 (source attestation), §19 (federation trust).

---

### §20.1 Graph Index {#section-20-1}

#### §20.1.1 Purpose {#section-20-1-1}

The facts table is a flat relation keyed by entity URI. Entity-to-entity connections exist implicitly: any fact whose `value.type = "ref"` and whose value URI denotes a known entity constitutes a directed edge from the subject entity to the referenced entity.

<div className="stigmem-keypoint">

**Without a materialized adjacency structure, multi-hop traversal requires O(k × |F|) full table scans per recall query.**

§20 mandates a materialized `entity_edges` table to enable
efficient bounded-depth BFS.

</div>

#### §20.1.2 Schema {#section-20-1-2}

```sql
CREATE TABLE IF NOT EXISTS entity_edges (
    id              TEXT PRIMARY KEY,      -- edge UUID (= source fact id)
    subject         TEXT NOT NULL,         -- normalized entity URI ("from" node)
    relation        TEXT NOT NULL,         -- predicate / edge label
    object          TEXT NOT NULL,         -- normalized entity URI ("to" node)
    scope           TEXT NOT NULL,
    confidence      REAL NOT NULL,         -- mirrors fact.confidence; updated by decay sweeper
    source_trust    REAL,                  -- cached t(fact.source) per §19.4; nullable
    decay_epoch     INTEGER,               -- Unix ms of last decay sweep touch
    created_at      INTEGER NOT NULL       -- Unix ms
);

CREATE INDEX IF NOT EXISTS idx_edges_subject     ON entity_edges (subject,  scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_object      ON entity_edges (object,   scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel ON entity_edges (subject,  relation, scope);
```

Implementations MUST create this table and all three indexes before accepting `PUT /v1/facts` calls that could produce ref-type values.

#### §20.1.3 Adjacency Invariants {#section-20-1-3}

<ol className="stigmem-steps">
<li><strong>Insert on ref fact.</strong> An <code>entity_edges</code> row MUST be inserted whenever a fact is persisted with <code>value.type = "ref"</code> and the <code>v</code> field passes entity-URI validation. The <code>id</code> MUST equal the source fact's <code>id</code>. The <code>object</code> MUST be the normalized form of the ref target URI.</li>
<li><strong>Decay sweep propagation.</strong> When the decay sweeper updates a fact's <code>confidence</code>, it MUST update the corresponding <code>entity_edges</code> row's <code>confidence</code> and <code>decay_epoch</code> in the same transaction.</li>
<li><strong>Retraction soft-delete.</strong> Set <code>confidence = 0.0</code> on the <code>facts</code> row AND on the <code>entity_edges</code> row (not hard-delete), AND insert a row into <code>fact_retractions(fact_id, retracted_at)</code>. The <code>fact_retractions</code> record is authoritative for time-travel queries.</li>
<li><strong>Garden scope.</strong> <code>entity_edges</code> rows inherit the fact's <code>scope</code>. Cross-garden traversal is governed by the caller's garden ACL checked at the application layer before returning results.</li>
<li><strong>Consistency.</strong> An <code>entity_edges</code> row MUST NOT outlive the deletion of its source fact. SHOULD use a foreign-key cascade or equivalent constraint.</li>
</ol>

#### §20.1.4 Edge Metadata Fields {#section-20-1-4}

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>id</code></dt>
<dt><span className="stigmem-fields__type">TEXT (UUID)</span></dt>
<dd>Primary key; equals the source fact's <code>id</code>.</dd>
</div>

<div>
<dt><code>subject</code> / <code>object</code></dt>
<dt><span className="stigmem-fields__type">TEXT (URI)</span></dt>
<dd>Normalized "from" / "to" entity URIs.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">TEXT</span></dt>
<dd>Predicate label from the source fact.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">TEXT</span></dt>
<dd>Garden or global scope identifier.</dd>
</div>

<div>
<dt><code>confidence</code></dt>
<dt><span className="stigmem-fields__type">REAL [0,1]</span></dt>
<dd>Current confidence; mirrors and tracks <code>facts.confidence</code>.</dd>
</div>

<div>
<dt><code>source_trust</code></dt>
<dt><span className="stigmem-fields__type">REAL [0,1]</span></dt>
<dd>Cached <code>t(fact.source)</code>. MAY be null for pre-Phase-9 data.</dd>
</div>

<div>
<dt><code>decay_epoch</code></dt>
<dt><span className="stigmem-fields__type">INTEGER</span></dt>
<dd>Unix ms of last decay sweep update.</dd>
</div>

<div>
<dt><code>created_at</code></dt>
<dt><span className="stigmem-fields__type">INTEGER</span></dt>
<dd>Unix ms of row creation (= fact insertion time).</dd>
</div>

</div>

#### §20.1.5 `neighbors()` Query Semantics {#section-20-1-5}

The `neighbors()` traversal is the primitive used by the recall pipeline's graph expansion stage and is also exposed directly via `GET /v1/graph/neighbors`.

```
GET /v1/graph/neighbors
  ?entity={entity_uri}
  &depth={k}            // integer 1–3; default 1; MUST reject > 3
  &relation_filter={rel_pattern}  // optional; comma-separated relation labels or glob patterns
  &scope={scope}        // required; MUST NOT traverse across scope boundaries
  &min_confidence={c}   // optional; default 0.1
  &min_trust={t}        // optional; default 0.0
  &cursor={opaque}      // pagination cursor
  &page_size={n}        // default 20; max 200
```

<div className="stigmem-grid">

<div><h4>Depth cap</h4><p>MUST cap depth at 3. Requests with <code>depth &gt; 3</code> MUST return HTTP 400 <code>graph_depth_exceeded</code>.</p></div>
<div><h4>Prune early</h4><p>SHOULD prune edges with <code>confidence &lt; min_confidence</code> or <code>source_trust &lt; min_trust</code> before BFS, not after, to reduce fanout.</p></div>
<div><h4>Glob only</h4><p><code>relation_filter</code> MAY use <code>&#42;</code> as a wildcard suffix. MUST NOT evaluate as full regex; only prefix-glob is supported.</p></div>
<div><h4>Shortest-path dedup</h4><p>Duplicate paths to the same neighbor MUST be de-duplicated; the shortest path (fewest hops) is reported.</p></div>

</div>

#### §20.1.6 Pagination and Cursor Stability {#section-20-1-6}

<div className="stigmem-grid">

<div><h4>Opaque</h4><p>Base64url-encoded to callers.</p></div>
<div><h4>Stable</h4><p>A cursor that was valid before a new fact was inserted MUST continue to work and MUST NOT skip or re-return neighbors that were present at cursor issuance.</p></div>
<div><h4>TTL 300 s</h4><p>Invalidated after <code>STIGMEM_CURSOR_TTL_S</code> seconds. Expired cursor returns HTTP 400 <code>cursor_expired</code>.</p></div>

</div>

The server MUST include a `next_cursor` field in the response only when more pages exist.

#### §20.1.7 Federation Integrity {#section-20-1-7}

<div className="stigmem-keypoint">

**The `entity_edges` table is local-node state.**

When facts are received from a federated peer, the receiving node
MUST apply the same insert/retract/decay invariants to its local
`entity_edges` table. Edges derived from federated facts MUST record
the peer's `source_trust` so that cross-node traversal paths carry
trust provenance. Nodes MUST NOT return federated-source edges in
`neighbors()` results when the caller's capability token lacks
cross-federation read scope.

</div>

---

### §20.2 Embedding Storage {#section-20-2}

#### §20.2.1 Vector Table {#section-20-2-1}

Implementations MUST use `sqlite-vec` for vector storage. The virtual table schema is:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
    id       TEXT PRIMARY KEY,
    embedding FLOAT[768]         -- default dimensionality; see §20.2.4
);
```

The `id` column is the source fact's `id` for per-fact embeddings, or the string `"card:{entity_uri}:{scope}"` for memory card embeddings.

#### §20.2.2 Embedding Unit {#section-20-2-2}

Each live fact (confidence > `STIGMEM_EMBED_MIN_CONFIDENCE`, default 0.1) MUST be embedded as the composed string:

```
"{entity_display} {relation} {value_text}"
```

where `entity_display` is the last path segment of the entity URI, `relation` is the fact's relation label, and `value_text` is the typed value's textual representation.

<div className="stigmem-keypoint">

**All embeddings MUST be L2-normalized to unit length on insertion.**

Cosine similarity reduces to a dot product, enabling sqlite-vec's
native dot-product acceleration. The 1-to-1 mapping (one embedding
per fact row) ensures that vector ANN retrieval returns individual,
attributable facts rather than entity-level blobs.

</div>

#### §20.2.3 Default Model {#section-20-2-3}

The default embedding model is `nomic-embed-text-v1.5` (768 dimensions, Apache-2.0, runnable offline via Ollama).

<div className="stigmem-fields">

<div>
<dt>Provider</dt>
<dt><span className="stigmem-fields__type">Model</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>ollama</code> (default)</dt>
<dt><span className="stigmem-fields__type">nomic-embed-text · 768</span></dt>
<dd>Offline; Matryoshka-capable.</dd>
</div>

<div>
<dt><code>ollama</code></dt>
<dt><span className="stigmem-fields__type">mxbai-embed-large · 1024</span></dt>
<dd>Higher recall; larger memory footprint.</dd>
</div>

<div>
<dt><code>openai</code></dt>
<dt><span className="stigmem-fields__type">text-embedding-3-small · 1536</span></dt>
<dd>Cloud opt-in; requires <code>OPENAI_API_KEY</code>.</dd>
</div>

<div>
<dt><code>voyage</code></dt>
<dt><span className="stigmem-fields__type">voyage-3-lite · 512</span></dt>
<dd>Cloud opt-in; requires <code>VOYAGE_API_KEY</code>.</dd>
</div>

</div>

#### §20.2.4 Dimensionality Declaration {#section-20-2-4}

Each node MUST record its configured embedding dimensionality in the `/.well-known/stigmem` response. `truncated_dimensions` MAY be set to a smaller integer when using Matryoshka-capable models; the floor for `nomic-embed-text-v1.5` is **64 dimensions**.

<div className="stigmem-keypoint">

**Implementations MUST refuse to mix embeddings of different dimensionalities in the same `vec_facts` table.**

If `STIGMEM_EMBED_DIMENSIONS` changes after facts have been indexed,
the node MUST refuse to start and emit a `vec_facts dimensionality
mismatch` error. Re-indexing is performed by draining and
re-inserting all rows.

</div>

#### §20.2.5 Embedding Lifecycle {#section-20-2-5}

<div className="stigmem-fields">

<div>
<dt>Event</dt>
<dt><span className="stigmem-fields__type">Action</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Fact inserted &gt; threshold</dt>
<dt><span className="stigmem-fields__type">embed + insert</span></dt>
<dd>Insert into <code>vec_facts</code>.</dd>
</div>

<div>
<dt>Value change</dt>
<dt><span className="stigmem-fields__type">re-embed</span></dt>
<dd>Update <code>vec_facts</code> row.</dd>
</div>

<div>
<dt>Confidence &lt; tombstone threshold</dt>
<dt><span className="stigmem-fields__type">delete</span></dt>
<dd>Default 0.1. Stale low-confidence vectors pollute ANN results.</dd>
</div>

<div>
<dt>Confidence restored</dt>
<dt><span className="stigmem-fields__type">re-insert</span></dt>
<dd>Re-embed and re-insert.</dd>
</div>

<div>
<dt>Hard-delete</dt>
<dt><span className="stigmem-fields__type">delete (txn)</span></dt>
<dd>Same transaction.</dd>
</div>

</div>

#### §20.2.6 Contradiction Interaction {#section-20-2-6}

<div className="stigmem-keypoint">

**Both contradicting facts retain their embeddings.**

The contradiction penalty is applied at ranking time, not by
modifying stored vectors. Implementations MUST NOT delete or modify
the embedding of a contradicted fact.

</div>

---

### §20.3 Recall API {#section-20-3}

#### §20.3.1 Route {#section-20-3-1}

```
GET  /v1/recall
POST /v1/recall   (preferred when query text is long)
```

POST is preferred when `query` exceeds 1000 characters to avoid URI length limits. The MCP tool `recall` wraps the same endpoint with identical semantics.

#### §20.3.2 Request Shape {#section-20-3-2}

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Required · Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>query</code></dt>
<dt><span className="stigmem-fields__type">yes · —</span></dt>
<dd>Natural-language or structured query string.</dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">yes · —</span></dt>
<dd>Max tokens in the response payload.</dd>
</div>

<div>
<dt><code>depth</code></dt>
<dt><span className="stigmem-fields__type">no · 1 (max 2)</span></dt>
<dd>Graph expansion depth; capped lower than <code>neighbors()</code>'s max-3 to bound recall latency.</dd>
</div>

<div>
<dt><code>weights</code></dt>
<dt><span className="stigmem-fields__type">no · &#123;lex:0.30, vec:0.50, graph:0.20&#125;</span></dt>
<dd>Stage weights; MUST sum to 1.0 within ±0.001. Provisional — operators SHOULD re-tune against a held-out probe set.</dd>
</div>

<div>
<dt><code>include_low_trust</code></dt>
<dt><span className="stigmem-fields__type">no · false</span></dt>
<dd>If false, facts with effective confidence &lt; 0.2 are excluded.</dd>
</div>

<div>
<dt><code>entity</code> / <code>relation</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Entity URI enables entity-centric recall; relation filter skips memory card lookup.</dd>
</div>

<div>
<dt><code>lambda_mmr</code></dt>
<dt><span className="stigmem-fields__type">no · 0.7</span></dt>
<dd>MMR diversity-relevance tradeoff; 1.0 = pure relevance.</dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">no · 0.1</span></dt>
<dd>Minimum effective confidence for candidate inclusion.</dd>
</div>

</div>

**Validation errors:** `token_budget < 1` → `invalid_token_budget`; `depth > 2` → `recall_depth_exceeded`; weights not summing to 1.0 → `invalid_weights`.

#### §20.3.3 Ranking Pipeline {#section-20-3-3}

The recall pipeline runs three stages then fuses their candidate sets: **Stage 1 (Lexical / BM25)**, **Stage 2 (Dense ANN)**, **Stage 3 (Graph expansion BFS)**.

<div className="stigmem-keypoint">

**Stage 2 (ANN) scope enforcement MUST be applied via the join to `facts`.**

`vec_facts` carries no `scope` column. Implementations MUST NOT pass
ANN results to fusion before this join filter; doing so risks
cross-scope leakage. Implementations MUST ALSO verify the caller's
garden ACL for each Stage 2 candidate. Stage 3 seed entities MUST
have their garden ACL verified before BFS expansion begins.

</div>

Stage 3 edge score:

```
graph_score(f at entity e via edge x) =
  (1 / (1 + hops)) × edge.confidence / log(1 + out_degree(x.subject))
```

The `log(1 + out_degree)` denominator is the **hub-bias guard** — it penalizes hub entities whose facts would otherwise dominate graph expansion regardless of query relevance.

**Fusion formula:**

```
raw_score(f) = α · norm(bm25(f)) + β · norm(cosine_sim(f)) + γ · norm(graph_score(f))

salience(f)  = recency(f)
             × confidence_weight(f)
             × access_freq_weight(f)
             × contradiction_weight(f)
             × garden_tier(f)

score(f)     = raw_score(f) × salience(f) × source_trust_multiplier(f.source_trust)
```

**Salience signals:**

<div className="stigmem-fields">

<div>
<dt>Signal</dt>
<dt><span className="stigmem-fields__type">Formula</span></dt>
<dd>Range</dd>
</div>

<div>
<dt><code>recency(f)</code></dt>
<dt><span className="stigmem-fields__type"><code>exp(-0.01 × age_days)</code></span></dt>
<dd>(0, 1]</dd>
</div>

<div>
<dt><code>confidence_weight(f)</code></dt>
<dt><span className="stigmem-fields__type"><code>f.confidence</code></span></dt>
<dd>[0, 1]</dd>
</div>

<div>
<dt><code>access_freq_weight(f)</code></dt>
<dt><span className="stigmem-fields__type">log-normalized within set</span></dt>
<dd>[0, 1]</dd>
</div>

<div>
<dt><code>contradiction_weight(f)</code></dt>
<dt><span className="stigmem-fields__type">1.0 ok · 0.7 unresolved</span></dt>
<dd>&#123;0.7, 1.0&#125;</dd>
</div>

<div>
<dt><code>garden_tier(f)</code></dt>
<dt><span className="stigmem-fields__type">configurable</span></dt>
<dd>Default 1.0; quarantine default 0.2.</dd>
</div>

<div>
<dt><code>source_trust_multiplier(t)</code></dt>
<dt><span className="stigmem-fields__type"><code>0.5 + 0.5 × t</code></span></dt>
<dd>[0.5, 1]; 1.0 when <code>trust_mode = off</code>.</dd>
</div>

</div>

`access_count` MUST be incremented each time a fact appears in a recall response. SHOULD batch increments (flush interval ≤ 30 s).

#### §20.3.4 Token-Budget Packing (MMR) {#section-20-3-4}

The scored candidate set is packed using **Maximal Marginal Relevance**:

```
next = argmax_{f ∈ R \ selected} [
    λ_mmr · score(f)
  - (1 − λ_mmr) · max_{f_j ∈ selected} cosine_sim(embed(f), embed(f_j))
]
```

The loop runs until the remaining token budget cannot accommodate the next candidate.

```
token_cost(f) = 40 + ceil(len(value_text_utf8) / 4)
```

<div className="stigmem-keypoint">

**Empty-budget edge case: return empty `results` with `truncated: true`, NOT HTTP 400.**

The caller controls budget. When `entity` is specified
(entity-centric recall), MMR MUST be disabled; all facts for that
entity in scope are returned sorted by `score` descending.

</div>

#### §20.3.5 Response Shape {#section-20-3-5}

```json
{
  "query": "what is Alice's current role?",
  "token_budget": 512,
  "tokens_used": 340,
  "results": [
    {
      "id":          "3f7a…",
      "entity":      "https://example.com/entity/alice",
      "relation":    "memory:role",
      "value":       { "type": "text", "v": "CEO" },
      "confidence":  0.97,
      "source_trust": 0.90,
      "score":       0.843,
      "hops":        0,
      "contradicted": false,
      "card_stale":  false
    }
  ],
  "memory_card": null,
  "truncated": false,
  "scores_debug": null
}
```

`memory_card` is populated for entity-centric queries. `scores_debug` MAY be populated when `debug=true`; MUST be null in production responses.

#### §20.3.6 `include_low_trust` Behavior {#section-20-3-6}

When `include_low_trust = false` (default), facts with `effective_confidence = fact.confidence × source_trust < 0.2` MUST be excluded from all three stages before fusion. When `true`, they are included but the `source_trust_multiplier` still applies, so they rank lower.

---

### §20.4 Memory Cards {#section-20-4}

#### §20.4.1 Card Definition {#section-20-4-1}

A **memory card** is a per-entity synthesized text summary stored as a fact with:

```
entity:   {entity-uri}
relation: stigmem:memory:card
value:    { "type": "text", "v": {card_markdown} }
source:   "system:stigmem:card-generator"
scope:    {same scope as constituent facts}
confidence: 1.0
```

<div className="stigmem-keypoint">

**`confidence = 1.0` expresses confidence in the card's existence, not its content accuracy.**

Cards are NOT subject to the fact decay sweeper.

</div>

#### §20.4.2 Card Schema {#section-20-4-2}

The `value.v` field is structured Markdown containing entity metadata, current facts table, contradictions list, and source summary.

<div className="stigmem-grid">

<div><h4>Effective confidence ≥ 0.3</h4><p>MUST include all live facts (<code>fact.confidence × source_trust</code>).</p></div>
<div><h4>Sort relation/HLC</h4><p>MUST sort rows by <code>(relation ASC, hlc DESC)</code> so the most recent assertion per relation appears first.</p></div>
<div><h4>Surface contradictions</h4><p>MUST surface both values and confidences. Cards MUST NOT silently resolve contradictions.</p></div>
<div><h4>4000 token cap</h4><p>Include the highest-confidence facts and append <code>… &#123;n_omitted&#125; lower-confidence facts omitted</code>.</p></div>
<div><h4>Single (entity, scope, garden_id)</h4><p>The card generator MUST NOT mix garden-scoped facts into a cross-garden card.</p></div>

</div>

The card is also embedded as a unit for entity-level semantic search; its `vec_facts` key is `"card:{entity_uri}:{scope}"`.

#### §20.4.3 Refresh Policy {#section-20-4-3}

Cards MUST NOT be subject to confidence decay. They are invalidated and queued for async refresh on these triggers:

<div className="stigmem-fields">

<div>
<dt>Trigger</dt>
<dt><span className="stigmem-fields__type">Action</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>New fact for entity</dt>
<dt><span className="stigmem-fields__type">async refresh</span></dt>
<dd>Invalidate card; enqueue background refresh.</dd>
</div>

<div>
<dt>Decay sweep touch</dt>
<dt><span className="stigmem-fields__type">async refresh</span></dt>
<dd>Constituent confidence change.</dd>
</div>

<div>
<dt>Card age &gt; <code>STIGMEM_CARD_MAX_AGE_S</code></dt>
<dt><span className="stigmem-fields__type">async refresh</span></dt>
<dd>Default 86400 s.</dd>
</div>

<div>
<dt>Contradiction resolved</dt>
<dt><span className="stigmem-fields__type">async refresh</span></dt>
<dd>Via <code>POST /v1/conflicts/:id/resolve</code>.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**During refresh, the stale card remains readable and is served with `card_stale: true`.**

When `force_refresh = true`, card regeneration is synchronous and
MUST complete within 500 ms. If exceeded, the stale card (or raw
facts if no card exists) MUST be returned with `card_stale: true`
and `force_refresh_timeout: true`.

</div>

#### §20.4.4 Recall Integration {#section-20-4-4}

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Entity-centric, card exists</dt>
<dt><span className="stigmem-fields__type">card + raw facts</span></dt>
<dd>Return card as <code>memory_card</code>; top-N raw facts as <code>results</code>.</dd>
</div>

<div>
<dt>Relation filter</dt>
<dt><span className="stigmem-fields__type">skip card</span></dt>
<dd>Return raw facts for that relation.</dd>
</div>

<div>
<dt>Card stale, no force</dt>
<dt><span className="stigmem-fields__type">stale + top-10</span></dt>
<dd>Return stale card with <code>card_stale: true</code> + top-10 raw facts.</dd>
</div>

<div>
<dt>Contradictions + include flag</dt>
<dt><span className="stigmem-fields__type">card + pairs</span></dt>
<dd>Return card + raw fact pairs for each contradiction.</dd>
</div>

<div>
<dt>No card</dt>
<dt><span className="stigmem-fields__type">raw + async gen</span></dt>
<dd>Return raw facts; trigger async card generation.</dd>
</div>

<div>
<dt>Generation in flight</dt>
<dt><span className="stigmem-fields__type">no block</span></dt>
<dd>Return raw facts immediately; do not block.</dd>
</div>

<div>
<dt>Not entity-centric</dt>
<dt><span className="stigmem-fields__type">skip card</span></dt>
<dd>Run full hybrid pipeline on raw facts.</dd>
</div>

</div>

Implementations MUST verify the caller's garden ACL against the card's `garden_id` before including the card in a recall response. Cards in unauthorized gardens MUST be excluded; the fallback is raw facts from authorized gardens only.

#### §20.4.5 Divergence Policy {#section-20-4-5}

<div className="stigmem-keypoint">

**Implementations MUST NOT serve a card whose content is known to be inconsistent with live facts.**

When raw facts contradict the card's synthesized summary, the card
MUST be invalidated immediately and the divergent fact MUST be
included in the `results` array with `card_stale: true`.

</div>

---

### §20.5 Subscriptions {#section-20-5}

The subscription primitive has been extracted into the colocated experimental spec [`Spec-X7-Subscriptions`](./subscriptions). Recall and graph implementations that emit card-refresh or fact-change notifications depend on that spec for event delivery semantics.

---

### §20.6 Causal / Derivation Links {#section-20-6}

#### §20.6.1 `derived_from` Lifecycle {#section-20-6-1}

The `derived_from` field on a fact is a JSON array of FactHash references identifying the source facts from which this fact was inferred or synthesized.

<ol className="stigmem-steps">
<li>Each entry MUST be a 64-character lowercase hex string (SHA-256 of the referenced fact's canonical wire representation).</li>
<li><code>derived_from</code> arrays MUST NOT contain cycles. The <code>PUT /v1/facts</code> handler MUST verify acyclicity before persisting. Cycles MUST be rejected with HTTP 400 <code>provenance_cycle_detected</code>.</li>
<li><code>derived_from</code> references MAY point to facts that no longer exist. Dangling references are valid — they preserve audit lineage.</li>
<li>Implementations MUST NOT alter <code>derived_from</code> after the fact is created. <code>PATCH</code> MUST reject with HTTP 422 <code>derived_from_immutable</code>.</li>
</ol>

#### §20.6.2 Provenance Walk {#section-20-6-2}

```
GET /v1/facts/:id/provenance
  ?depth={k}      // max 5; default 3
  &scope={scope}
```

<div className="stigmem-keypoint">

**The response MUST be indistinguishable from a missing fact to prevent cross-scope inference attacks.**

Implementations MUST verify caller read access to the root fact's
scope and `garden_id` before executing the walk. Unauthorized root
facts MUST return HTTP 403 with no node or edge data. Facts in
unauthorized scopes or gardens MUST be represented as
`{ "hash": "…", "exists": false }` — identical to genuinely absent
facts.

</div>

#### §20.6.3 Recall Integration {#section-20-6-3}

When `GET /v1/recall` returns a derived fact, its `derived_from` hashes MUST be included in the result object. Implementations SHOULD include the immediate parent facts (depth=1) in the `results` array when their token cost fits, annotated with `"provenance_of": "{derived_fact_id}"`. If the budget is tight, parent facts MUST be omitted (not truncated); the `derived_from` hashes allow a follow-up provenance walk.

Derivation depth contributes to the `graph_score` discount: each additional derivation hop applies a multiplier of 0.9 to the fact's `confidence_weight` salience signal.

#### §20.6.4 Derivation Link and Federation {#section-20-6-4}

When a derived fact is replicated to a peer via federation, the `derived_from` hashes MUST be transmitted in the wire format. The receiving node MUST store them as-is; it MUST NOT attempt to resolve hashes that it does not have locally. Dangling hashes on the receiving node are valid and MUST NOT prevent the fact from being persisted.

---

### §20.7 Schema Migrations {#section-20-7}

The following migrations MUST be applied when upgrading to pre-reset graph & recall design (v1.1 spec compliance):

```sql
-- Graph index
CREATE TABLE IF NOT EXISTS entity_edges ( ... );
CREATE INDEX IF NOT EXISTS idx_edges_subject     ON entity_edges (subject, scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_object      ON entity_edges (object,  scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel ON entity_edges (subject, relation, scope);

-- Vector table (sqlite-vec required)
CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
    id        TEXT PRIMARY KEY,
    embedding FLOAT[768]
);

-- Access frequency tracking
ALTER TABLE facts ADD COLUMN IF NOT EXISTS access_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS last_accessed_at INTEGER;

-- Subscription storage is owned by Spec-X7-Subscriptions.
```

#### §20.8 Error Reference {#section-20-8}

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>graph_depth_exceeded</code></span></dt>
<dd><code>neighbors()</code> or <code>recall</code> depth &gt; max allowed.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>cursor_expired</code></span></dt>
<dd>Pagination cursor TTL exceeded.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>invalid_token_budget</code></span></dt>
<dd><code>token_budget &lt; 1</code>.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>recall_depth_exceeded</code></span></dt>
<dd><code>depth &gt; 2</code> on recall request.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>invalid_weights</code></span></dt>
<dd><code>weights</code> values do not sum to 1.0 ± 0.001.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>provenance_cycle_detected</code></span></dt>
<dd><code>derived_from</code> graph contains a cycle.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>invalid_relation_filter</code></span></dt>
<dd><code>relation_filter</code> uses unsupported regex beyond prefix-glob.</dd>
</div>

<div>
<dt>422</dt>
<dt><span className="stigmem-fields__type"><code>derived_from_immutable</code></span></dt>
<dd>Attempt to modify <code>derived_from</code> on an existing fact.</dd>
</div>

<div>
<dt>422</dt>
<dt><span className="stigmem-fields__type"><code>embed_dimensionality_mismatch</code></span></dt>
<dd><code>vec_facts</code> configured dimensions differ from stored.</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type"><code>fact_not_found</code></span></dt>
<dd>Provenance walk root fact not found.</dd>
</div>

</div>

---
