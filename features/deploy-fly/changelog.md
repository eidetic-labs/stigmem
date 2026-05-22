# Fly.io Deployment Changelog

## Unreleased

- Added ADR-020 feature record for Fly.io deployment.
- Moved Fly.io lifecycle, evidence, security posture, and release-line gates
  into the feature record.
- Kept the experimental Fly.io node and dashboard deployment recipes as
  implementation source.

## v0.9.0a1

- Tracked Fly.io deployment as deferred experimental deployment surface.
- Preserved node Fly config, hosted-node config, dashboard config, persistent
  volume guidance, OIDC setup, storage-backend notes, scale-to-zero notes, and
  metrics configuration under `experimental/deploy-fly`.
