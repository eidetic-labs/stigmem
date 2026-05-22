# systemd Deployment Changelog

## Unreleased

- Added ADR-020 feature record for systemd deployment.
- Moved systemd lifecycle, evidence, security posture, and release-line gates
  into the feature record.
- Kept the experimental installer, environment template, service unit, and
  operator recipe as implementation source.
- Corrected stale recipe paths and default install version references to match
  the current alpha line.

## v0.9.0a1

- Tracked systemd deployment as deferred experimental deployment surface.
- Preserved installer, service unit, environment template, reverse proxy,
  offline install, logging, upgrade, and uninstall guidance under
  `experimental/deploy-systemd`.
