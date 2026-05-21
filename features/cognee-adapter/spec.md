# Cognee Adapter Spec

## Scope

The Cognee adapter connects Stigmem facts to Cognee graph ingestion and search.
It does not define Cognee behavior, Stigmem node API semantics, or the stable
adapter packaging contract.

This feature covers:

- the `stigmem-cognee-adapter` source package under
  `experimental/cognee-adapter`;
- serialization of Stigmem fact dictionaries into structured text for Cognee
  ingestion;
- single-fact and batch assertion into Cognee datasets;
- semantic search against Cognee with normalized Stigmem-shaped results;
- lazy Cognee LLM and vector database configuration from environment
  variables;
- synchronous wrappers for script/tool callers and asynchronous methods for
  event-loop callers.

## Adapter Contract

| Surface | Behavior |
| --- | --- |
| `assert_to_cognee(fact, dataset)` | Serializes one fact and stages it with `cognee.add`, then runs `cognee.cognify` for the target dataset. |
| `batch_assert_to_cognee(facts, dataset)` | Stages multiple serialized facts and runs one `cognee.cognify` call for bulk ingestion. |
| `query_from_cognee(scope, query, search_type)` | Runs Cognee search and returns Stigmem-compatible fact-shaped dictionaries. |
| Async variants | Provide the same behavior for callers already running an event loop. |

## Configuration

| Setting | Purpose |
| --- | --- |
| `COGNEE_STIGMEM_DATASET` | Default Cognee dataset name, defaulting to `stigmem`. |
| `COGNEE_LLM_PROVIDER` | Optional Cognee LLM provider. |
| `COGNEE_LLM_MODEL` | Optional Cognee LLM model. |
| `COGNEE_LLM_API_KEY` | Optional provider API key passed to Cognee. |
| `COGNEE_VECTOR_DB_PROVIDER` | Cognee vector database provider, defaulting to `lancedb`. |
| `COGNEE_VECTOR_DB_PATH` | Local vector database path, defaulting to `.cognee_db`. |

## Result Shape

Cognee results are normalized into fact-like dictionaries with `entity`,
`relation`, `value`, `source`, `scope`, `confidence`, and related Stigmem
fields. Opaque Cognee results fall back to `relation=cognee:result` with the
raw text in a text value.

## Non-Goals

- Shipping the adapter in the current alpha artifact set.
- Defining a stable Cognee package or plugin compatibility promise.
- Making Cognee required for Stigmem node availability.
- Retrying or circuit-breaking Cognee outages inside the adapter.
- Defining new Stigmem protocol semantics.

## Canonical Spec Assignment

There is no Spec-X assignment for the Cognee adapter. It is an external adapter
around existing Stigmem fact and query behavior, not a standalone Stigmem
protocol module.
