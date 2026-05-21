# Recall Graph Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/recall-graph/spec.md` | Legacy compatibility pointer used by the generated protocol index. |
| `node/src/stigmem_node/vector_search.py` | Vector search and embedding storage helpers. |
| `node/src/stigmem_node/embedding/` | Embedding model adapters and composition helpers. |
| `node/src/stigmem_node/card_materializer.py` | Memory-card materialization support. |
| `node/src/stigmem_node/routes/cards.py` | Card retrieval route surface. |
| `node/src/stigmem_node/routes/recall/` | Recall orchestration and graph-weighted retrieval behavior. |
| `experimental/recall-graph/concept-pipeline.md` | Legacy compatibility pointer for recall pipeline concept links. |
| `experimental/recall-graph/concept-embeddings.md` | Legacy compatibility pointer for embedding concept links. |
| `experimental/recall-graph/concept-memory-cards.md` | Legacy compatibility pointer for memory-card concept links. |
| `experimental/recall-graph/tutorial.md` | Legacy compatibility pointer for tutorial links. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Recall behavior | `node/tests/recall/test_recall.py`; `node/tests/recall/test_recall_b1_edges.py`; `node/tests/recall/test_recall_b2_edges.py` | Recall ranking, graph weights, card fast path, and edge behavior. |
| Embeddings and vector search | `node/tests/recall/test_embeddings.py`; `node/tests/recall/test_vector_search.py` | Embedding adapters, vector storage, backfill, and metadata behavior. |
| Tombstone/card interaction | `node/tests/tombstones/test_tombstone_filter.py` | Tombstoned entities are excluded from card/recall paths. |
| Protocol index | `uv run python scripts/generate_protocol_md.py --check` | Confirms experimental Spec-X metadata remains indexed. |

## Coverage Gaps

- Full graph traversal conformance for depth, cursor stability, and garden ACL
  boundaries is incomplete.
- Cloud embedding risk acceptance is recorded in the threat model, but
  operator sampling evidence is not.
- External operator soak evidence is not recorded.
