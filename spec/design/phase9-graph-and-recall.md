# Phase 9 Design Memo — Graph Index Shape and Recall Ranking

**Decision scope:** Four engineering decisions that spec §20 (`GET /v1/recall` normative route and MCP tool `recall`) and subsequent implementation issues build against.  
**Date:** 2026-05-04  
**Status:** Ready for CTO sign-off  
**Preconditions:** Stigmem v1.1 (§19 Federation Trust normative); facts store on SQLite + `sqlite-vec`; source-trust score `t(source)` already computed and cached per §19.4.

---

## 1. Graph Index Shape

### Decision

> Which adjacency structure do we materialize, what edge metadata do we keep, and how does it compose with the existing facts table for k-hop traversal?

### Context

The facts table is a flat relation: `(id, entity, relation, value, source, confidence, scope, hlc, …)`. Entity-to-entity connections exist implicitly: any fact whose `value.type = "ref"` and whose value URI is a known entity is a directed edge from `entity` to that URI. The current query path (`GET /v1/facts?entity=…`) retrieves facts _about_ one entity but cannot traverse to related entities without round-tripping through the application layer.

Phase 9's recall query — "what does this node know that is relevant to query Q?" — needs bounded multi-hop expansion. Without a materialized adjacency structure every traversal hop is a full table scan filtered by entity URI, making even 2-hop traversal prohibitively expensive on stores with > 50k facts.

### Options

| | Option A — No materialization | Option B — `entity_edges` table | Option C — Recursive CTE on facts |
|---|---|---|---|
| **Traversal cost** | O(k × \|F\|) per query; no index | O(k × degree) with covering index | O(k × \|F\|); CTE recompiled each call |
| **Write amplification** | None | One row per ref-type fact (~20–40% of typical stores) | None |
| **Metadata availability** | Join back to facts on every hop | Inline in edge row | Join back to facts on every hop |
| **Stale risk** | None (reads live facts) | Moderate; must invalidate on decay / confidence change | None (reads live facts) |
| **Implementation complexity** | Low | Medium | Low |

Option A degrades to full-scan traversal at any non-trivial scale. Option C trades computation for storage but recompiles the recursive CTE on every recall query and does not support metadata-driven traversal filtering (e.g., skip edges below a confidence threshold without a join). Option B has bounded write amplification — ref-type facts are a minority — and enables metadata-filtered traversal with a covering index.

### Recommendation: Option B — Materialized `entity_edges` table

**Schema:**

```sql
CREATE TABLE entity_edges (
    id              TEXT PRIMARY KEY,   -- edge UUID (= source fact id)
    subject         TEXT NOT NULL,      -- normalized entity URI (the "from" node)
    relation        TEXT NOT NULL,      -- predicate / edge label
    object          TEXT NOT NULL,      -- normalized entity URI (the "to" node)
    scope           TEXT NOT NULL,
    confidence      REAL NOT NULL,      -- mirrors fact.confidence; updated by decay sweeper
    source_trust    REAL,               -- cached t(fact.source) per §19.4; nullable
    decay_epoch     INTEGER,            -- Unix ms of last decay sweep touch
    created_at      INTEGER NOT NULL    -- Unix ms
);

CREATE INDEX idx_edges_subject  ON entity_edges (subject, scope, confidence);
CREATE INDEX idx_edges_object   ON entity_edges (object,  scope, confidence);
CREATE INDEX idx_edges_subject_rel ON entity_edges (subject, relation, scope);
```

**Invariants:**

1. A row is inserted into `entity_edges` whenever a fact is persisted with `value.type = "ref"` and the `v` field passes entity-URI validation. The `object` is the normalized ref target.
2. When the decay sweeper updates a fact's `confidence`, it MUST update the corresponding `entity_edges` row in the same transaction.
3. When a fact is retracted (`confidence = 0.0`), the edge row MUST be soft-deleted (set `confidence = 0.0`) not hard-deleted, to preserve audit lineage. Hard deletion is a maintenance-window operation.
4. Garden-tagged facts: `entity_edges` rows inherit the fact's `scope`. Cross-garden traversal is governed by the caller's garden ACL, checked at the application layer before returning traversal results.

**Traversal budget:** Recall queries MUST cap traversal at depth 2 by default (configurable up to 3). Unbounded BFS over a power-law-degree graph collapses to hub nodes (the hub-bias lens); depth-capping combined with degree-normalised scoring (§3 below) prevents this. Edges with `confidence < 0.1` or `source_trust < 0.2` SHOULD be pruned before traversal begins.

---

## 2. Embedding Strategy

### Decision

> What unit of text is embedded, which model is the default, and how do embeddings interact with decay and contradiction?

### Context

`sqlite-vec` is already the vector store backend. The open questions are what text to feed the embedding model, which model to use, and what staleness policy to enforce.

### What to embed

| | Option A — `value` only | Option B — composed triple string | Option C — memory card (entity-level) |
|---|---|---|---|
| **Semantic coverage** | Misses relation and entity; "CTO" embedded identically in "role:CTO" and "decision:use-CTO" | Full triple context; identical values on different relations are distinguished | Captures entity gestalt; noisy when entity has many unrelated facts |
| **Granularity** | Per-fact | Per-fact | Per-entity |
| **Staleness** | Invalidated on fact retraction | Invalidated on fact retraction | Invalidated on any fact change for the entity |
| **Index size** | N embeddings for N facts | N embeddings for N facts | M embeddings for M entities (M ≪ N) |
| **Recall accuracy for relational queries** | Poor | Good | Variable |

### Recommendation: Option B as primary + Option C as secondary (memory card) index

Embed the composed string `"{entity_display} {relation} {value_text}"` for each live fact (confidence > 0.1). For `value.type = "ref"`, use the entity's display name (last path segment of the URI) rather than the raw URI to improve semantic alignment. This is a 1-to-1 mapping: one embedding per fact row, stored in the `vec_facts` virtual table keyed by fact ID.

The memory card embedding (Option C) is described in §4 and serves entity-centric queries. It is a secondary index, not a replacement.

### Model recommendation: `nomic-embed-text-v1.5` as default

| Model | Dimensions | License | Runs locally | MTEB Retrieval avg | Notes |
|---|---|---|---|---|---|
| `nomic-embed-text-v1.5` | 768 | Apache-2.0 | Yes (Ollama) | 53.9 | Matryoshka; can truncate to 256/128 for smaller stores |
| `mxbai-embed-large-v1` | 1024 | Apache-2.0 | Yes (Ollama) | 54.4 | Slightly better recall; higher memory footprint |
| `text-embedding-3-small` | 1536 | Proprietary | No (OpenAI API) | 62.3 | Best MTEB; requires network and API key |
| `voyage-3-lite` | 512 | Proprietary | No (Voyage AI) | 58.4 | Strong factual recall; lowest dim cloud option |

`nomic-embed-text-v1.5` is the default because it is open-weight, runs offline via Ollama with a single `ollama pull nomic-embed-text` command, performs competitively on the MTEB retrieval category (which best maps to fact-recall workloads), and its Matryoshka structure allows operators to truncate to 256 dimensions for resource-constrained deployments without re-indexing — they simply change a config flag and sqlite-vec uses only the first 256 components.

Cloud opt-in is via `STIGMEM_EMBED_PROVIDER=openai|voyage` environment variable. When a cloud provider is selected, the embedding function calls the provider API; the vector schema does not change (dimensions differ and MUST be declared in node config at initialization; changing providers requires re-indexing).

**Cosine similarity vs. dot product:** Normalize all embeddings to unit length on insertion so that cosine similarity reduces to dot product. This enables sqlite-vec's native dot-product acceleration while preserving cosine semantics. The normalization MUST happen at indexing time, not at query time, to avoid per-query overhead. Implementations MUST document that raw stored vectors are L2-normalized.

### Dimensionality tradeoff

768 dimensions is the recommended default. The MTEB-calibrated recall lens notes that moving from 768 to 1536 dimensions yields +2–4 NDCG points on retrieval tasks but doubles the sqlite-vec index size and per-query ANN latency. For most single-node deployments with < 500k facts, 768 is the right tradeoff. Operators with > 1M facts and dedicated hardware should evaluate `mxbai-embed-large-v1` (1024-dim) for the marginal recall gain.

### Decay and contradiction interaction

**Decay:** When a fact's confidence drops below 0.1 (the decay sweeper's configurable `embed_tombstone_threshold`), its vector MUST be deleted from `vec_facts`. Stale low-confidence vectors silently pollute ANN results — this is the representation-freshness lens. Deletion is atomic with the decay sweep update. Re-embedding is not needed; if the fact is later restored (confidence raised), a fresh embedding is computed.

**Contradiction:** Both contradicting facts retain their embeddings. However, when a fact is part of an unresolved contradiction (per §3.3), its embedding score is multiplied by a `contradiction_penalty` (default: 0.7) in the fusion stage (§3 below). This does not modify the stored vector; the penalty is applied at ranking time using the `contradicted` flag from the facts table.

---

## 3. Hybrid Recall Ranking

### Decision

> How do lexical, dense vector, and graph traversal signals combine? How does the §19.4 source-trust multiplier compose? What salience signals beyond decay should the ranking consider, and how does the token-budget packing strategy avoid duplication?

### Pipeline Architecture

```
Query Q
│
├─ 1. Lexical stage (FTS5 / BM25)
│     SELECT ... FROM facts_fts WHERE facts_fts MATCH tokenize(Q)
│     → candidate set L with bm25_score
│
├─ 2. Dense stage (sqlite-vec ANN)
│     SELECT ... FROM vec_facts ORDER BY distance(embed(Q), vec) LIMIT k
│     → candidate set V with cosine_sim
│
├─ 3. Graph expansion (bounded BFS on entity_edges, depth ≤ 2)
│     seed = distinct entities in L ∪ V
│     expand to depth-2 neighbours; score by (1 / (1 + depth)) × edge.confidence
│     → candidate set G with graph_score
│
└─ 4. Fusion + ranking → scored, de-duplicated result set R
```

The three stages run independently and can be parallelized. Fusion happens after all three complete. This is a late-fusion architecture, which allows each retriever to specialize on its strength without interference.

### Fusion Formula

For each candidate fact `f` in `L ∪ V ∪ G`:

```
raw_score(f) = α · norm(bm25(f))
             + β · norm(cosine_sim(f))
             + γ · norm(graph_score(f))

salience(f)  = recency(f) · confidence_weight(f) · access_freq(f)
               · contradiction_weight(f) · garden_tier(f)

score(f)     = raw_score(f) · salience(f) · source_trust_multiplier(f.source_trust)
```

Where `norm(·)` is min-max normalization within the candidate set (separately for each retriever's output) so scores are in [0, 1] before interpolation.

**Default weights:** α = 0.30, β = 0.50, γ = 0.20.

These weights are a starting point. Per the benchmark-first validation lens, they MUST be tuned on a held-out probe set before the route is declared stable. A minimum viable eval set: 200 queries (entity-lookup × 50, relation-lookup × 50, open-ended × 50, adversarial × 50) with recall@10 and MRR as primary metrics. Implementation issue should include this as a delivery criterion.

**Weight rationale:**
- Dense retrieval (β = 0.5) dominates because embedding captures semantic paraphrase that exact-term BM25 misses entirely for natural-language queries.
- Lexical (α = 0.3) captures relation namespaces (`memory:role`, `roadmap:status`) that embedding collapses when they share surface vocabulary.
- Graph (γ = 0.2) provides soft relatedness from entity-to-entity links, improving recall for queries about entities only indirectly mentioned in the query string.

### Source-Trust Multiplier

Per §19.4.4, `effective_confidence = fact.confidence × t(fact.source)`. The ranking formula integrates this as:

```
source_trust_multiplier(t) = 0.5 + 0.5 × t    # maps [0.0, 1.0] → [0.5, 1.0]
```

The floor of 0.5 ensures that even minimally-trusted facts remain retrievable (they are not zeroed out), while a fully-trusted source scores 1.0. The `t(fact.source)` value SHOULD be fetched from the per-source trust cache (60s TTL per §19.4.4) not recomputed on each fact.

When `trust_mode = off` (§19.7.4), `source_trust_multiplier` is fixed at 1.0 for all facts.

### Salience Signals

| Signal | Formula | Range |
|---|---|---|
| **Recency** | `exp(-λ · age_days)` where λ = 0.01 (half-life ≈ 69 days) | (0, 1] |
| **Confidence weight** | `fact.confidence` (already in [0, 1]; acts as direct multiplier) | [0, 1] |
| **Access frequency** | `log(1 + access_count) / log(1 + max_access_count)` normalized within the candidate set | [0, 1] |
| **Contradiction weight** | 1.0 if no unresolved contradiction; 0.7 otherwise | {0.7, 1.0} |
| **Garden tier** | configurable float per garden (`garden_trust_weight`); default 1.0; quarantine garden default 0.2 | [0, 1] |

The `access_count` field is incremented on the fact row each time it appears in a recall result; this requires a lightweight write path. Implementations SHOULD batch these increments (e.g., flush every 30 seconds) to avoid write contention.

**Hub-bias guard:** When computing `graph_score` in step 3, apply degree normalization:

```
graph_score(f) = (1 / (1 + depth)) × edge.confidence / log(1 + out_degree(entity))
```

This penalizes highly-connected hub entities (e.g., the company root entity) that would otherwise dominate traversal results regardless of query relevance.

### Token-Budget Packing: MMR

Greedy by score is the wrong default. In a fact store, multiple facts about the same entity with the same relation are frequently near-duplicate (e.g., different timestamps of the same `memory:role = CTO` assertion). Greedy selection fills the token budget with redundant information.

**Maximal Marginal Relevance (MMR)** is the recommended packing strategy:

```
next = argmax_{f ∈ R \ selected} [
    λ_mmr · score(f)
    - (1 - λ_mmr) · max_{f_j ∈ selected} cos_sim(embed(f), embed(f_j))
]
```

With `λ_mmr = 0.7` (favors relevance; reduces to greedy at λ=1.0). This iteratively selects the highest-scoring candidate whose embedding is maximally different from what has already been selected. Tokens are counted after each selection; the loop terminates when the remaining budget cannot fit the next candidate.

The token counter MUST account for the rendering overhead per fact (field labels, punctuation, newlines) not just the raw value length. Recommended estimate: 40 tokens of fixed overhead per fact row plus `ceil(char_count / 4)` for the value text.

When `entity` is specified in the query (entity-centric recall), MMR is disabled — the caller wants all facts about that entity, sorted by score, up to the budget.

---

## 4. Memory Cards

### Decision

> What is a memory card's structure, how often is it refreshed, how does it stay coherent under contradictions, and when should recall return a card vs. raw facts?

### Structure

A **memory card** is a per-entity synthesized text summary stored as a `text`-type fact with:

```
entity:   <entity-uri>
relation: stigmem:memory:card
value:    { type: "text", v: <card_markdown> }
source:   "system:stigmem:card-generator"
scope:    <same scope as constituent facts>
confidence: 1.0   # confidence in the card's existence, not its content accuracy
```

The card `value` is structured Markdown with the following sections:

```markdown
## {entity_display_name}

**Type:** {entity_type}  **URI:** {entity_uri}  **Last refreshed:** {iso8601}

### Current facts ({n} live, {m} contradicted)

| Relation | Value | Confidence | Source | Since |
|----------|-------|------------|--------|-------|
| memory:role | CEO | 1.00 | agent/assistant | 2026-04-01 |
| roadmap:status | phase-9 | 0.85 | agent/cto | 2026-05-01 |
...

### Contradictions ({m} unresolved)

- **memory:role**: `CEO` (conf 1.00) ⟷ `CTO` (conf 0.80) — *unresolved*

### Sources

{n_sources} distinct sources; trust range [{min_t:.2f}, {max_t:.2f}]
```

**Content rules:**
- Include all live facts with `effective_confidence ≥ 0.3` (applying source-trust per §19.4.4).
- Sort rows by `(relation ASC, hlc DESC)` so the latest assertion for each relation appears first.
- Contradictions MUST be surfaced explicitly with both values and their confidences. The card MUST NOT silently pick a winner.
- Hard cap: 4000 tokens in the `value` field. If an entity has more facts than fit, include the highest-confidence facts and append a `… {n_omitted} lower-confidence facts omitted` note.
- Card facts with `garden_id` set are scoped to that garden; the card generator MUST NOT mix garden-scoped facts into a cross-garden card. One card per `(entity, scope, garden_id)` triple where `garden_id` may be null (ungardenned facts).

### Embedding

Each memory card is embedded as its full Markdown text and stored in `vec_facts` as a secondary vector for that entity, keyed as `"card:{entity_uri}:{scope}"`. This enables entity-level semantic search in the dense retrieval stage without retrieving all constituent fact rows.

### Refresh Policy

Cards are invalidated and queued for async refresh on three triggers:

| Trigger | Action |
|---|---|
| New fact asserted for entity | Invalidate card; enqueue background refresh |
| Decay sweep touches a constituent fact (confidence change) | Invalidate card; enqueue background refresh |
| Card age exceeds `STIGMEM_CARD_MAX_AGE_S` (default: 86400s / 24h) | Background job invalidates and refreshes |

During refresh, the **stale card remains readable** — the old card is served with a `card_stale: true` flag in the response. Callers that require fresh data can pass `force_refresh=true`, which blocks on synchronous card regeneration (bounded to 500ms; falls back to raw facts if exceeded).

The `stigmem:memory:card` relation is exempt from the decay sweeper — card facts MUST NOT have their confidence decayed by the TTL decay policy. They are invalidated only by the triggers above.

### Coherence under contradictions

The card does not resolve contradictions — it surfaces them with full detail. When a contradiction exists for a `(entity, relation, scope)` triple:

1. Both values appear in the Contradictions section.
2. The winning value (per §3.3 resolution order) appears in the Current facts table, marked `[CONTRADICTED]`.
3. The card's `contradicted_count` metadata field is non-zero, which surfaces in recall results as a signal to the consumer that the card's summary is partially unreliable.

Cards are regenerated after contradiction resolution: when `POST /v1/conflicts/:id/resolve` is called, the card for the entity is invalidated and queued for refresh.

### Recall fall-through: card vs. raw facts

`GET /v1/recall` (and the `recall` MCP tool) SHOULD return the memory card as the primary result for entity-centric queries, with raw facts as supplementary. Fall through to raw facts only:

| Condition | Behavior |
|---|---|
| `relation=` query param specified | Skip card; return raw facts for that relation |
| Card age > `max_card_age` AND `force_refresh=false` | Return stale card with `card_stale: true` + top-10 raw facts |
| Card has `contradicted_count > 0` AND caller passes `include_contradicted=true` | Return card + raw fact pairs for each contradiction |
| No card exists for entity + scope | Return raw facts; trigger async card generation |
| Card generation is in flight (lock held) | Return raw facts immediately |
| Query is not entity-centric (no `entity=` param) | Card lookup is skipped; run full hybrid pipeline on raw facts |

---

## 5. Stretch Topics

### 5.1 Higher-Order Embeddings (GNNs, Hypergraphs) — Defer to v2

Graph Neural Networks could capture multi-hop relational context that the current BFS expansion + cosine similarity pipeline misses — e.g., "which agent is most central to decisions in scope X" requires propagating node features across the graph, not just depth-limited traversal.

The feasibility blockers for v1: (a) GNN inference requires either a Python training pipeline or an ONNX model — neither fits the current pure-SQLite deployment model; (b) incremental GNN updating on a growing fact graph has O(N·k) re-embedding cost per new edge; (c) there is no eval set to measure the gain.

**Recommendation:** Defer GNN-based retrieval to v2. The entity-edge traversal in §1 + MMR packing in §3 approximates the multi-hop signal without training cost. Revisit when the eval set (§3) is established and can measure GNN recall uplift against a fixed baseline.

Hypergraphs (where an edge can span N entities, e.g., a reification triple per §2.3) are partially addressed by the existing reification pattern. The `entity_edges` table as specified handles binary relations only; n-ary edges require a separate `edge_members` join table. This is a natural v2 extension that does not change the core adjacency structure.

### 5.2 Neural-Symbolic Recall

The hybrid pipeline in §3 is already a partial neural-symbolic system: BM25 provides the symbolic predicate-matching layer; embeddings provide the neural semantic layer. A deeper integration — e.g., query rewriting that parses natural language into structured `(entity, relation)` predicates before retrieval — would improve precision for relational queries ("what is Alice's role?") that the current pipeline handles imprecisely (the embedding of "what is Alice's role?" is semantically close to many `memory:role` facts but not specifically pinned to entity `alice`).

**Recommendation:** Include a lightweight query parser in the `recall` MCP tool that attempts to extract `entity` and `relation` hints from the natural-language query string using regex against the known relation namespace registry. This is a symbolic pre-filter that narrows the dense retrieval search space. Full neural query understanding (e.g., fine-tuned NLI model) is a v2 concern.

### 5.3 Sheaf Theory for Federated Consistency

Sheaf-theoretic consistency is relevant to federation (§6 / §19) not directly to single-node recall. The intuition: when two federated nodes hold overlapping facts about the same entity, global consistency requires that their local views (sections) be compatible under the restriction maps of the sheaf. The `source_trust` scoring in §19.4 is a practical approximation: it downweights facts from peers whose manifests are unverified.

For Phase 9 (single-node recall), sheaf theory does not add actionable engineering decisions. It becomes relevant when designing the multi-instance recall merge in §6.7–§6.8 — specifically, which facts from peer nodes are included in a local recall result and how conflicts between local and remote facts are surfaced. Flag for the federation recall extension in v2.

---

## 6. References

1. **Nomic Embed v1.5** — Nussbaum et al. (2024). *Nomic Embed: Training a Reproducible Long Context Text Embedder*. arXiv:2402.01613. Establishes 768-dim Matryoshka embeddings with MTEB retrieval avg 53.9; the basis for the default model recommendation.

2. **MTEB Leaderboard** — Muennighoff et al. (2023). *MTEB: Massive Text Embedding Benchmark*. EACL 2023. The calibration framework for comparing embedding models on retrieval tasks; cited for model selection in §2.

3. **ColBERT v2** — Santhanam et al. (2022). *ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction*. NAACL 2022. Late-interaction model whose per-token scoring is the conceptual precedent for the per-fact scoring in the fusion formula (§3); not recommended for direct adoption given SQLite constraint, but cited for the interpolation weight rationale.

4. **GraphRAG** — Edge et al. (2024). *From Local to Global: A Graph RAG Approach to Query-Focused Summarization*. Microsoft Research. The graph-expansion stage (§3, step 3) is directly inspired by GraphRAG's community summary approach; the depth-2 BFS + hub-normalised scoring addresses the hub-bias problem identified in GraphRAG evaluations.

5. **MMR for diversity** — Carbonell & Goldstein (1998). *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*. SIGIR 1998. Classic citation for the MMR formula in §3; the λ=0.7 default is derived from their empirical findings on summary quality vs. relevance tradeoff.

---

*This memo informs spec §20 and implementation subtasks for Phase 9. No code changes; written deliverable only. Next action: CTO review and sign-off as substrate for §20.*
