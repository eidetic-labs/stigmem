# Spec-X1-Lazy-Instruction-Discovery — Status

> Per [ADR-008](../../docs/adr/008-experimental-gates.md), gate status for `experimental/lazy-instruction-discovery/`. Spec ID per [ADR-010](../../docs/adr/010-modular-specs.md).

**Spec ID:** `Spec-X1-Lazy-Instruction-Discovery`
**Legacy section:** §21
**Status:** Blocked
**Active version:** v0.9.0a1 (code last functional under retracted v1.0)
**Last updated:** 2026-05-15
**Owner:** unowned (contributors may revisit after ADR-003 lands)
**Buildable:** yes — code compiles; tests pass at the level the original author wrote them

---

## Summary

§21 introduces a `recall_instruction` tool that agents call at boot time to load instruction-typed facts as their operational instructions. Unlike facts retrieved during task execution (which the agent treats as content), instructions retrieved at boot time become part of the agent's *governing instructions* before any task is processed. This was intended to enable runtime-configurable agent behavior — operators could update an agent's instructions by writing facts, without redeploying the agent.

## Why deferred

Per ADR-002 and the threat-model risk register:

- **R-15 (Critical/High):** `instruction:write` permission in the original §21 design is functionally equivalent to admin authority over any agent using lazy discovery. There is no current technical gate separating `instruction:write` from general `write` permission. Anyone with write access to the `instruction:` scope can author agent instructions.
- **The v1.0 prompt-injection model relied on the §19.7 sanitizer, which is structurally inadequate** (per ADR-003). §21 amplifies that inadequacy: injection content lands in the system prompt, not in mid-task content.
- **The OpenClaw audit's C4 finding (handoff worm vector)** is a related class of attack that operates at the adapter level. §21 is the protocol-level analogue.

Reintroducing §21 without first solving these issues would be the single most direct route to recreating the v1.0 retraction conditions.

---

## Gate progress

| Gate | Description | Status | Date | Artifact |
|---|---|---|---|---|
| 1 | Threat-model delta | **Blocked** on ADR-003 | 2026-05-15 | [`security.md`](security.md) |
| 2 | ADR (redesign required) | **Blocked** on Gate 1 | — | (deferred) |
| 3 | Conformance vectors (especially adversarial) | Open | — | — |
| 4 | 30-day external operator soak | Open | — | — |
| 5 | Documentation parity | Open | — | — |

---

## Notes per gate

### Gate 1 — Threat-model delta

The delta cannot be productively written until ADR-003 (capability-based prompt-injection handling) is accepted and implemented. Once ADR-003 lands, the delta will need to address:

- Does §21 use the `interpret_as = "instruction"` flag from ADR-003, or does it have its own permission model?
- The dedicated `instruction_write` permission tier proposed in §8.2 of the threat model needs a concrete design. Should it be a new scope (`instruction:`-prefixed scopes are admin-write-only by default), a new capability-token verb, or both?
- Cross-org instruction loading: should `recall_instruction` ever return instruction-typed facts written by federated peers? The current §21 design says yes; ADR-003's quarantine-by-default for cross-org instructions says no.
- Boot-stub embedding requirements: §21.1.1 requires unconditional prohibitions to be embedded directly in the boot stub body. The threat-model delta needs to specify what "unconditional" means in operational terms.

The feature-owned security analysis now lives in [`security.md`](security.md)
per ADR-018. It records R-15 as the owned risk and R-21 as a contributed
cross-cutting risk.

**Estimated work to complete Gate 1 once unblocked:** 1 week of focused design + review.

### Gate 2 — ADR

The ADR must address the redesign questions from Gate 1. The original §21 spec is a starting point but cannot be reintroduced as-is — too many of its assumptions are incompatible with the post-ADR-003 model.

**Estimated work:** 1 week after Gate 1 is done.

### Gate 3 — Conformance vectors

Required adversarial vectors (at minimum):

- Instruction-typed fact write without `instruction_write` capability → expect 403.
- Federation inbound instruction-typed fact → expect quarantine.
- Boot-stub `recall_instruction` call returning a quarantined fact → expect that the quarantined fact is excluded.
- Capability-token verb forgery attempting `instruction:write` → expect rejection.
- Cross-namespace read attempt (agent A reading agent B's instructions) → expect 403.

Existing tests under `experimental/21-lazy-instruction-discovery/tests/` predate the ADR-003 model and need replacement.

### Gate 4 — Operator soak

§21 is high-blast-radius if mishandled. Soak operator must be willing to run instruction-typed facts in a non-critical workload (e.g., a developer-tools internal agent) and report findings publicly. **Soak duration: minimum 30 days, recommended 60 days for this feature** because the operational consequences of an undetected `instruction:write` mistake are slow to surface.

### Gate 5 — Documentation parity

- **Learn:** explanation of the lazy-load model and why it's distinct from regular recall.
- **Build:** API reference for `recall_instruction`; integration patterns for boot stubs.
- **Operate:** runbook for instruction-promotion approval (cross-org); auditing `instruction:` scope grants.
- **Secure:** scenarios.md updates for R-15 once the redesign closes the structural gap; threat-model delta link.

---

## Open questions

1. **Should the redesigned `recall_instruction` be a distinct API endpoint or a special mode of `recall()`?** The original §21 has it as distinct; integration with ADR-003's channel separation might unify them.

2. **What's the right default behavior for an agent whose instruction recall fails?** Original §21 had implicit fallback to whatever is in the boot stub body. The hardened design needs an explicit failure mode (refuse to start? fall back to boot stub? alert operator?) — and the choice has security implications.

3. **Does instruction promotion (cross-org admin approval) need its own audit-event type beyond `instruction_promoted`?** Per ADR-003, the answer is currently no; revisit if the delta surfaces additional needs.

4. **Should §21 require ADR-003 to be `Accepted` and implemented, or only `Accepted`?** Recommend: implemented. §21 design depends on the actual data-model shape, not just the decision to ship it.

---

## History

- **2026-05-15** — added ADR-018 colocated security analysis in `security.md`.
- **2026-05-06** — moved to `experimental/` per ADR-002. Status: Blocked on ADR-003.
- **2026-05-04** — original §21 normative spec published in v2.0 (now retracted).
- **2026-05-03** — `EXPERIMENTAL` caution banner added to §21 in spec (see commit `10c4ace`); this was the early signal that the feature wasn't shipping confidently.
