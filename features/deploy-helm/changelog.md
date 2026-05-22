# Helm Deployment Changelog

## Unreleased

- Added ADR-020 feature record for Helm deployment.
- Moved Helm lifecycle, evidence, security posture, and release-line gates into
  the feature record.
- Kept the experimental Helm chart and operator recipe as implementation source.

## v0.9.0a1

- Tracked Helm deployment as deferred experimental deployment surface.
- Preserved chart metadata, templates, values, hardening defaults, and operator
  recipe under `experimental/deploy-helm`.
