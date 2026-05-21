# RTBF Tombstones Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for tombstone spec, status, evidence, security, and feature-local
  history.

## Post-v0.9.0a1 Main

- Added `experimental/tombstones/` as the `stigmem-plugin-tombstones` source
  package.
- Added plugin manifest, config schema, hook placeholders, migration
  declaration, registration tests, plugin-loaded tests, and deterministic hook
  ordering coverage.
- Kept signed/package artifact evidence deferred to the plugin launch lane.
