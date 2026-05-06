---
title: Recall
sidebar_label: Recall
description: When to use recall vs query_facts, how token-budget packing works, and how to tune stage weights.
audience: Integrator
---

# Recall

**Audience:** Agent developers building on top of a Stigmem node.
**Spec reference:** §20.3 Recall API.

---

The `recall` endpoint answers the question: *"What do I most need to know right now?"* It scans the fact store with a hybrid three-stage pipeline (lexical + dense + graph), scores candidates by relevance to your query, and packs as many facts as possible within a token budget — returning a coherent, size-bounded context slice rather than an unbounded list.

## `recall` vs `query_facts`

| | `POST /v1/recall` | `GET /v1/facts` |
|---|---|---|
| **Use when** | Query is open-ended or semantic ("what do I know about project X?") | You know the exact entity, relation, or predicate |
| **Input** | Natural-language or keyword query string | Structured filters (entity, relation, scope, date range) |
| **Output** | Scored, token-budget-bounded, MMR-packed slice | Paginated full list matching filters |
| **Graph expansion** | Yes — optional depth-1 or depth-2 hop | No |
| **Memory card** | Included when `entity` param is set | Not included |
| **Score signal** | BM25 + cosine similarity + graph proximity | N/A |
| **Token control** | `token_budget` parameter | `limit` / pagination |

**Use `query_facts` when you need a complete list of facts for a specific predicate** — for example, fetching all `memory:tag` values for a project before running a report. Use `recall` when you need the most relevant slice of memory to include in an agent's context window.

---

## How the pipeline works

### Stage 1 — Lexical (BM25/FTS5)

The query string is matched against a full-text index of `entity + relation + value` fields using SQLite FTS5 / BM25 scoring. This stage is fast and catches exact-keyword or near-exact matches. Weight: `lexical` (default 0.30).

### Stage 2 — Dense vector (ANN)

The query string is embedded with the same model used at write time (default: `nomic-embed-text-v1.5`) and compared to the `vec_facts` index via approximate nearest-neighbour search (sqlite-vec). This stage catches semantic matches that lexical search misses. Weight: `vector` (default 0.50). Requires `STIGMEM_EMBED_ENABLED=true`.

### Stage 3 — Graph expansion

Seed facts from stages 1–2 are expanded by traversing the `entity_edges` adjacency index. Related entities are pulled in even if they didn't score on the query directly. Controlled by `depth` (1 or 2) and `weights.graph` (default 0.20). Set `depth=0` to skip graph expansion entirely.

### MMR packing

After scoring, candidates are packed into the response using Maximal Marginal Relevance (MMR). MMR alternates between relevance and diversity: each slot picks the next candidate that is both highly relevant and dissimilar to what is already packed. This prevents five near-duplicate facts about the same entity consuming the whole budget.

Tune with `lambda_mmr`:
- `lambda_mmr=1.0` — pure greedy relevance (highest scores first, no diversity penalty).
- `lambda_mmr=0.5` — balanced (equal weight on relevance and diversity).
- `lambda_mmr=0.0` — pure diversity (avoids all similarity to already-packed items, regardless of score).

Default is `0.7` — biased toward relevance with moderate diversity.

---

## Token budget

The `token_budget` parameter limits the total size of the packed response. The node counts estimated tokens across `entity`, `relation`, and `value` fields for each candidate fact. Field labels and metadata (`id`, `score`, `source_trust`, etc.) are excluded from the count.

When the budget is exhausted the response includes `"truncated": true`. The count of tokens actually used is returned as `token_budget_used`. Facts are always added in MMR order — the highest-priority items appear first in the `results` array even when the response is truncated.

**Setting a budget.** A typical LLM context window for agent tool responses is 4 000–8 000 tokens. Leave headroom for the agent's instructions and the conversation history. A starting value of `2000`–`4000` works for most agent tasks.

:::tip Check truncated
If your agent is missing relevant facts, check `truncated` first. If it is `true`, either raise `token_budget` or narrow the query to a specific entity.
:::

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | — | Natural-language or structured query |
| `token_budget` | integer | Yes | — | Max response tokens (field labels excluded) |
| `depth` | integer | No | 1 | Graph expansion hops; 0 disables graph stage |
| `weights` | object | No | `{lexical:0.30, vector:0.50, graph:0.20}` | Stage weights; must sum to 1.0 ±0.001 |
| `entity` | string | No | — | Entity URI; triggers entity-centric (card-first) recall |
| `relation` | string | No | — | Relation filter; skips memory card lookup |
| `scope` | string | No | global | Garden or global scope |
| `lambda_mmr` | float | No | 0.7 | MMR diversity tradeoff (0–1) |
| `min_confidence` | float | No | 0.1 | Minimum effective confidence for inclusion |
| `force_refresh` | boolean | No | false | Block on synchronous memory card refresh |
| `include_contradicted` | boolean | No | false | Include facts with unresolved contradictions |

---

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

When `entity` is set, the response includes a `memory_card` block — a pre-synthesized entity summary — before the ranked fact list. Use this when the agent is reasoning about a specific entity.

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

---

## Weight tuning

The three stage weights control how much each signal contributes to a fact's final score. Adjust when the defaults produce poor results for your use case.

| Scenario | Recommended weights |
|---|---|
| Exact-keyword queries ("what is task X?") | `{lexical: 0.60, vector: 0.20, graph: 0.20}` |
| Semantic / conceptual queries ("what do I know about auth?") | `{lexical: 0.10, vector: 0.70, graph: 0.20}` |
| Graph-heavy: exploring entity relationships | `{lexical: 0.20, vector: 0.30, graph: 0.50}` |
| Embeddings disabled (`STIGMEM_EMBED_ENABLED=false`) | `{lexical: 0.70, vector: 0.00, graph: 0.30}` |

When embeddings are disabled the vector stage is skipped and its weight redistributed proportionally at recall time — but passing explicit weights that sum to 1.0 without a `vector` component is cleaner.

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

---

## Memory cards and recall fast-path (§20.4)

Memory cards are per-entity, per-scope pre-aggregated summaries stored in the `memory_cards` table. They accelerate recall by short-circuiting raw-fact re-ranking for entities that have a fresh, reliable card.

**Stale-on-write.** Every `POST /v1/facts` call marks the affected entity's card stale immediately after the fact is persisted. This is a non-blocking background operation that never delays the write path.

**Refresh-on-read (fast-path).** During `POST /v1/recall`, the node calls `get_fresh_card` for each candidate entity. When a card passes all three conditions — `is_stale = false`, `has_contradictions = false`, and `avg_confidence ≥ 0.5` — the entity's raw facts are replaced in the scoring pipeline by a single synthetic `ScoredFact` carrying the card summary as its value. This fact appears in the response with `from_card: true` and the relation `stigmem:card:summary`.

**Divergence policy.** When any condition is false (including a transient refresh error), the entity falls through to full raw-fact re-ranking. The fallback is transparent to callers: the only signal is the absence of `from_card: true` on those facts. This policy ensures that entities with unresolved contradictions or outdated confidence scores never have their raw evidence hidden behind a potentially unreliable summary.

**Fetching or forcing a card refresh.** Use `GET /v1/cards/{entity_uri}` to inspect a card directly or force a server-side refresh with `?refresh=true`. See the [Memory Cards guide](./memory-cards.md) for the full lifecycle, schema, and Python SDK usage.

---

## Security and access control

- All recall results are filtered by the caller's garden ACL (§17) at query time — callers never see facts from gardens they don't have read access to.
- The content sanitizer (§19.7) strips known prompt-injection sentinels and bidirectional-override characters from `value` fields before they appear in the response.
- `source_trust` on each result reflects the identity strength of the writing agent (§19). Effective confidence = `confidence × source_trust`. Facts below `min_confidence` are excluded.

---

## Related guides

- [Querying facts](/docs/build/guides/querying-facts) — structured, predicate-based fact queries
- [Embeddings](/docs/build/guides/embeddings) — model selection, reindexing, and mixed-model safety
- [Memory Gardens](/docs/build/guides/memory-gardens) — garden ACL and recall scoping
- [Subscriptions](/docs/build/guides/subscriptions) — push notifications when watched facts change
