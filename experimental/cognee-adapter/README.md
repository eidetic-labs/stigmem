# stigmem-plugin-cognee-adapter

Bridges [Stigmem](https://github.com/eidetic-labs/stigmem) with
[topoteretes/Cognee](https://github.com/topoteretes/cognee) — a knowledge-graph
/ memory layer that ingests documents and conversations, extracts entities and
relationships via LLM, and exposes them as a queryable graph.

This package is experimental and opt-in. Installing it makes the
`cognee-adapter` plugin discoverable through the `stigmem.plugins` entry-point
group; host applications still choose when to call the adapter.

## Federation model

stigmem holds **structured atomic facts** across agents: typed key-value
triples `(entity, relation, value)` with provenance and scope.  Cognee builds a
**rich relational knowledge graph** from unstructured input, making facts
accessible via semantic search and graph traversal.

The two stores complement each other:

| Layer | Strength | Query style |
|---|---|---|
| stigmem | Exact, typed, auditable facts | Structured filter (entity/relation/scope) |
| Cognee | Contextual relationships, semantic similarity | Natural-language graph search |

This adapter exposes two seams:

1. **`assert_to_cognee(fact, dataset)`** — when stigmem asserts a fact, push it
   into Cognee as structured text.  Cognee cognifies the text into a typed
   graph node/edge, making the relationship discoverable through semantic
   queries that cross fact boundaries.

2. **`query_from_cognee(scope, query)`** — run a Cognee semantic search and
   return results as stigmem-compatible fact-shaped records, ready to merge or
   display alongside native stigmem facts.

## Design

The adapter is intentionally thin:

- It serialises each fact to a structured text string (`entity:X | relation:Y | value:V | …`)
  that Cognee can parse back into graph triples.
- It applies Cognee config (`set_llm_config`, `set_vector_db_config`) lazily
  from environment variables on first use — no global side effects at import
  time.
- Synchronous wrappers (`assert_to_cognee`, `query_from_cognee`) call
  `asyncio.run()` so callers without an event loop can use the adapter
  directly.  The `_async` variants are available for callers that already run
  an event loop.
- `batch_assert_to_cognee` defers `cognify` until after all facts are staged —
  preferred for bulk ingestion because each `cognify` call invokes the LLM
  extraction pipeline.

## Files

| File | Purpose |
|---|---|
| `src/stigmem_plugin_cognee/adapter.py` | Bridge adapter — serialisation, Cognee calls, normalisation |
| `src/stigmem_plugin_cognee/manifest.py` | Stigmem plugin discovery manifest |
| `demo.py` | Runnable end-to-end demo (assert facts → push to Cognee → query) |
| `tests/conftest.py` | pytest path setup |
| `tests/test_cognee_adapter.py` | Unit tests (cognee mocked; no live deps required) |

## Installation

```bash
python -m pip install 'stigmem-plugin-cognee-adapter>=0.1.0,<2.0.0'
```

### Requirements

- Python ≥ 3.11
- `stigmem-py`: `pip install stigmem-py` (or from workspace)
- `cognee`: `pip install cognee`
- An LLM backend accessible by Cognee (default: OpenAI — set `OPENAI_API_KEY`
  or use `COGNEE_LLM_PROVIDER` + `COGNEE_LLM_API_KEY` for other providers)

### Environment variables

```bash
# stigmem node
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key            # optional
STIGMEM_SOURCE_ENTITY=agent:my-agent  # entity URI for assertions

# Cognee — adapter config
COGNEE_STIGMEM_DATASET=stigmem         # dataset name (default: stigmem)

# Cognee — LLM backend (applied lazily on first assert/query)
COGNEE_LLM_PROVIDER=openai
COGNEE_LLM_MODEL=gpt-4o-mini
COGNEE_LLM_API_KEY=sk-your-openai-key  # or set OPENAI_API_KEY directly

# Cognee — vector DB (default: local LanceDB)
COGNEE_VECTOR_DB_PROVIDER=lancedb
COGNEE_VECTOR_DB_PATH=.cognee_db
```

## Usage

### Push a single fact into Cognee

```python
from stigmem_plugin_cognee.adapter import StigmemCogneeAdapter

bridge = StigmemCogneeAdapter.from_env()

# fact dict mirrors FactRecord.model_dump()
fact = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "engineer"},
    "source": "agent:my-agent",
    "scope": "company",
    "confidence": 1.0,
}

bridge.assert_to_cognee(fact, dataset="stigmem")
```

### Batch insert (preferred for multiple facts)

```python
bridge.batch_assert_to_cognee(list_of_fact_dicts, dataset="stigmem")
# cognify is called once after all facts are staged
```

### Query the Cognee graph

```python
results = bridge.query_from_cognee(
    scope="company",
    query="What role does alice have?",
)
for rec in results:
    print(rec["entity"], rec["relation"], rec["value"])
```

### Async usage

```python
import asyncio

async def main() -> None:
    bridge = StigmemCogneeAdapter.from_env()
    await bridge.assert_to_cognee_async(fact, dataset="stigmem")
    results = await bridge.query_from_cognee_async("company", "Who owns project:loom?")
    print(results)

asyncio.run(main())
```

### End-to-end demo

```bash
cd stigmem/experimental/cognee-adapter
STIGMEM_URL=http://localhost:8765 \
  COGNEE_LLM_PROVIDER=openai \
  COGNEE_LLM_MODEL=gpt-4o-mini \
  COGNEE_LLM_API_KEY=sk-... \
  python demo.py
```

The demo asserts six related facts about the Loom project into stigmem, pushes
them into Cognee's graph, then queries the graph with natural-language questions
to verify the relationships are discoverable.

## Enable

The adapter has no node-global behavior gate at v0.1.0. Enable it in the host
application by installing the package and importing
`stigmem_plugin_cognee.adapter.StigmemCogneeAdapter`.

```bash
python -m pip install 'stigmem-plugin-cognee-adapter>=0.1.0,<2.0.0'
stigmem plugins list
```

## Disable

Remove the adapter from the host application path and restart the process that
loads plugins. If it was installed only for this integration, uninstall it:

```bash
python -m pip uninstall stigmem-plugin-cognee-adapter
```

## Test

```bash
cd experimental/cognee-adapter
python -m pytest tests/ -v
```

No live stigmem node, Cognee instance, or LLM API key required — the `cognee`
module is fully mocked in the test suite.

## Uninstall

```bash
python -m pip uninstall stigmem-plugin-cognee-adapter
```

## Search types

Cognee exposes several search variants.  Pass `search_type` to
`query_from_cognee`:

| Value | Cognee SearchType | Returns |
|---|---|---|
| `"INSIGHTS"` (default) | `SearchType.INSIGHTS` | Graph triples matching the query |
| `"GRAPH_COMPLETION"` | `SearchType.GRAPH_COMPLETION` | LLM-composed answer from graph traversal |
| `"CHUNKS"` | `SearchType.CHUNKS` | Raw ingested text chunks |
| `"SUMMARIES"` | `SearchType.SUMMARIES` | Text summaries |

`INSIGHTS` is recommended for structured fact retrieval; `GRAPH_COMPLETION` for
narrative answers that synthesise across multiple facts.

## Invariants

- **Idempotency**: re-asserting the same fact text is safe — Cognee deduplicates
  at the graph level.  stigmem facts are immutable; each new assert gets a new
  `id`, so re-pushing the same logical fact creates a duplicate graph node.
  Applications that need update semantics should query stigmem for the latest
  fact before pushing.
- **Blast radius**: Cognee is a secondary enrichment layer.  Failures in
  `assert_to_cognee` or `query_from_cognee` do not affect stigmem availability;
  callers should catch exceptions and degrade gracefully.
- **Partition behaviour**: if Cognee is unavailable, stigmem continues to serve
  exact facts.  The adapter does not retry internally — callers own the retry /
  circuit-breaker policy.
