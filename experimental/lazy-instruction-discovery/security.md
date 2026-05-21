---
feature: lazy-instruction-discovery
spec_id: Spec-X1-Lazy-Instruction-Discovery
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-21
owned_risks:
  - R-15
contributed_risks:
  - R-21
---

# Lazy Instruction Discovery Security

This file is a compatibility pointer for existing
`experimental/lazy-instruction-discovery/security.md` links.

The canonical ADR-020 feature security record now lives at
[`features/lazy-instruction-discovery/security.md`](../../features/lazy-instruction-discovery/security.md).

This compatibility file remains registered for the security-documentation
validator while legacy links migrate. Lazy instruction discovery owns R-15
instruction-scope write authority and contributes to R-21 agent feedback-loop
worm risk; the canonical analysis is now in the feature record.
