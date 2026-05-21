---
spec_id: Spec-X11-Recall-Graph
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
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

**Status:** Experimental / dormant source package. Archived source material was drafted as normative, but this spec is deferred from the supported v0.9.0aN surface and must pass ADR-008 gates before reintroduction.

Graph adjacency index, vector embeddings, hybrid recall pipeline, memory cards, and causal links.

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for recall graph semantics.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** Experimental. Implementation issues may reference this preserved design, but it is not part of the supported default install.
**Depends on:** §2 (fact shape), §5 (wire format), §17 (memory garden), §18 (source attestation), §19 (federation trust).

§20 defines the graph adjacency index, embedding storage, recall API, memory
cards, and causal/derivation link lifecycle. The subscription primitive that
previously lived in §20.5 is now colocated under
[`Spec-X7-Subscriptions`](../subscriptions/spec.md).

---

### §20.1 Graph Index {#section-20-1}

#### §20.1.1 Purpose {#section-20-1-1}

The facts table is a flat relation keyed by entity URI. Entity-to-entity connections exist implicitly: any fact whose `value.type = "ref"` and whose value URI denotes a known entity constitutes a directed edge from the subject entity to the referenced entity. Without a materialized adjacency structure, multi-hop traversal requires O(k × |F|) full table scans per recall query. §20 mandates a materialized `entity_edges` table to enable efficient bounded-depth BFS.

#### §20.1.2 Schema {#section-20-1-2}

The `entity_edges` table materializes the implicit graph encoded in `ref`-typed fact values. Each row corresponds to a single ref-fact and mirrors its confidence and scope so the graph traversal stage can filter by scope and sort by edge weight without joining back to the facts table. The `source_trust` column caches the trust score from §19.4 at edge-creation time; it is nullable because trust scoring is an optional feature. The `decay_epoch` column tracks when the decay sweeper (§15) last touched this edge, allowing the sweeper to skip recently processed rows. Three indexes cover the two traversal directions (subject→object, object→subject) and a subject+relation composite for relation-filtered neighbor queries.

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

1. **Insert on ref fact.** An `entity_edges` row MUST be inserted whenever a fact is persisted with `value.type = "ref"` and the `v` field passes entity-URI validation. The `id` MUST equal the source fact's `id`. The `object` MUST be the normalized form of the ref target URI.
2. **Decay sweep propagation.** When the decay sweeper updates a fact's `confidence`, it MUST update the corresponding `entity_edges` row's `confidence` and `decay_epoch` in the same transaction.
3. **Retraction soft-delete.** When a fact is retracted, the implementation MUST: (a) set `confidence = 0.0` on the `facts` row (live-query compat), (b) set `confidence = 0.0` on the `entity_edges` row (not hard-delete), AND (c) insert a row into `fact_retractions(fact_id, retracted_at)` with `retracted_at = NOW()`. The `fact_retractions` record is the authoritative timestamp for time-travel queries (§24.2.1 c.3); the in-place `confidence = 0.0` update is retained for live-query backward compatibility only. Hard deletion is a maintenance-window operation only.
4. **Garden scope.** `entity_edges` rows inherit the fact's `scope`. Cross-garden traversal is governed by the caller's garden ACL checked at the application layer before returning traversal results (§17.3).
5. **Consistency.** An `entity_edges` row MUST NOT outlive the deletion of its source fact from the facts table. Implementations SHOULD use a foreign-key cascade or equivalent constraint to enforce this.

#### §20.1.4 Edge Metadata Fields {#section-20-1-4}

| Field | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key; equals the source fact's `id`. |
| `subject` | TEXT (URI) | Normalized "from" entity URI. |
| `relation` | TEXT | Predicate label from the source fact. |
| `object` | TEXT (URI) | Normalized "to" entity URI (the ref target). |
| `scope` | TEXT | Garden or global scope identifier. |
| `confidence` | REAL [0,1] | Current confidence; mirrors and tracks `facts.confidence`. |
| `source_trust` | REAL [0,1] | Cached `t(fact.source)` from §19.4.4. MAY be null for pre-Phase-9 data. |
| `decay_epoch` | INTEGER | Unix ms of last decay sweep update. |
| `created_at` | INTEGER | Unix ms of row creation (= fact insertion time). |

#### §20.1.5 `neighbors()` Query Semantics {#section-20-1-5}

The `neighbors()` traversal is the primitive used by the recall pipeline's graph expansion stage and is also exposed directly via `GET /v1/graph/neighbors`.

**Request:**

```
GET /v1/graph/neighbors
  ?entity={entity_uri}
  &depth={k}            // integer 1–3; default 1; MUST reject > 3
  &relation_filter={rel_pattern}  // optional; comma-separated relation labels or glob patterns
  &scope={scope}        // required; MUST NOT traverse across scope boundaries
  &min_confidence={c}   // optional; default 0.1
  &min_trust={t}        // optional; default 0.0
  &cursor={opaque}      // pagination cursor (see §20.1.6)
  &page_size={n}        // default 20; max 200
```

**Response:**

```json
{
  "entity": "https://example.com/entity/alice",
  "depth": 2,
  "neighbors": [
    {
      "entity": "https://example.com/entity/beta-corp",
      "relation": "memory:employer",
      "hops": 1,
      "confidence": 0.92,
      "source_trust": 0.85,
      "path": ["https://example.com/entity/alice"]
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIwfQ",
  "total_hint": 47
}
```

**Normative rules:**

- Implementations MUST cap depth at 3. Requests with `depth > 3` MUST return HTTP 400 with error code `graph_depth_exceeded`.
- Implementations SHOULD prune edges with `confidence < min_confidence` or `source_trust < min_trust` before beginning BFS, not after, to reduce traversal fanout.
- `relation_filter` MAY use `*` as a wildcard suffix (e.g., `memory:*` matches all `memory:` relations). Implementations MUST NOT evaluate `relation_filter` as a full regex; only prefix-glob is supported.
- Duplicate paths to the same neighbor entity MUST be de-duplicated; the shortest path (fewest hops) is reported.

#### §20.1.6 Pagination and Cursor Stability {#section-20-1-6}

The `neighbors()` endpoint uses cursor-based pagination. Cursors MUST be:

- Opaque (base64url-encoded) to callers.
- Stable for the lifetime of the underlying fact data: a cursor that was valid before a new fact was inserted MUST continue to work and MUST NOT skip or re-return neighbors that were present at the time the cursor was issued.
- Invalidated (gracefully) after `STIGMEM_CURSOR_TTL_S` seconds (default 300). A request with an expired cursor MUST return HTTP 400 with error code `cursor_expired`.

The server MUST include a `next_cursor` field in the response only when more pages exist. An absent `next_cursor` indicates the final page.

#### §20.1.7 Federation Integrity {#section-20-1-7}

The `entity_edges` table is **local-node state**. When facts are received from a federated peer (§19.3), the receiving node MUST apply the same insert / retract / decay invariants (§20.1.3) to its local `entity_edges` table. Edges derived from federated facts MUST record the peer's `source_trust` in the `source_trust` field (as computed per §19.4.4) so that cross-node traversal paths carry trust provenance.

Nodes MUST NOT return federated-source edges in `neighbors()` results when the caller's capability token lacks cross-federation read scope (§19.5.2).

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

The `id` column is the source fact's `id` for per-fact embeddings, or the string `"card:{entity_uri}:{scope}"` for memory card embeddings (§20.4.2).

#### §20.2.2 Embedding Unit {#section-20-2-2}

Each live fact (confidence > `STIGMEM_EMBED_MIN_CONFIDENCE`, default 0.1) MUST be embedded as the composed string:

```
"{entity_display} {relation} {value_text}"
```

where:
- `entity_display` is the last path segment of the entity URI (e.g., `alice` from `https://example.com/entity/alice`).
- `relation` is the fact's relation label.
- `value_text` is: for `value.type = "text"`, the raw `v` string; for `value.type = "ref"`, the last path segment of the ref URI; for `value.type = "number"`, the decimal string; for `value.type = "bool"`, `"true"` or `"false"`.

This 1-to-1 mapping (one embedding per fact row) ensures that vector ANN retrieval returns individual, attributable facts rather than entity-level blobs. Memory card embeddings (§20.4.2) form a secondary, entity-level index.

All embeddings MUST be L2-normalized to unit length on insertion so that cosine similarity reduces to a dot product, enabling sqlite-vec's native dot-product acceleration. Implementations MUST document that raw stored vectors are unit-norm.

#### §20.2.3 Default Model {#section-20-2-3}

The default embedding model is `nomic-embed-text-v1.5` (768 dimensions, Apache-2.0, runnable offline via Ollama: `ollama pull nomic-embed-text`). This model is chosen because it is open-weight, runs without network access, and achieves MTEB retrieval avg ~53.1 on the standard benchmark set (MTEB leaderboard, 2025-05-04), which is representative of the fact-recall workload.

Alternative models are supported via environment configuration:

| `STIGMEM_EMBED_PROVIDER` | `STIGMEM_EMBED_MODEL` | Dimensions | Notes |
|---|---|---|---|
| `ollama` (default) | `nomic-embed-text` (default) | 768 | Offline; Matryoshka-capable |
| `ollama` | `mxbai-embed-large` | 1024 | Higher recall; larger memory footprint |
| `openai` | `text-embedding-3-small` | 1536 | Cloud opt-in; requires `OPENAI_API_KEY` |
| `voyage` | `voyage-3-lite` | 512 | Cloud opt-in; requires `VOYAGE_API_KEY` |

#### §20.2.4 Dimensionality Declaration {#section-20-2-4}

Each node MUST record its configured embedding dimensionality in the `/.well-known/stigmem` response:

```json
{
  "embedding": {
    "model": "nomic-embed-text-v1.5",
    "provider": "ollama",
    "dimensions": 768,
    "truncated_dimensions": null
  }
}
```

`truncated_dimensions` MAY be set to a smaller integer (e.g., 256) when using Matryoshka-capable models and the operator has configured dimension truncation for resource-constrained deployments. Implementations MUST use only the first `truncated_dimensions` components from the model's output. Implementations MUST document the minimum effective `truncated_dimensions` for each supported model; for `nomic-embed-text-v1.5` this floor is **64 dimensions** — setting `truncated_dimensions` below this value MUST be rejected with error `embed_dimensions_below_floor`.

**Incompatibility rule:** Implementations MUST refuse to mix embeddings of different dimensionalities in the same `vec_facts` table. If `STIGMEM_EMBED_DIMENSIONS` is changed after facts have been indexed, the node MUST refuse to start and emit the error:

```
FATAL: vec_facts dimensionality mismatch: stored=768 configured=1536. Re-index required.
```

Re-indexing is performed by draining and re-inserting all rows into `vec_facts` with the new model. Nodes MUST NOT silently drop or truncate existing embeddings when dimensions change.

#### §20.2.5 Embedding Lifecycle {#section-20-2-5}

| Event | Action |
|---|---|
| Fact inserted with confidence > threshold | Embed and insert into `vec_facts` |
| Fact updated (value change) | Re-embed and update `vec_facts` row |
| Fact confidence drops below `embed_tombstone_threshold` (default 0.1) | Delete from `vec_facts` |
| Fact confidence restored above threshold | Re-embed and re-insert into `vec_facts` |
| Fact hard-deleted | Delete from `vec_facts` (MUST be in same transaction) |

Stale low-confidence vectors MUST be deleted; they pollute ANN results with semantically present but epistemically discredited facts.

#### §20.2.6 Contradiction Interaction {#section-20-2-6}

Both contradicting facts retain their embeddings. The contradiction penalty is applied at ranking time (§20.3.3), not by modifying stored vectors. Implementations MUST NOT delete or modify the embedding of a contradicted fact; they MUST apply the scoring penalty using the `contradicted` flag from the facts table.

---

### §20.3 Recall API {#section-20-3}

#### §20.3.1 Route {#section-20-3-1}

The recall endpoint supports both GET and POST. GET is convenient for short queries and cacheable at HTTP intermediaries; POST is preferred when the query string exceeds 1000 characters to avoid URI length limits imposed by proxies and load balancers.

```
GET  /v1/recall
POST /v1/recall   (preferred when query text is long)
```

The POST form accepts a JSON body identical to the query parameters below. Both forms are equivalent; POST is preferred when `query` exceeds 1000 characters to avoid URI length limits.

The MCP tool `recall` wraps the same endpoint with identical semantics.

#### §20.3.2 Request Shape {#section-20-3-2}

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | — | Natural-language or structured query string |
| `token_budget` | integer | Yes | — | Max tokens in the response payload (exclusive of field labels) |
| `depth` | integer | No | 1 | Graph expansion depth for the traversal stage; max 2 (capped lower than `neighbors()` max-3 to bound recall latency at the P95 target) |
| `weights` | object | No | `{lexical:0.30, vector:0.50, graph:0.20}` | Stage weights; MUST sum to 1.0 within ±0.001. **These defaults are provisional** — operators SHOULD re-tune `α`, `β`, `γ` against a held-out probe set (recall@10, MRR) before production use. |
| `include_low_trust` | boolean | No | `false` | If `false`, facts with effective confidence < 0.2 are excluded |
| `entity` | string | No | — | Entity URI; enables entity-centric recall (card-first) |
| `relation` | string | No | — | Relation label filter; skips memory card lookup |
| `scope` | string | No | global | Garden or global scope |
| `include_contradicted` | boolean | No | `false` | Include contradicted facts in results |
| `force_refresh` | boolean | No | `false` | Block on synchronous memory card refresh before responding |
| `lambda_mmr` | float | No | 0.7 | MMR diversity-relevance tradeoff; 1.0 = pure relevance (greedy) |
| `min_confidence` | float | No | 0.1 | Minimum effective confidence for candidate inclusion |

**Validation:**
- Implementations MUST reject `token_budget < 1` with HTTP 400, error code `invalid_token_budget`.
- Implementations MUST reject `depth > 2` with HTTP 400, error code `recall_depth_exceeded`.
- Implementations MUST reject `weights` that do not sum to 1.0 ± 0.001 with HTTP 400, error code `invalid_weights`.

#### §20.3.3 Ranking Pipeline {#section-20-3-3}

The recall pipeline runs three stages then fuses their candidate sets.

**Stage 1 — Lexical (FTS5 / BM25):**

```sql
SELECT f.id, bm25(facts_fts) AS bm25_score
FROM facts_fts
WHERE facts_fts MATCH tokenize(query)
  AND scope = :scope
  AND confidence >= :min_confidence
ORDER BY bm25_score
LIMIT 200
```

**Stage 2 — Dense (ANN):**

```sql
SELECT vf.id, vf.distance
FROM vec_facts vf
JOIN facts f ON f.id = vf.id
WHERE vf.embedding MATCH embed(query)
  AND vf.k = 200
  AND f.scope = :scope
  AND f.confidence >= :min_confidence
```

`vec_facts` carries no `scope` column; scope enforcement MUST be applied via the join to `facts` as shown above. Implementations MUST NOT pass ANN results to the fusion stage before this join filter; doing so risks cross-scope leakage. Implementations MUST ALSO verify the caller's garden ACL for each Stage 2 candidate before passing it to fusion — scope filtering alone is insufficient if the caller's garden access does not cover the candidate's `garden_id`.

Cosine similarity `= 1 - distance` for unit-norm vectors.

**Stage 3 — Graph expansion (BFS on `entity_edges`):**

Seed entities are the distinct `entity` values from the union of stage 1 and stage 2 results. Seed entities MUST have their garden ACL verified before BFS expansion begins; entities in unauthorized gardens MUST be dropped as seeds. Expand to depth ≤ `depth` (max 2). For each reached entity, include the top-20 facts by effective confidence. Edge score:

```
graph_score(f at entity e via edge x) =
  (1 / (1 + hops)) × edge.confidence / log(1 + out_degree(x.subject))
```

The `log(1 + out_degree)` denominator is the **hub-bias guard**: it penalizes hub entities (e.g., a root namespace entity with thousands of outbound edges) whose facts would otherwise dominate graph expansion results regardless of query relevance.

**Fusion formula:**

For each candidate fact `f` across all three candidate sets:

```
raw_score(f) = α · norm(bm25(f)) + β · norm(cosine_sim(f)) + γ · norm(graph_score(f))

salience(f)  = recency(f)
             × confidence_weight(f)
             × access_freq_weight(f)
             × contradiction_weight(f)
             × garden_tier(f)

score(f)     = raw_score(f) × salience(f) × source_trust_multiplier(f.source_trust)
```

where `norm(·)` is min-max normalization within the candidate set independently for each stage (missing stage values normalize to 0.0), and:

| Salience signal | Formula | Range |
|---|---|---|
| `recency(f)` | `exp(-0.01 × age_days)` | (0, 1] |
| `confidence_weight(f)` | `f.confidence` | [0, 1] |
| `access_freq_weight(f)` | `log(1 + access_count) / log(1 + max_access_count)` within candidate set | [0, 1] |
| `contradiction_weight(f)` | 1.0 if no unresolved contradiction; 0.7 otherwise | {0.7, 1.0} |
| `garden_tier(f)` | Configurable per garden; default 1.0; quarantine garden default 0.2 | [0, 1] |
| `source_trust_multiplier(t)` | `0.5 + 0.5 × t` (maps [0,1] → [0.5,1.0]); 1.0 when `trust_mode = off` | [0.5, 1] |

The `access_count` field on fact rows MUST be incremented each time a fact appears in a recall response. Implementations SHOULD batch these increments (flush interval ≤ 30s) to avoid write contention.

#### §20.3.4 Token-Budget Packing (MMR) {#section-20-3-4}

The scored candidate set is packed into the response using **Maximal Marginal Relevance (MMR)**:

```
next = argmax_{f ∈ R \ selected} [
    λ_mmr · score(f)
  - (1 − λ_mmr) · max_{f_j ∈ selected} cosine_sim(embed(f), embed(f_j))
]
```

The loop runs until the remaining token budget cannot accommodate the next candidate. Implementations MUST estimate token cost as:

```
token_cost(f) = 40 + ceil(len(value_text_utf8) / 4)
```

The constant 40 accounts for field labels, punctuation, and newline overhead per result row. Implementations MUST stay under `token_budget`; they MUST NOT return a partial result row to fit exactly.

**Empty-budget edge case:** When no candidate's `token_cost` fits within the remaining budget — including when `token_budget` is too small to hold even the smallest candidate — implementations MUST return an empty `results` array with `truncated: true` and `tokens_used: 0`. They MUST NOT return HTTP 400; the caller controls budget.

**Exception:** When `entity` is specified (entity-centric recall), MMR MUST be disabled. All facts for that entity in scope are returned sorted by `score` descending, up to the token budget.

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

- `memory_card` is populated for entity-centric queries (§20.4.4).
- `truncated: true` indicates the result set was cut to fit `token_budget`.
- `scores_debug` MAY be populated (with stage-level scores) when the request includes `debug=true`; MUST be null in production responses.

#### §20.3.6 `include_low_trust` Behavior {#section-20-3-6}

When `include_low_trust = false` (default), facts with `effective_confidence = fact.confidence × source_trust < 0.2` MUST be excluded from all three stages before fusion. When `include_low_trust = true`, they are included but the `source_trust_multiplier` still applies, so they rank lower.

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

The `confidence = 1.0` field expresses confidence in the card's _existence_, not its content accuracy. Cards are NOT subject to the fact decay sweeper (§20.4.3).

#### §20.4.2 Card Schema {#section-20-4-2}

The `value.v` field is structured Markdown:

```markdown
## {entity_display_name}

**Type:** {entity_type}  **URI:** {entity_uri}  **Last refreshed:** {iso8601}

### Current facts ({n} live, {m} contradicted)

| Relation | Value | Confidence | Source | Since |
|----------|-------|------------|--------|-------|
| memory:role | CEO | 1.00 | agent/assistant | 2026-04-01 |
...

### Contradictions ({m} unresolved)

- **memory:role**: `CEO` (conf 1.00) ⟷ `CTO` (conf 0.80) — *unresolved*

### Sources

{n_sources} distinct sources; trust range [{min_t:.2f}, {max_t:.2f}]
```

**Content rules:**
- MUST include all live facts with effective confidence ≥ 0.3 (fact.confidence × source_trust per §19.4.4).
- MUST sort rows by `(relation ASC, hlc DESC)` so the most recent assertion per relation appears first.
- MUST surface contradictions explicitly with both values and their confidences. Cards MUST NOT silently resolve contradictions.
- MUST cap content at 4000 tokens. When an entity's facts exceed this limit, include the highest-confidence facts and append `… {n_omitted} lower-confidence facts omitted`.
- MUST be scoped to a single `(entity, scope, garden_id)` triple where `garden_id` may be null. The card generator MUST NOT mix garden-scoped facts into a cross-garden card.

The card is also embedded as a unit for entity-level semantic search; its `vec_facts` key is `"card:{entity_uri}:{scope}"` (§20.2.1).

#### §20.4.3 Refresh Policy {#section-20-4-3}

Cards MUST NOT be subject to confidence decay. They are invalidated and queued for async refresh on these triggers:

| Trigger | Action |
|---|---|
| New fact asserted for entity | Invalidate card; enqueue background refresh |
| Decay sweep touches a constituent fact (confidence changes) | Invalidate card; enqueue background refresh |
| Card age exceeds `STIGMEM_CARD_MAX_AGE_S` (default: 86400 s) | Background job invalidates and refreshes |
| Contradiction resolved via `POST /v1/conflicts/:id/resolve` | Invalidate card; enqueue refresh |

During refresh, the **stale card remains readable** and is served with `card_stale: true`. When `force_refresh = true`, card regeneration is synchronous and MUST complete within 500 ms. If the deadline is exceeded, the stale card (or raw facts if no card exists) MUST be returned with `card_stale: true` and `force_refresh_timeout: true`.

#### §20.4.4 Recall Integration {#section-20-4-4}

In `GET /v1/recall`, memory cards are used as follows:

| Condition | Behavior |
|---|---|
| `entity` param specified, no `relation` filter, card exists | Return card as `memory_card`; top-N raw facts as `results` |
| `relation` filter specified | Skip card; return raw facts for that relation |
| Card stale and `force_refresh = false` | Return stale card with `card_stale: true` + top-10 raw facts |
| Card has contradictions and `include_contradicted = true` | Return card + raw fact pairs for each contradiction |
| No card exists | Return raw facts; trigger async card generation |
| Card generation in flight | Return raw facts immediately; do not block |
| Query is not entity-centric (no `entity` param) | Skip card lookup; run full hybrid pipeline on raw facts |

Implementations MUST verify the caller's garden ACL against the card's `garden_id` before including the card in a recall response. Cards in unauthorized gardens MUST be excluded; when a card is excluded, the fallback is raw facts from authorized gardens only (following the rows above as if no card exists).

#### §20.4.5 Divergence Policy {#section-20-4-5}

When raw facts contradict the card's synthesized summary (i.e., a fact's current value differs from what was captured in a cached card), the card MUST be invalidated immediately and the divergent fact MUST be included in the `results` array of the recall response with `card_stale: true`. Implementations MUST NOT serve a card whose content is known to be inconsistent with live facts.

---

### §20.5 Subscriptions {#section-20-5}

The subscription primitive has been extracted into the colocated experimental
spec [`Spec-X7-Subscriptions`](../subscriptions/spec.md). Recall and graph
implementations that emit card-refresh or fact-change notifications depend on
that spec for event delivery semantics.

---

### §20.6 Causal / Derivation Links {#section-20-6}

#### §20.6.1 `derived_from` Lifecycle {#section-20-6-1}

The `derived_from` field on a fact (§2 v1.1 additions) is a JSON array of FactHash references identifying the source facts from which this fact was inferred or synthesized:

```json
{
  "entity": "https://example.com/entity/alice",
  "relation": "derived:tenure_days",
  "value": { "type": "number", "v": 730 },
  "derived_from": [
    "a3f9c2d1e8b74f6a…",    // 64-char lowercase hex SHA-256 of the start-date fact
    "b7e4d5f2a1c36e9b…"     // 64-char lowercase hex SHA-256 of the current-date fact
  ]
}
```

**Invariants:**

1. Each entry in `derived_from` MUST be a 64-character lowercase hex string (SHA-256 of the referenced fact's canonical wire representation per §5.3).
2. `derived_from` arrays MUST NOT contain cycles. The `PUT /v1/facts` handler MUST verify acyclicity before persisting. Cycles MUST be rejected with HTTP 400, error code `provenance_cycle_detected`.
3. `derived_from` references MAY point to facts that no longer exist (the source fact was retracted). Dangling references are valid — they preserve audit lineage.
4. Implementations MUST NOT alter `derived_from` after the fact is created. `PATCH /v1/facts/:id` MUST reject `derived_from` modifications with HTTP 422, error code `derived_from_immutable`.

#### §20.6.2 Provenance Walk {#section-20-6-2}

The provenance walk retrieves the full derivation graph for a given fact, following `derived_from` references recursively.

```
GET /v1/facts/:id/provenance
  ?depth={k}      // max 5; default 3
  &scope={scope}
```

Implementations MUST verify that the caller has read access to the root fact's scope and `garden_id` before executing the walk. Unauthorized root facts MUST return HTTP 403 with error code `access_denied`. No node or edge data MUST be returned for an unauthorized root fact.

**Response:**

```json
{
  "root_fact_id":   "{uuid}",
  "depth_limit":    3,
  "nodes": [
    { "id": "…", "entity": "…", "relation": "…", "value": {…}, "confidence": 0.9, "exists": true },
    { "hash": "a3f9c2d1e8b7…", "exists": false }   // retracted or unauthorized fact
  ],
  "edges": [
    { "derived_fact_id": "…", "source_hash": "a3f9c2d1e8b7…" }
  ],
  "truncated": false
}
```

Nodes with `"exists": false` represent either retracted source facts or facts in unauthorized scopes/gardens. When resolving `derived_from` references during the walk, implementations MUST check the caller's garden ACL for each referenced fact's scope and `garden_id`. Facts in unauthorized scopes or gardens MUST be represented as `{ "hash": "…", "exists": false }` — identical in shape to genuinely absent facts. Implementations MUST NOT confirm or deny the existence of facts in unauthorized scopes or gardens via the provenance walk; the response MUST be indistinguishable from a missing fact to prevent cross-scope inference attacks.

#### §20.6.3 Recall Integration {#section-20-6-3}

When `GET /v1/recall` returns a derived fact, its `derived_from` hashes MUST be included in the result object:

```json
{
  "id": "…",
  "entity": "…",
  "relation": "derived:tenure_days",
  "value": { "type": "number", "v": 730 },
  "derived_from": ["a3f9c2d1e8b7…", "b7e4d5f2a1c3…"],
  "confidence": 0.85,
  "score": 0.72
}
```

Implementations SHOULD include the immediate parent facts (depth=1) in the `results` array when their token cost fits within `token_budget`, annotated with `"provenance_of": "{derived_fact_id}"`. This allows consumers to verify derived facts without a separate API call. If the budget is tight, parent facts MUST be omitted (not truncated); the `derived_from` hashes allow a follow-up provenance walk.

Derivation depth contributes to the `graph_score` discount: each additional derivation hop applies a multiplier of 0.9 to the fact's `confidence_weight` salience signal, mirroring the intuition that derived facts carry less epistemic weight than directly observed facts.

#### §20.6.4 Derivation Link and Federation {#section-20-6-4}

When a derived fact is replicated to a peer via federation (§19.3), the `derived_from` hashes MUST be transmitted in the wire format. The receiving node MUST store them as-is; it MUST NOT attempt to resolve hashes that it does not have locally. Dangling hashes on the receiving node are valid and MUST NOT prevent the fact from being persisted.

---

### §20.7 Schema Migrations {#section-20-7}

The following migrations MUST be applied when upgrading to pre-reset graph & recall design (v1.1 spec compliance):

```sql
-- Graph index
CREATE TABLE IF NOT EXISTS entity_edges ( ... );  -- see §20.1.2
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
ALTER TABLE facts ADD COLUMN IF NOT EXISTS last_accessed_at INTEGER;  -- Unix ms

-- Subscription storage is owned by Spec-X7-Subscriptions.
```

#### §20.8 Error Reference {#section-20-8}

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `graph_depth_exceeded` | `neighbors()` or `recall` depth > max allowed |
| 400 | `cursor_expired` | Pagination cursor TTL exceeded |
| 400 | `invalid_token_budget` | `token_budget < 1` |
| 400 | `recall_depth_exceeded` | `depth > 2` on recall request |
| 400 | `invalid_weights` | `weights` values do not sum to 1.0 ± 0.001 |
| 400 | `provenance_cycle_detected` | `derived_from` graph contains a cycle |
| 400 | `invalid_relation_filter` | `relation_filter` uses unsupported regex beyond prefix-glob |
| 422 | `derived_from_immutable` | Attempt to modify `derived_from` on an existing fact |
| 422 | `embed_dimensionality_mismatch` | `vec_facts` configured dimensions differ from stored |
| 404 | `fact_not_found` | Provenance walk root fact not found |

---
