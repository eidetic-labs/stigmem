# Cognee Adapter Evidence

## Conformance Test Corpus

The v0.1.0 package keeps the existing mock-based unit test corpus:

- `tests/test_cognee_adapter.py::test_fact_to_text_basic`
- `tests/test_cognee_adapter.py::test_parse_round_trip`
- `tests/test_cognee_adapter.py::test_normalize_dict_results`
- `tests/test_cognee_adapter.py::test_assert_to_cognee_calls_add_and_cognify`
- `tests/test_cognee_adapter.py::test_batch_assert_calls_add_n_times_cognify_once`
- `tests/test_cognee_adapter.py::test_query_from_cognee_normalizes_results`

The tests mock the Cognee module and do not require a live Cognee runtime, LLM
provider, vector store, or Stigmem node.

## Validation Runs

v0.1.0 publication validation covers:

- src-layout import path: `stigmem_plugin_cognee.adapter`
- entry-point manifest: `cognee-adapter`
- package metadata and README guard compliance
- mocked Cognee assertion, batch assertion, configuration, and query behavior

Live Cognee runtime validation remains outside the automated release gate for
this experimental package.

## Known False-Positive / False-Negative Cases

- Opaque Cognee search payloads intentionally become fallback text records.
- Cognee graph deduplication behavior is runtime-dependent and is not asserted
  by the package tests.
- LLM extraction quality is a Cognee/provider concern and is not treated as a
  Stigmem adapter conformance signal.
