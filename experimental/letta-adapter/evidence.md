# Letta Adapter Evidence

## Conformance Test Corpus

The v0.1.0 package keeps the existing mock-based unit test corpus:

- `tests/test_letta_adapter.py::test_fact_to_text_basic`
- `tests/test_letta_adapter.py::test_parse_round_trip`
- `tests/test_letta_adapter.py::test_from_env_reads_defaults`
- `tests/test_letta_adapter.py::test_push_to_letta_calls_insert`
- `tests/test_letta_adapter.py::test_batch_push_calls_insert_n_times`
- `tests/test_letta_adapter.py::test_pull_parses_stigmem_fact`
- `tests/test_letta_adapter.py::test_pull_stigmem_only_filters`
- `tests/test_letta_adapter.py::test_push_raises_import_error_without_letta`

The tests mock the Letta module and do not require a live Letta server, agent,
or Stigmem node.

## Validation Runs

v0.1.0 publication validation covers:

- src-layout import path: `stigmem_plugin_letta.adapter`
- entry-point manifest: `letta-adapter`
- package metadata and README guard compliance
- mocked Letta serialization, environment configuration, push, batch push,
  pull, filtering, and missing-dependency behavior

Live Letta runtime validation remains outside the automated release gate for
this experimental package.

## Known False-Positive / False-Negative Cases

- Letta archival memory deduplication and pagination behavior is
  runtime-dependent and is not asserted by package tests.
- The mocked corpus validates client call shape, not a live Letta server's
  storage behavior.
- Host-level prompt and write policy is outside the adapter conformance signal.
