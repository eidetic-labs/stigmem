# PaaS Deployment Changelog

## Unreleased

- Added ADR-020 feature record for PaaS deployment.
- Moved PaaS lifecycle, evidence, security posture, and release-line gates into
  the feature record.
- Kept the experimental Render, Railway, AWS App Runner, and Google Cloud Run
  recipes as implementation source.

## v0.9.0a1

- Tracked PaaS deployment as deferred experimental deployment surface.
- Preserved Render, Railway, AWS App Runner, Google Cloud Run, persistence,
  secrets, health-check, OIDC, and scale-to-zero guidance under
  `experimental/deploy-paas`.
