# Spec-X3-Time-Travel — Status

> Per [ADR-008](../../docs/adr/008-experimental-gates.md), gate status for `experimental/time-travel/`.

**Spec ID:** `Spec-X3-Time-Travel`  
**Legacy section:** §24

**Status:** Dormant
**Active version:** v0.9.0a1 (last tested against)
**Last updated:** 2026-05-09
**Owner:** unowned
**Buildable:** unknown — pending PR 3 verification sweep

---

## Summary

This feature was extracted to `experimental/` per [ADR-002](../../docs/adr/002-v1-scope.md) v1 critical-path scope cut + [ADR-009](../../docs/adr/009-repo-structure.md) §2(b). Code preserved as-is from pre-reset state; no immediate plan for ADR-008 promotion.

## Why deferred

Per ADR-002, v0.9.0a1's default install matches the v1 critical-path scope. This feature is outside that scope. Re-introduction follows the [ADR-008](../../docs/adr/008-experimental-gates.md) five-gate process (threat-model delta → ADR → conformance vectors → 30-day external operator soak → documentation parity).

---

## Gate progress

| Gate | Description | Status | Date | Artifact |
|---|---|---|---|---|
| 1 | Threat-model delta | Open | — | `spec/security/deltas/time-travel-threat-model.md` |
| 2 | ADR | Open | — | `docs/adr/NNN-time-travel.md` |
| 3 | Conformance vectors | Open | — | `data/conformance/time-travel/` |
| 4 | 30-day external operator soak | Open | — | LOG.md entry |
| 5 | Documentation parity | Open | — | Learn / Build / Operate / Secure pages |

---

## Cross-references

- [`experimental/README.md`](../README.md) — canonical experimental index.
- [`docs/docs/reference/experimental-features.md`](../../docs/docs/reference/experimental-features.md) — public-facing experimental index.
- [ADR-008](../../docs/adr/008-experimental-gates.md) — re-introduction gates.
- [ADR-009](../../docs/adr/009-repo-structure.md) — repo structure.
