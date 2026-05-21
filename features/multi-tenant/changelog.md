# Multi-Tenant Scoping Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for multi-tenant scoping spec, status, evidence, security, and
  feature-local history.

## Post-v0.9.0a1 Main

- Added `experimental/multi-tenant/` as the
  `stigmem-plugin-multi-tenant` source package.
- Added default-collapse behavior so default installs resolve all callers into
  the `default` tenant.
- Added plugin-enabled route and plugin tests for tenant isolation, garden
  isolation, slug reuse, audit scoping, and hook registration.
