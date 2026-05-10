---
feature: intent-envelope
status: deferred-indefinitely
spec_id: (no Spec-X assigned — deferred indefinitely per ADR-001; if reintroduced, gets next available Spec-X number per ADR-010)
legacy_section: §4
applies_to: stigmem v0.9.0a1
last_updated: 2026-05-09
---

# §4 Intent Envelope — STATUS

## What this is

§4 of the stigmem spec described an `IntentEnvelope` shape — a typed envelope wrapping goals, constraints, preferences, and handoffs into atomic protocol units. The original design intent: agent runtimes communicate intent transitions (start work, hand off, abandon, escalate) via standardized envelope facts that downstream agents and operators can reason about uniformly.

## Status

**Deferred indefinitely** per [ADR-001](../../docs/adr/001-versioning.md). Per `spec/EVOLUTION.md`: §4 Intent Envelope was retained as a non-normative appendix stub through v1.0 evolutionary checkpoints, never implemented, and removed from active roadmap before the v0.9.0a1 reset.

## Why the design intent is worth preserving

Despite never being implemented, the §4 design captured a coherent abstraction over agent intent transitions that current handoff/decision/escalation patterns (per the OpenClaw adapter) approximate piecemeal. A future re-introduction would consolidate those patterns under a single typed envelope shape.

## Reintroduction gates (per ADR-008)

If §4 returns, all five ADR-008 gates apply. The most likely path:

1. **Threat-model delta:** how does an Intent Envelope affect the prompt-injection trust boundary (per ADR-003)? Does it expose new authz surface for instruction-typed envelope contents?
2. **ADR drafted and merged:** what's the v1.x or v2.x shape of `IntentEnvelope`? Does it supersede or complement the current handoff/decision/escalation primitives?
3. **Conformance vectors:** how does an envelope fact differ on the wire from a regular fact? What validations apply?
4. **30-day external operator soak:** which adapter ships the first IntentEnvelope-using deployment?
5. **Documentation parity:** Learn / Build / Operate / Secure tab presence per ADR-005.

## Cross-references

- Spec text: [`experimental/intent-envelope/spec.md`](spec.md) — content migrated from `docs/docs/spec/intent-envelope.md` per master-checklist §4.3a stale-page evaluation.
- Original snapshots: [`spec/archive/evolution/`](../../spec/archive/evolution/) — search for "Intent Envelope" or "§4" in any pre-reset checkpoint.
- ADR-001 — versioning, why §4 was deferred indefinitely.
- ADR-008 — reintroduction gates.
