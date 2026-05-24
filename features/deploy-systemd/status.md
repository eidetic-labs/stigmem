# systemd Deployment Status

The systemd deployment is deferred for the current alpha artifact set.
Installer, environment template, service unit, and operator guidance exist, but
live distro validation, installer review, hardening review, upgrade/rollback
validation, offline-install validation, and ownership are not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `external` |
| Owner | `unowned` |
| Package | `stigmem-node` |
| Implementation | `experimental/deploy-systemd` |
| Publication state | `defer` - deployment helper, not a standalone plugin artifact; live distro validation remains open. |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | systemd deployment source existed as deferred experimental deployment surface. | `experimental/deploy-systemd/STATUS.md`; `experimental/deploy-systemd/stigmem-node.service` |
| `0.9.xA` planned | Keep systemd discoverable while live distro validation, installer review, hardening review, upgrade/rollback validation, offline install, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | README, installer, environment template, and service unit exist. |
| Feature record | Complete | ADR-020 feature record added under `features/deploy-systemd`. |
| Shell syntax | Required per PR | `bash -n experimental/deploy-systemd/install.sh` should pass before migration PR merge. |
| Live distro validation | Open | No current Debian, Ubuntu, RHEL, or Fedora install evidence is recorded. |
| Hardening review | Open | systemd hardening directives need release-line review. |
| Upgrade and rollback | Open | Upgrade guidance exists, but rollback validation is not recorded. |
| Offline install | Open | Air-gapped install notes exist, but validation is not recorded. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- systemd is not the supported current alpha deployment path.
- Live distro validation is not complete.
- Service hardening, reverse proxy, backup/restore, upgrade/rollback, and
  offline-install behavior are not release-qualified.
