---
feature: time-travel
spec_id: Spec-X3-Time-Travel-Queries
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-21
owned_risks: []
contributed_risks:
  - R-17
  - R-18
---

# Time-Travel Queries Security

This file is a compatibility pointer for existing
`experimental/time-travel/security.md` links.

The canonical ADR-020 feature security record now lives at
[`features/time-travel/security.md`](../../features/time-travel/security.md).

This compatibility file remains registered for the security-documentation
validator while legacy links migrate. Time-travel contributes to R-17
legal-hold historical data exposure and R-18 CID field-exclusion tampering; the
canonical analysis for both contributions is now in the feature record.

The implementation package remains in `experimental/time-travel/` during the
transition. Security analysis, residual risk, and promotion blockers belong in
the feature record.
