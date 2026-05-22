# Fly.io Deployment Status

The Fly.io deployment is deferred for the current alpha artifact set. Node and
dashboard configuration files exist, but live Fly validation, persistence and
restore evidence, production secrets review, and ownership are not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `stigmem` |
| Implementation | `experimental/deploy-fly` |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Fly.io deployment source existed as deferred experimental deployment surface. | `experimental/deploy-fly/STATUS.md`; `experimental/deploy-fly/fly.toml` |
| `0.9.xA` planned | Keep Fly.io discoverable while live deployment, secrets, persistence, dashboard validation, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Node README, node Fly configs, and dashboard Fly config exist. |
| Feature record | Complete | ADR-020 feature record added under `features/deploy-fly`. |
| Static config syntax | Required per PR | Fly TOML files should parse before migration PR merge. |
| Live Fly deployment | Open | No current Fly app deployment evidence is recorded. |
| Persistence and restore | Open | Volume creation is documented, but backup/restore validation is not recorded. |
| Secrets posture review | Open | OIDC, libSQL, encryption, and dashboard secrets require release-line review. |
| Dashboard validation | Open | Dashboard Fly config exists, but live dashboard deployment validation is not recorded. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- Fly.io is not the supported current alpha deployment path.
- Live node and dashboard validation are not complete.
- Persistence backup/restore and secret-handling evidence are not complete.
