---
spec_id: Spec-13-Capability-Based-Instructions
version: 0.1.0-alpha.0
status: Draft
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: ADR-003 capability-based prompt-injection redesign material
depends_on:
  - Spec-01-Core >= 0.1.0-alpha.0
  - Spec-06-Capability-Tokens >= 0.1.0-alpha.0
  - Spec-07-Recall-Pipeline >= 0.1.0-alpha.0
---

# Spec-13-Capability-Based-Instructions

Structural content/instruction separation, explicit promotion of recalled memory into executable instruction, provenance retention, and capability enforcement for agent instruction flows.

## Extraction Status

This is the ADR-010 metadata stub for the modular spec migration. The normative prose is targeted for the v0.9.0bN capability-redesign work and remains anchored in ADR-003 until extracted.

## Source Material

- [`../../docs/adr/003-prompt-injection.md`](../../docs/adr/003-prompt-injection.md)
- R-15 and R-21 entries in [`../security/threat-model.md`](../security/threat-model.md)
