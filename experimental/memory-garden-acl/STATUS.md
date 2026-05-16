# Spec-X5-Memory-Garden-Advanced-ACL — Status

> Per [ADR-008](../../docs/adr/008-experimental-gates.md), gate status for
> `experimental/memory-garden-acl/`. Spec ID per
> [ADR-010](../../docs/adr/010-modular-specs.md).

**Spec ID:** `Spec-X5-Memory-Garden-Advanced-ACL`
**Legacy section:** §17 advanced
**Status:** Source scaffolded / opt-in experimental; ADR-008 blocked
**Active version:** Source package scaffolded on main after v0.9.0a1; no released plugin artifact yet
**Last updated:** 2026-05-16
**Owner:** unowned for ADR-008 graduation
**Buildable:** yes

---

## Summary

Memory Garden advanced ACL behavior remains outside the v0.9.0a1 default
surface per ADR-002 and ADR-009. Basic garden CRUD, membership, and direct
`garden_id` read/write guards stay core; advanced cross-cutting ACL behavior is
being extracted into the `stigmem-plugin-memory-garden-acl` source package.

The PR 4e scaffold declares `pre_assert_authorize`, `pre_recall_authorize`, and
`recall_filter` handlers with all behavior disabled by default. Runtime behavior
movement, plugin-loaded validation, public docs closeout, and signed package
artifact evidence remain follow-on work.

## Gate progress

| Gate | Description | Status | Date | Artifact |
|---|---|---|---|---|
| 1 | Threat-model delta | Open | 2026-05-15 | [`security.md`](security.md) |
| 2 | ADR | Open | — | — |
| 3 | Conformance vectors | Open | — | — |
| 4 | 30-day external operator soak | Open | — | — |
| 5 | Documentation parity | Open | — | — |

## History

- **2026-05-16** — PR 4e #331 documented the extraction boundary. Basic garden
  CRUD/membership and direct `garden_id` read/write guards remain core; advanced
  cross-cutting ACL behavior is the plugin target.
- **2026-05-16** — PR 4e #332 scaffolded the
  `experimental/memory-garden-acl/` plugin source package with manifest, config
  schema, hook placeholders, and registration/order tests.
- **2026-05-15** — added ADR-018 colocated security analysis in `security.md`.
