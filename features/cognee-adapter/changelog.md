# Cognee Adapter Changelog

## Unreleased

- Removed the `cognee` optional dependency extra before v0.9.0a10 tagging so
  default plugin and meta-package installs do not resolve Cognee's transitive
  `diskcache==5.6.3` dependency while `CVE-2025-69872` has no audited
  non-vulnerable dependency path.
- Packaged the adapter as `stigmem-plugin-cognee-adapter` v0.1.0 with
  src-layout metadata, a Stigmem plugin discovery manifest, and publication
  records for the v0.9.0a10 adapter batch.

## 2026-05-21

- Added ADR-020 feature record for the Cognee adapter and made this directory
  the canonical location for adapter behavior, evidence, security posture, and
  release status.

## v0.9.0a1

- Tracked the Cognee adapter as dormant experimental external adapter surface
  area outside the current alpha artifact set.
