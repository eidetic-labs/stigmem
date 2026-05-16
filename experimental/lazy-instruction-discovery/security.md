---
feature: lazy-instruction-discovery
spec_id: Spec-X1-Lazy-Instruction-Discovery
status: Experimental
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-15
owned_risks:
  - R-15
contributed_risks:
  - R-21
---

# Lazy Instruction Discovery Security

This document is the feature-owned security analysis for
`experimental/lazy-instruction-discovery/`. It is registered from the unified
threat model at [`spec/security/threat-model.md`](../../spec/security/threat-model.md).

## Owned Risks

### R-15: Instruction-scope write authority

**Threat refs:** T9-T1, T9-E1  
**STRIDE class:** Tampering / Elevation of privilege  
**Status:** Open with partial local-write mitigation
**Likelihood:** Low  
**Impact:** Critical  
**Priority:** High  
**Spec refs:** `Spec-X1-Lazy-Instruction-Discovery`, §3.5

Lazy instruction discovery lets agents load instruction-typed facts as
operational instructions at boot. Any key that can write facts with
`interpret_as="instruction"` can therefore author instructions for agents that
consume those facts. Stigmem now separates this from ordinary writes:
`interpret_as="instruction"` requires `instruction:write` on local fact writes.
Operators must still treat that grant as admin-equivalent authority over the
consuming agents.

Current controls are scope-based access control, the dedicated
`instruction:write` local-write gate, recall channel separation through
`interpret_as`, and the requirement that boot stubs embed unconditional
prohibitions directly instead of relying on lazy loaded content.

Required mitigation remains an admission boundary for lazy instruction use:
admin-approved promotion policy, federation-inbound quarantine or rejection for
instruction-typed facts, and protocol adversarial vectors for the full path.

## Contributed Risks

### R-21: Agent feedback-loop worm

R-21 is cross-cutting and remains canonical in
[`spec/security/threat-model.md`](../../spec/security/threat-model.md).
Lazy instruction discovery contributes to the risk because instruction facts
are one path by which prompt-injected or malicious content can become durable
agent behavior and then cause additional attacker-chosen writes.

## Threat Model Delta

This feature adds the agent-runtime-to-instruction-recall trust boundary
documented as TB-9 in the unified threat model. The security-sensitive
transition is content moving from persisted facts into instruction context.
That transition is higher impact than ordinary recall because it happens before
task processing and may affect all subsequent decisions by the agent.

## Operator Scenarios

- Audit every API key with `instruction:` write scope as if it were an admin
  key for the affected agents.
- Keep lazy instruction discovery disabled for production federation until the
  ADR-003 capability redesign and the `instruction_write` permission tier land.
- If an instruction-scope key is suspected compromised, revoke it immediately,
  rotate any consuming agent credentials, and review recent `instruction:`
  writes before restarting affected agents.

## Conformance Pointers

Required adversarial vectors before promotion:

- instruction-typed fact write without `instruction_write` capability returns
  403;
- federation inbound instruction-typed facts are quarantined by default;
- boot-time instruction recall excludes quarantined facts;
- cross-agent instruction namespace reads are denied.

## Reintroduction Gates

Gate 1 stays blocked until the ADR-003 implementation shape is available. The
feature cannot graduate while R-15 remains open, because the original design
does not distinguish regular fact writes from instruction-authoring writes.

## Cross-References

- Unified threat model: [`spec/security/threat-model.md`](../../spec/security/threat-model.md)
- Feature status: [`STATUS.md`](STATUS.md)
- Feature spec: [`spec.md`](spec.md)
- ADR-003: [`docs/adr/003-prompt-injection.md`](../../docs/adr/003-prompt-injection.md)
- ADR-018: [`docs/adr/018-security-documentation-colocation.md`](../../docs/adr/018-security-documentation-colocation.md)
