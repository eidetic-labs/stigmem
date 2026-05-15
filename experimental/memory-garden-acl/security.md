---
feature: memory-garden-acl
spec_id: Spec-X5-Memory-Garden
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-15
owned_risks: []
contributed_risks:
  - R-21
---

# Memory Garden ACL Security

This document records security analysis for
`experimental/memory-garden-acl/`. No owned R-XX risk is currently assigned to
this feature, but it contributes to R-21.

## Owned Risks

None currently identified. Any future owned risk must be added to the unified
threat model and this file in the same PR.

## Contributed Risks

### R-21: Agent feedback-loop worm

R-21 is cross-cutting and remains canonical in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).
Memory garden ACLs contribute to the risk because read/write graph isolation is
one of the candidate mitigations: writer keys should not be able to write into
scopes whose facts influenced the same agent session.

## Threat Model Delta

The feature can narrow or widen R-21 depending on its eventual design. A
hardened design should make session read/write boundaries explicit and
auditable. A loose design could accidentally authorize an agent to write back
into the same garden that supplied prompt-influencing facts.

## Operator Scenarios

- Do not treat garden ACLs as a complete R-21 mitigation until per-session
  read/write graph isolation is designed and tested.
- Review any feature design that grants writer keys based on recent recall
  context as security-sensitive.

## Conformance Pointers

Required adversarial vectors before promotion:

- an agent cannot write into a garden it read from in the same protected
  session;
- attempted graph-isolation bypasses leave audit evidence;
- outbound federation excludes facts derived from transitively recalled
  content until explicitly approved.

## Reintroduction Gates

Gate 1 remains open. The security delta must explicitly say whether the feature
implements, supports, or merely coexists with the R-21 mitigation design.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- ADR-003: [`docs/adr/003-prompt-injection.md`](../../docs/adr/003-prompt-injection.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
