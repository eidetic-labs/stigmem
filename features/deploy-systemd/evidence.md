# systemd Deployment Evidence

This file records evidence for the systemd deployment feature. The current
record is source-inventory and static syntax evidence only; it does not claim
live distro support.

## Source Inventory

| Path | Evidence |
| --- | --- |
| `experimental/deploy-systemd/README.md` | Install, configure/start, smoke test, logs, upgrade, reverse proxy, offline install, and uninstall guidance. |
| `experimental/deploy-systemd/install.sh` | Root installer for user, directories, venv, package install, environment file, and service unit. |
| `experimental/deploy-systemd/.env.example` | Node environment template. |
| `experimental/deploy-systemd/stigmem-node.service` | systemd unit and hardening directives. |
| `experimental/deploy-systemd/STATUS.md` | Legacy pointer after ADR-020 migration. |

## Validation

| Check | Status | Notes |
| --- | --- | --- |
| Feature record validation | Required per PR | `python3 scripts/check_feature_records.py`. |
| Feature projection validation | Required per PR | `python3 scripts/check_feature_projections.py`. |
| Security projection validation | Required per PR | `python3 scripts/check_feature_security_projection.py`. |
| Changelog projection validation | Required per PR | `python3 scripts/check_feature_changelog_projection.py`. |
| Compatibility projection validation | Required per PR | `python3 scripts/check_feature_compatibility_projection.py`. |
| Protocol projection validation | Required per PR | `python3 scripts/check_feature_protocol_projection.py`. |
| Shell syntax | Required per PR | `bash -n experimental/deploy-systemd/install.sh`. |
| Docs build | Required per PR | `CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs`. |

## Open Evidence

- No live distro install evidence is recorded.
- No upgrade/rollback validation is recorded.
- No offline-install validation is recorded.
- No production hardening review evidence is recorded.
- No operator ownership evidence is recorded.
