# Multi-Tenant Scoping Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for multi-tenant scoping spec, status, evidence, security, and
  feature-local history.
- Aligned a8 feature records and public projections around the same posture:
  multi-tenant scoping is opt-in experimental plugin behavior, default installs
  collapse to the `default` tenant, and shared-node readiness is not claimed.
- Added tenant-ID normalization/validation, explicit TenantContext source
  metadata, and structural CI coverage for tenant context construction.
- Documented the capability reservation and core-enforced/plugin-acknowledged
  hook pattern for the a8 plugin boundary.

## Post-v0.9.0a1 Main

- Added `experimental/multi-tenant/` as the
  `stigmem-plugin-multi-tenant` source package.
- Added default-collapse behavior so default installs resolve all callers into
  the `default` tenant.
- Added plugin-enabled route and plugin tests for tenant isolation, garden
  isolation, slug reuse, audit scoping, and hook registration.
- Added cross-surface coverage for recall, tracing labels, subscription fan-out,
  billing tenant propagation, and node-level federation pull default-tenant-only
  behavior.

## v0.9.0a8 Horizon

- Multi-tenant scoping remains an opt-in alpha-series plugin target for
  tenant-context enforcement, isolation tests, and operator-facing activation
  guidance.
- Tenant-aware non-default federation, per-tenant quota/resource isolation,
  operator soak evidence, and signed plugin artifacts remain outside the a8
  claim.
