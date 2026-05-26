---
feature: cognee-adapter
spec_id: Spec-X0-Cognee-Adapter
status: Experimental
applies_to: stigmem v0.9.0a10
last_updated: 2026-05-25
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# Cognee Adapter Security Review

## Threat Model at v0.1.0

The adapter can send Stigmem fact content, source identifiers, scope labels,
and confidence values to a Cognee runtime and its configured LLM/vector-store
providers. Risks include credential exposure, unintended cross-scope indexing,
provider retention of sensitive fact text, and operators treating semantic
Cognee results as authorization-grade Stigmem facts.

## Mitigations Implemented

- Cognee is imported lazily, so installing the plugin does not contact Cognee or
  configure providers by itself.
- Runtime behavior is host-application driven; there is no default node hook
  that automatically exports facts.
- Configuration is explicit through `COGNEE_*` environment variables.
- Opaque Cognee results are labeled with `relation="cognee:result"` rather than
  silently pretending to be exact Stigmem facts.
- The adapter contributes to R-01 and R-02 because it handles externally sourced
  semantic memory data that must remain provenance-scoped and authorization
  aware.
- The adapter contributes to R-21 because live Cognee deployments may call
  external provider backends; operators must treat those network boundaries as
  explicit deployment choices.

## Open Risks for Post-v0.1.0

- Add live-provider evidence for selected Cognee versions and storage backends.
- Document recommended dataset partitioning for Stigmem scopes.
- Add optional caller-provided redaction/filter callbacks before Cognee export.
- Add integration tests against a pinned Cognee runtime when the project selects
  a supported Cognee version.

## v0.1.0 Disclaimer

This adapter is `experimental` and `opt-in`. Operators using it accept the risks
documented above. Production-grade certification follows the hardened-core
release gates.
