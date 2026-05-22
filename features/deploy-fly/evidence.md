# Fly.io Deployment Evidence

This file records evidence for the Fly.io deployment feature. The current
record is source-inventory and static syntax evidence only; it does not claim
live Fly deployment support.

## Source Inventory

| Path | Evidence |
| --- | --- |
| `experimental/deploy-fly/README.md` | First-time setup, secrets, deploy, health check, libSQL/Turso, scale-to-zero, encryption, and metrics guidance. |
| `experimental/deploy-fly/fly.toml` | Reference Stigmem node Fly configuration. |
| `experimental/deploy-fly/infra-fly.toml` | Hosted-node Fly configuration variant with auth and OIDC enabled. |
| `experimental/deploy-fly/fly.dashboard.toml` | Dashboard Fly configuration. |
| `experimental/deploy-fly/STATUS.md` | Legacy pointer after ADR-020 migration. |

## Validation

| Check | Status | Notes |
| --- | --- | --- |
| Feature record validation | Required per PR | `python3 scripts/check_feature_records.py`. |
| Feature projection validation | Required per PR | `python3 scripts/check_feature_projections.py`. |
| Security projection validation | Required per PR | `python3 scripts/check_feature_security_projection.py`. |
| Changelog projection validation | Required per PR | `python3 scripts/check_feature_changelog_projection.py`. |
| Compatibility projection validation | Required per PR | `python3 scripts/check_feature_compatibility_projection.py`. |
| Protocol projection validation | Required per PR | `python3 scripts/check_feature_protocol_projection.py`. |
| Static TOML syntax | Required per PR | Parse `fly.toml`, `infra-fly.toml`, and `fly.dashboard.toml` with Python `tomllib`. |

## Open Evidence

- No live Fly app deployment evidence is recorded.
- No Fly volume backup and restore validation is recorded.
- No live dashboard deployment evidence is recorded.
- No operator ownership evidence is recorded.
