# Content-Addressed Fact IDs Changelog

Feature-local changes are recorded here by release. During release prep,
user/operator-facing entries are promoted into the root `CHANGELOG.md`.

## Unreleased

- Added ADR-020 feature record and made this directory the canonical feature
  home for CID spec, status, evidence, security, and feature-local history.
- Recorded the `v0.9.0a3` CID validation gate for issue #554, including core
  ownership, compatibility projection, implementation coverage, and release
  posture evidence.

## v0.9.0a3 Horizon

- CID core/spec validation remains part of the active alpha horizon: core CID
  computation, write-path persistence, alias lookup, verification endpoint,
  backfill status/CLI, migration support, tests, and conformance vectors.

## v0.9.0a1 Lineage

- Monolithic spec material for content-addressed fact IDs was preserved and
  later extracted into `Spec-21-Content-Addressed-IDs`.
