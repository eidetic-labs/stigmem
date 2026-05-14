---
spec_id: Spec-10-Hardening
version: 0.1.0-alpha.0
status: Draft
applies_to: stigmem v0.9.0aN
last_updated: 2026-05-14
supersedes: spec/stigmem-spec-v0.9.0a1.md sections 22.1, 22.2, 22.4, and 22.6
depends_on:
  - Spec-01-Core >= 0.1.0-alpha.0
  - Spec-05-Federation-Trust >= 0.1.0-alpha.0
  - Spec-06-Capability-Tokens >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
---

# Spec-10-Hardening

Transport hardening, key rotation, rate limits, quotas, container baseline, and operator hardening requirements.

## Extraction Status

This is the ADR-010 metadata stub for the modular spec migration. The normative text remains in [`../stigmem-spec-v0.9.0a1.md`](../stigmem-spec-v0.9.0a1.md) until the section-by-section extraction PR migrates the prose into this file.

## Legacy Sections

- §22.1 mTLS and transport hardening
- §22.2 Key rotation
- §22.4 Rate limits and quotas
- §22.6 Container baseline
