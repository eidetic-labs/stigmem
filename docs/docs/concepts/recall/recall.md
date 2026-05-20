---
title: Recall
sidebar_label: Recall
description: When to use recall vs query_facts, how token-budget packing works, and how to tune stage weights.
audience: Integrator
---

# Recall

<p className="stigmem-meta"><span>5 min read</span><span>Agent developer</span><span>Spec-07-Recall-Pipeline + Spec-X11-Recall-Graph</span></p>

<div className="stigmem-lead">

**What this page is**

The `recall` endpoint answers: *"What do I most need to know right
now?"* It scans the fact store with a hybrid three-stage pipeline
(lexical + dense + graph), scores candidates by relevance, and packs
as many facts as possible within a token budget — returning a
coherent, size-bounded context slice rather than an unbounded list.

</div>

## `recall` vs `query_facts`

<div className="stigmem-fields">

<div>
<dt>Aspect</dt>
<dt><span className="stigmem-fields__type"><code>POST /v1/recall</code></span></dt>
<dd><code>GET /v1/facts</code></dd>
</div>

<div>
<dt>Use when</dt>
<dt><span className="stigmem-fields__type">open-ended or semantic</span></dt>
<dd>"What do I know about project X?" vs. you know the exact entity, relation, or predicate.</dd>
</div>

<div>
<dt>Input</dt>
<dt><span className="stigmem-fields__type">natural-language query</span></dt>
<dd>Structured filters (entity, relation, scope, date range).</dd>
</div>

<div>
<dt>Output</dt>
<dt><span className="stigmem-fields__type">scored, MMR-packed slice</span></dt>
<dd>Paginated full list matching filters.</dd>
</div>

<div>
<dt>Graph expansion</dt>
<dt><span className="stigmem-fields__type">yes — depth 1 or 2</span></dt>
<dd>No.</dd>
</div>

<div>
<dt>Memory card</dt>
<dt><span className="stigmem-fields__type">included with <code>entity</code> param</span></dt>
<dd>Not included.</dd>
</div>

<div>
<dt>Score signal</dt>
<dt><span className="stigmem-fields__type">BM25 + cosine + graph proximity</span></dt>
<dd>N/A.</dd>
</div>

<div>
<dt>Token control</dt>
<dt><span className="stigmem-fields__type"><code>token_budget</code></span></dt>
<dd><code>limit</code> / pagination.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Use `query_facts` when you need a complete list for a specific predicate.**

For example, fetching all <code>memory:tag</code> values for a project
before running a report. Use <code>recall</code> when you need the
most relevant slice of memory to include in an agent's context
window.

</div>

## How the pipeline works

### Stage 1 · Lexical (BM25/FTS5)

The query string is matched against a full-text index of
`entity + relation + value` fields using SQLite FTS5 / BM25 scoring.
Fast; catches exact-keyword or near-exact matches. Weight: `lexical`
(default 0.30).

### Stage 2 · Dense vector (ANN)

The query string is embedded with the same model used at write time
(default: `nomic-embed-text-v1.5`) and compared to the `vec_facts`
index via approximate nearest-neighbour search (sqlite-vec). Catches
semantic matches that lexical search misses. Weight: `vector`
(default 0.50). Requires `STIGMEM_EMBED_ENABLED=true`.

### Stage 3 · Graph expansion

Seed facts from stages 1–2 are expanded by traversing the
`entity_edges` adjacency index. Related entities are pulled in even
if they didn't score on the query directly. Controlled by `depth` (1
or 2) and `weights.graph` (default 0.20). Set `depth=0` to skip
graph expansion entirely.

### MMR packing

After scoring, candidates are packed into the response using Maximal
Marginal Relevance (MMR). MMR alternates between relevance and
diversity: each slot picks the next candidate that is both highly
relevant and dissimilar to what is already packed. **This prevents
five near-duplicate facts about the same entity from consuming the
whole budget.**

<div className="stigmem-fields">

<div>
<dt><code>lambda_mmr</code></dt>
<dt><span className="stigmem-fields__type">Tradeoff</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>1.0</code></dt>
<dt><span className="stigmem-fields__type">pure relevance</span></dt>
<dd>Highest scores first, no diversity penalty.</dd>
</div>

<div>
<dt><code>0.5</code></dt>
<dt><span className="stigmem-fields__type">balanced</span></dt>
<dd>Equal weight on relevance and diversity.</dd>
</div>

<div>
<dt><code>0.0</code></dt>
<dt><span className="stigmem-fields__type">pure diversity</span></dt>
<dd>Avoids all similarity to already-packed items, regardless of score.</dd>
</div>

<div>
<dt><code>0.7</code> (default)</dt>
<dt><span className="stigmem-fields__type">relevance-biased</span></dt>
<dd>Moderate diversity.</dd>
</div>

</div>

## Token budget

The `token_budget` parameter limits the total size of the packed
response. The node counts estimated tokens across `entity`,
`relation`, and `value` fields for each candidate fact. Field labels
and metadata (`id`, `score`, `source_trust`, etc.) are excluded from
the count.

When the budget is exhausted the response includes
`"truncated": true`. The count of tokens actually used is returned
as `token_budget_used`. Facts are always added in MMR order — the
highest-priority items appear first in the `results` array even when
the response is truncated.

<div className="stigmem-keypoint">

**Setting a budget.**

A typical LLM context window for agent tool responses is 4,000–8,000
tokens. Leave headroom for the agent's instructions and the
conversation history. A starting value of <code>2000</code>–
<code>4000</code> works for most agent tasks.

</div>

:::tip Check truncated
If your agent is missing relevant facts, check `truncated` first. If
it is `true`, either raise `token_budget` or narrow the query to a
specific entity.
:::

## Parameters

<div className="stigmem-fields">

<div>
<dt>Parameter</dt>
<dt><span className="stigmem-fields__type">Type · Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>query</code></dt>
<dt><span className="stigmem-fields__type">string · required</span></dt>
<dd>Natural-language or structured query.</dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">integer · required</span></dt>
<dd>Max response tokens (field labels excluded).</dd>
</div>

<div>
<dt><code>depth</code></dt>
<dt><span className="stigmem-fields__type">integer · 1</span></dt>
<dd>Graph expansion hops; 0 disables graph stage.</dd>
</div>

<div>
<dt><code>weights</code></dt>
<dt><span className="stigmem-fields__type">object · <code>{`{lexical:0.30, vector:0.50, graph:0.20}`}</code></span></dt>
<dd>Stage weights; must sum to 1.0 ±0.001.</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Entity URI; triggers entity-centric (card-first) recall.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Relation filter; skips memory card lookup.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">string · global</span></dt>
<dd>Garden or global scope.</dd>
</div>

<div>
<dt><code>lambda_mmr</code></dt>
<dt><span className="stigmem-fields__type">float · 0.7</span></dt>
<dd>MMR diversity tradeoff (0–1).</dd>
</div>

<div>
<dt><code>min_confidence</code></dt>
<dt><span className="stigmem-fields__type">float · 0.1</span></dt>
<dd>Minimum effective confidence for inclusion.</dd>
</div>

<div>
<dt><code>force_refresh</code></dt>
<dt><span className="stigmem-fields__type">bool · false</span></dt>
<dd>Block on synchronous memory card refresh.</dd>
</div>

<div>
<dt><code>include_contradicted</code></dt>
<dt><span className="stigmem-fields__type">bool · false</span></dt>
<dd>Include facts with unresolved contradictions.</dd>
</div>

<div>
<dt><code>legacy_format</code></dt>
<dt><span className="stigmem-fields__type">query bool · false</span></dt>
<dd>Temporary one-minor-version compatibility switch. Omits <code>content</code> and <code>instructions</code> while preserving the legacy <code>facts</code> array.</dd>
</div>

</div>

## Response channels

By default, recall returns the legacy `facts` array plus
channel-separated `content` and `instructions` arrays. New adapters
should consume `content` and `instructions` separately and treat
recalled content as untrusted data. Older clients can call
`POST /v1/recall?legacy_format=true` during the compatibility window
to receive the pre-channel response shape.

## Examples

### Open-ended semantic query

```bash
curl -s -X POST http://localhost:8765/v1/recall \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "what is the current project status?",
    "token_budget": 2000
  }'
```

### Entity-centric query (memory card first)

When `entity` is set, the response includes a `memory_card` block —
a pre-synthesized entity summary — before the ranked fact list. Use
this when the agent is reasoning about a specific entity.

```bash
curl -s -X POST http://localhost:8765/v1/recall \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "deployment history",
    "entity": "stigmem://company.example/project/api-service",
    "token_budget": 3000,
    "depth": 2
  }'
```

### Python SDK

```python
from stigmem import StigmemClient

client = StigmemClient(base_url="http://localhost:8765", api_key="<api-key>")

result = client.recall(
    query="what are the current blockers on phase 9?",
    token_budget=2000,
    depth=1,
)

for fact in result.results:
    print(f"{fact.entity}  {fact.relation}  {fact.value}  (score={fact.score:.3f})")

if result.truncated:
    print(f"Warning: response truncated at {result.token_budget_used} tokens")
```

## Weight tuning

The three stage weights control how much each signal contributes to
a fact's final score. Adjust when the defaults produce poor results.

<div className="stigmem-fields">

<div>
<dt>Scenario</dt>
<dt><span className="stigmem-fields__type">Recommended weights</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Exact-keyword queries</dt>
<dt><span className="stigmem-fields__type"><code>{`{lexical: 0.60, vector: 0.20, graph: 0.20}`}</code></span></dt>
<dd>"What is task X?"</dd>
</div>

<div>
<dt>Semantic / conceptual queries</dt>
<dt><span className="stigmem-fields__type"><code>{`{lexical: 0.10, vector: 0.70, graph: 0.20}`}</code></span></dt>
<dd>"What do I know about auth?"</dd>
</div>

<div>
<dt>Graph-heavy: exploring relationships</dt>
<dt><span className="stigmem-fields__type"><code>{`{lexical: 0.20, vector: 0.30, graph: 0.50}`}</code></span></dt>
<dd>Entity-centric exploration.</dd>
</div>

<div>
<dt>Embeddings disabled</dt>
<dt><span className="stigmem-fields__type"><code>{`{lexical: 0.70, vector: 0.00, graph: 0.30}`}</code></span></dt>
<dd><code>STIGMEM_EMBED_ENABLED=false</code>.</dd>
</div>

</div>

When embeddings are disabled the vector stage is skipped and its
weight redistributed proportionally at recall time — but passing
explicit weights that sum to 1.0 without a `vector` component is
cleaner.

```bash
curl -s -X POST http://localhost:8765/v1/recall \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "production incident 2026-04-15",
    "token_budget": 3000,
    "weights": {"lexical": 0.60, "vector": 0.20, "graph": 0.20}
  }'
```

## Memory cards and recall fast-path

Memory cards are per-entity, per-scope pre-aggregated summaries
stored in the `memory_cards` table. They accelerate recall by
short-circuiting raw-fact re-ranking for entities that have a fresh,
reliable card.

<div className="stigmem-grid">

<div><h4>Stale-on-write</h4><p>Every <code>POST /v1/facts</code> call marks the affected entity's card stale immediately after the fact is persisted. Non-blocking background operation that never delays the write path.</p></div>
<div><h4>Refresh-on-read (fast-path)</h4><p>During recall, the node calls <code>get_fresh_card</code> for each candidate entity. When a card passes all three conditions — <code>is_stale = false</code>, <code>has_contradictions = false</code>, and <code>avg_confidence ≥ 0.5</code> — the entity's raw facts are replaced by a single synthetic <code>ScoredFact</code> carrying the card summary. This fact appears with <code>from_card: true</code> and the relation <code>stigmem:card:summary</code>.</p></div>
<div><h4>Divergence policy</h4><p>When any condition is false (including a transient refresh error), the entity falls through to full raw-fact re-ranking. The fallback is transparent to callers: the only signal is the absence of <code>from_card: true</code> on those facts.</p></div>

</div>

**Fetching or forcing a card refresh.** Use
`GET /v1/cards/{entity_uri}` to inspect a card directly or force a
server-side refresh with `?refresh=true`. See the
[Memory Cards guide](https://github.com/eidetic-labs/stigmem/tree/main/experimental/recall-graph)
for the full lifecycle.

## Security and access control

<div className="stigmem-grid">

<div><h4>Garden ACL filtering</h4><p>All recall results are filtered by the caller's garden ACL (Spec-02) at query time — callers never see facts from gardens they don't have read access to.</p></div>
<div><h4>Content sanitizer</h4><p>The recall-time sanitizer (ADR-003) strips known prompt-injection sentinels and bidirectional-override characters from <code>value</code> fields.</p></div>
<div><h4>Source-trust multiplication</h4><p><code>source_trust</code> on each result reflects the identity strength of the writing agent. Effective confidence = <code>confidence × source_trust</code>. Facts below <code>min_confidence</code> are excluded.</p></div>

</div>

## Related guides

<div className="stigmem-next">

<a href="../facts/querying-facts">
<strong>Concepts</strong>
<span>Querying facts</span>
<small>Structured, predicate-based fact queries.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/recall-graph">
<strong>Experimental</strong>
<span>Embeddings</span>
<small>Model selection, reindexing, and mixed-model safety.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/memory-garden-acl">
<strong>Experimental</strong>
<span>Memory Gardens</span>
<small>Garden ACL and recall scoping.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/subscriptions">
<strong>Experimental</strong>
<span>Subscriptions</span>
<small>Push notifications when watched facts change.</small>
</a>

</div>
