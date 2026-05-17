# Spec-X3-Time-Travel — Status

> Per [ADR-008](../../docs/adr/008-experimental-gates.md), gate status for
> `experimental/time-travel/`. Spec ID per
> [ADR-010](../../docs/adr/010-modular-specs.md).

**Spec ID:** `Spec-X3-Time-Travel-Queries`
**Legacy section:** §24
**Status:** Extracted / opt-in experimental; ADR-008 graduation blocked
**Active version:** source extracted on `main` after v0.9.0a1; queued for a later alpha artifact refresh
**Last updated:** 2026-05-16
**Owner:** unowned for ADR-008 graduation; PR 4c extraction maintained in `experimental/time-travel/`
**Buildable:** yes — plugin source, manifest registration, default no-plugin tests, plugin-loaded fact/recall tests, and hook-order tests pass on `main`

This feature remains outside the default surface per [ADR-002](../../docs/adr/002-v1-scope.md) and [ADR-009](../../docs/adr/009-repo-structure.md); shared promotion gates live in [../STATUS-GATES.md](../STATUS-GATES.md).

---

## Summary

Spec-X3 defines historical `as_of` queries for facts and recall. PR 4c moved
that behavior behind the `stigmem-plugin-time-travel` source package. Default
installs now fail closed with `time_travel_plugin_not_loaded` when callers pass
`as_of`; plugin-loaded test clients preserve the historical fact-query and
recall behavior for alpha validation.

This extraction validates the ADR-011 plugin boundary for time-travel hooks. It
does not graduate the feature into the supported surface, and it does not mean a
signed or published plugin artifact is available yet.

## Gate progress

| Gate | Description | Status | Date | Artifact |
|---|---|---|---|---|
| 1 | Threat-model delta | Partial | 2026-05-16 | [`security.md`](security.md) records R-17/R-18 contributions; promotion still requires legal-hold and CID/source-trust test evidence |
| 2 | ADR or amendment | Open | — | — |
| 3 | Conformance vectors | Partial | 2026-05-16 | Plugin-required vectors and plugin-loaded/default-install tests on `main` |
| 4 | 30-day external operator soak | Open | — | — |
| 5 | Documentation parity | Open | — | Artifact publication evidence deferred until all planned plugins are built |

## History

- **2026-05-16** — PR 4c validation landed default-install fail-closed tests,
  plugin-loaded fact/recall `as_of` tests, deterministic hook-order coverage,
  and v2 conformance coverage for plugin-required vectors.
- **2026-05-16** — PR 4c gating moved default-install `as_of` behavior behind
  `stigmem-plugin-time-travel` registration.
- **2026-05-16** — PR 4c scaffold added the
  `experimental/time-travel/` source package with manifest, config schema,
  hook placeholders, and registration tests.
- **2026-05-09** — moved to `experimental/` per ADR-002 and ADR-009.
