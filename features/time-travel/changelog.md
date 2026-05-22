# Time-Travel Queries Changelog

Feature-local changes are recorded here by release. During release prep,
user/operator-facing entries are promoted into the root `CHANGELOG.md`.

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for time-travel spec, status, evidence, security, and feature-local
  history.
- Tightened the plugin boundary so registered time-travel plugins still require
  explicit operator enablement for fact-query and recall `as_of` surfaces.
- Added historical query validation for recall retention floors, recency scoring
  relative to `as_of`, CID tamper rejection, and rank-hook visibility limits.
- Added a4 security-posture coverage for retroactive tombstone suppression and
  non-admin legal-hold responses that do not reveal legal-hold existence.

## Post-v0.9.0a1 Main

- Added `experimental/time-travel/` as the `stigmem-plugin-time-travel` source
  package.
- Added manifest, config schema, hook placeholders, registration tests,
  deterministic hook-order coverage, and plugin discovery coverage.
- Updated default install behavior so `as_of` requests fail closed when the
  plugin is not loaded.
- Preserved plugin-loaded fact-query and recall `as_of` behavior for alpha
  validation.

## v0.9.0a4 Horizon

- Time-travel query support is the active alpha-series plugin-boundary
  validation target for `as_of` read semantics, default fail-closed behavior,
  tombstone-aware historical recall, security posture, and operator activation
  guidance.

## v0.9.0a1 Lineage

- Monolithic spec material preserved section 24 time-travel/as-of query
  semantics before extraction to `Spec-X3-Time-Travel-Queries`.
