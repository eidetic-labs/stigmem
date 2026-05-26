# Gemini Adapter Evidence

## Conformance Test Corpus

The v0.1.0 package keeps the existing mock-based unit test corpus:

- `tests/test_gemini_adapter.py::test_declarations_contains_five_tools`
- `tests/test_gemini_adapter.py::test_declarations_use_uppercase_types`
- `tests/test_gemini_adapter.py::test_from_env_reads_url`
- `tests/test_gemini_adapter.py::test_gemini_tools_returns_declarations`
- `tests/test_gemini_adapter.py::test_dispatch_assert_fact`
- `tests/test_gemini_adapter.py::test_dispatch_query_facts`
- `tests/test_gemini_adapter.py::test_dispatch_unknown_function`

The tests mock Stigmem HTTP calls and do not require a live Stigmem node,
Gemini API key, or Gemini SDK.

## Validation Runs

v0.1.0 publication validation covers:

- src-layout import path: `stigmem_plugin_gemini.adapter`
- entry-point manifest: `gemini-adapter`
- package metadata and README guard compliance
- mocked Gemini declaration, environment configuration, dispatch, and error
  handling behavior

Live Gemini API/model validation remains outside the automated release gate for
this experimental package.

## Known False-Positive / False-Negative Cases

- The mocked corpus validates Gemini declaration shape, not live Gemini model
  acceptance for every supported model family.
- The convenience `run()` loop is dependency-optional and requires host-level
  API key configuration; package tests avoid live API calls by design.
- Model tool-call selection quality is a Gemini/provider concern and is not
  treated as a Stigmem adapter conformance signal.
