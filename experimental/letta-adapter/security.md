---
feature: letta-adapter
spec_id: Spec-X0-Letta-Adapter
status: Experimental
applies_to: stigmem v0.9.0a10
last_updated: 2026-05-26
owned_risks: []
contributed_risks:
  - R-01
  - R-02
  - R-21
---

# Letta Adapter Security Review

## Threat Model at v0.1.0

The adapter can send Stigmem fact content, source identifiers, scope labels,
and confidence values to a configured Letta server and target agent. Risks
include credential exposure, wrong-agent writes, native-memory confusion,
cross-scope archival leakage, and operators treating agent memory as
authorization-grade Stigmem facts.

## Mitigations Implemented

- Letta is imported lazily and is an optional runtime extra, so installing the
  plugin does not contact Letta or configure credentials by itself.
- Runtime behavior is host-application driven; there is no default node hook
  that automatically exports facts.
- Push and pull calls require an explicit `agent_id`.
- Stigmem-origin passages use a `[stigmem]` prefix and `stigmem_only=True` can
  filter native Letta memories.
- Configuration is explicit through `LETTA_URL` and `LETTA_TOKEN`.
- The adapter contributes to R-01 and R-02 because it handles externally stored
  memory records that must remain provenance-scoped and authorization aware.
- The adapter contributes to R-21 because live Letta deployments may cross an
  external network boundary; operators must treat that as an explicit
  deployment choice.

## Open Risks for Post-v0.1.0

- Add live Letta server evidence for selected Letta versions.
- Document recommended agent partitioning for Stigmem scopes.
- Add optional caller-provided redaction/filter callbacks before Letta export.
- Add integration tests against a pinned Letta runtime when the project selects
  a supported Letta validation lane.

## v0.1.0 Disclaimer

This adapter is `experimental` and `opt-in`. Operators using it accept the
risks documented above. Production-grade certification follows the hardened-core
release gates.
