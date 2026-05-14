---
spec_id: Spec-12-HLC-Bounded-Skew
version: 0.1.0-alpha.0
status: Draft
applies_to: stigmem v0.9.0aN
last_updated: 2026-05-14
supersedes: R-19 HLC bounded-skew follow-up material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-05-Federation-Trust >= 0.1.0-alpha.0
---

# Spec-12-HLC-Bounded-Skew

Remote HLC skew bounds, rejection/degradation behavior, audit events, metrics, and federation ordering invariants.

## Extraction Status

This is the ADR-010 metadata stub for the modular spec migration. The HLC bounded-skew design is new material introduced after the v0.9.0a1 reset and remains tied to R-19 review evidence until the section-by-section extraction PR writes the normative prose here.

## Source Material

- [`../security/threat-model.md`](../security/threat-model.md) R-19 and related STRIDE entries
- Current reference-node HLC and federation ingest implementation
