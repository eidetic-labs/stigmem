---
feature: gemini-adapter
spec_id: Spec-X0-Gemini-Adapter
status: Experimental
applies_to: stigmem v0.9.0a10
last_updated: 2026-05-26
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# Gemini Adapter Security Review

## Threat Model at v0.1.0

The adapter can send Stigmem tool declarations, tool arguments, source
identifiers, scope labels, and model-loop results through a host application's
Gemini integration. Risks include credential exposure, prompt/tool-call
confusion, cross-scope data disclosure through host prompts, and operators
treating model-generated summaries as authorization-grade Stigmem facts.

## Mitigations Implemented

- The Gemini SDK is imported lazily and is an optional runtime extra, so
  installing the plugin does not contact Gemini or configure providers by
  itself.
- Runtime behavior is host-application driven; there is no default node hook
  that automatically sends facts or queries to Gemini.
- `dispatch()` returns JSON error payloads instead of raising through the model
  loop.
- The optional `run()` loop caps tool-call rounds to limit runaway tool cycles.
- Configuration is explicit through `STIGMEM_*` and `GOOGLE_API_KEY`
  environment variables.
- The adapter contributes to R-01 and R-02 because it handles externally
  mediated tool calls that must remain provenance-scoped and authorization
  aware.
- The adapter contributes to R-21 because live Gemini deployments call an
  external provider backend; operators must treat that network boundary as an
  explicit deployment choice.

## Open Risks for Post-v0.1.0

- Add live-provider evidence for selected Gemini SDK and model versions.
- Document recommended prompt and response redaction for sensitive scopes.
- Add optional caller-provided allow/deny filters before dispatch.
- Add integration tests against a pinned Gemini SDK version if the project
  selects a supported live-model validation lane.

## v0.1.0 Disclaimer

This adapter is `experimental` and `opt-in`. Operators using it accept the
risks documented above. Production-grade certification follows the hardened-core
release gates.
