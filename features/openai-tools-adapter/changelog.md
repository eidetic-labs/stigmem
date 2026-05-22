# OpenAI Tools Adapter Changelog

## Unreleased

- Added ADR-020 feature record for the OpenAI-compatible tools adapter.
- Consolidated OpenAI, LiteLLM, and OpenAI-compatible local endpoint behavior
  under this feature record.
- Kept the Ollama/LiteLLM adapter as a separate compatibility identity that
  references this adapter for implementation detail.

## v0.9.0a1

- Tracked the OpenAI tools adapter as experimental external adapter source.
- Provided OpenAI-compatible tool declarations, dispatch, LiteLLM helper loop,
  OpenAI SDK helper loop, package metadata, and mocked unit tests.
