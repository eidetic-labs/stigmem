# multi-tenant — Status

multi-tenant is Source-available experimental on `main` after Stigmem issue
[#431](https://github.com/Eidetic-Labs/stigmem/issues/431); owner unowned;
buildable from source; last updated 2026-05-17. Spec ID: (no Spec-X assigned
— deferred per [ADR-002](../../docs/adr/002-v1-scope.md); if reintroduced,
gets next available Spec-X number per
[ADR-010](../../docs/adr/010-modular-specs.md)). Legacy section: not
applicable.

This feature remains outside the default surface per [ADR-002](../../docs/adr/002-v1-scope.md) and [ADR-009](../../docs/adr/009-repo-structure.md); shared promotion gates live in [../STATUS-GATES.md](../STATUS-GATES.md).

Gate 1 threat-model delta is tracked in [`security.md`](security.md). It records
multi-tenant contributions to R-01, R-02, and R-21 while keeping those risks
canonical in the protocol-level threat model until the feature is assigned a
numbered Spec-X.

Runtime behavior is opt-in. Default installs collapse callers into the
single-tenant `default` partition even when stored API keys carry non-default
tenant IDs. Installing and enabling `stigmem-plugin-multi-tenant` restores
non-default tenant resolution through the `tenant_resolve` hook.
