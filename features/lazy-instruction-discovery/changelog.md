# Lazy Instruction Discovery Changelog

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for lazy instruction discovery spec, status, evidence, security, and
  feature-local history.

## Post-v0.9.0a1 Main

- Added `experimental/lazy-instruction-discovery/` as the
  `stigmem-plugin-lazy-instruction-discovery` source package.
- Added plugin registration, default no-plugin tests, plugin-loaded route
  tests, and hook-order tests.
- Kept signed/package artifact evidence deferred to the plugin launch train.
