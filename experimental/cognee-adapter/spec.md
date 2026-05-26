# Cognee Adapter Spec

## Purpose

`stigmem-plugin-cognee-adapter` bridges Stigmem's exact, typed fact model with
Cognee's memory-graph ingestion and semantic search surface. It lets a host
application push selected Stigmem facts into Cognee and read Cognee search
results back as Stigmem-shaped records.

The adapter is intentionally a bridge package, not a node-wide behavior plugin.
Installing it makes the `cognee-adapter` manifest discoverable. Runtime calls
remain explicit through `StigmemCogneeAdapter`.

## Fact-Mapping Semantics

Stigmem facts are serialized into structured text:

```text
entity:<entity> | relation:<relation> | value:<value> | source:<source> | scope:<scope> | confidence:<confidence>
```

The adapter includes `valid_until` and `stigmem_id` when present. Cognee ingests
that text through `cognee.add()` and runs extraction through `cognee.cognify()`.

Cognee results are normalized into Stigmem-compatible dictionaries. Structured
results round-trip the original `entity`, `relation`, `value`, `source`,
`scope`, `confidence`, and `id` fields. Opaque results are returned with
`relation="cognee:result"` and a text value.

## Scope Model

The adapter preserves the fact scope field in the serialized text and in parsed
round trips. It does not enforce Stigmem ACLs inside Cognee. Operators must
choose datasets, Cognee stores, and host-application call sites that match their
scope and retention model.

## Configuration Surface

The adapter reads these environment variables when built through
`StigmemCogneeAdapter.from_env()` or when Cognee configuration is applied:

| Variable | Purpose |
| --- | --- |
| `COGNEE_STIGMEM_DATASET` | Default Cognee dataset name. |
| `COGNEE_LLM_PROVIDER` | Cognee LLM provider name. |
| `COGNEE_LLM_MODEL` | Cognee model name. |
| `COGNEE_LLM_API_KEY` | API key passed to Cognee LLM config. |
| `COGNEE_VECTOR_DB_PROVIDER` | Cognee vector database provider. |
| `COGNEE_VECTOR_DB_PATH` | Cognee vector database path. |

## API

`StigmemCogneeAdapter.from_env()` constructs an adapter from environment.

`assert_to_cognee(fact, dataset=None)` serializes one Stigmem fact and pushes it
to Cognee, then runs `cognify` for the dataset.

`batch_assert_to_cognee(facts, dataset=None)` stages multiple facts and runs a
single `cognify` call.

`query_from_cognee(scope, query, search_type="INSIGHTS")` runs a Cognee search
and returns normalized Stigmem-shaped records.

Async variants are available for host applications that already run an event
loop.

## Failure Modes

- Missing `cognee` dependency raises `ImportError` with an install hint when a
  Cognee operation is attempted.
- Cognee or LLM outages propagate to the caller; the adapter does not retry.
- Unparseable Cognee results are preserved as text-valued fallback records.
- Operators must treat Cognee as a secondary enrichment system, not the source
  of Stigmem authorization decisions.
