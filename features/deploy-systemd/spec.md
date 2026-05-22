# systemd Deployment Spec

The systemd deployment feature packages a bare-metal Linux deployment recipe
for a single Stigmem node. It is intended for operators who want an
experimental non-container path while the supported alpha deployment path
remains Docker Compose.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `README.md` | Operator recipe for install, configuration, start, smoke test, logs, upgrade, reverse proxy, offline install, and uninstall. |
| `install.sh` | Root installer that creates a service user, install/data directories, Python venv, environment file, systemd unit, and enabled service. |
| `.env.example` | Environment template for node URL, networking, storage, libSQL, encryption, auth/OIDC, federation, trust, sanitizer, and logging settings. |
| `stigmem-node.service` | systemd unit with local bind defaults, data write path, restart behavior, journald logging, and hardening directives. |
| `STATUS.md` | Legacy status pointer; this feature record owns lifecycle truth after migration. |

## Configuration Areas

| Area | Values |
| --- | --- |
| Runtime | Python 3.11+, `stigmem-node`, `/opt/stigmem/venv/bin/stigmem-node`. |
| User and paths | System user `stigmem`, install path `/opt/stigmem`, data path `/var/lib/stigmem`. |
| Network | Default bind `127.0.0.1:8765`; reverse proxy recommended for public HTTPS. |
| Storage | SQLite by default at `/var/lib/stigmem/stigmem.db`; optional libSQL/Turso variables. |
| Auth and OIDC | Environment switches for auth-required mode and OIDC issuer/audience/domain settings. |
| Federation | Environment switches for federation and key material. |
| Hardening | `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`, `ProtectHome=true`, and `ReadWritePaths=/var/lib/stigmem`. |
| Offline install | Wheel download and `STIGMEM_OFFLINE=1` path for air-gapped hosts. |

## Out of Scope

- Treating systemd as the supported alpha deployment path.
- Claiming live validation across Debian, Ubuntu, RHEL, and Fedora before
  release-line evidence exists.
- Guaranteeing production hardening before service-unit, reverse-proxy,
  firewall, auth, backup, and upgrade/rollback review.
- Replacing OS-specific package management or host hardening procedures.

## Spec Assignment

There is no Spec-X assignment for systemd deployment. It is an experimental
deployment recipe rather than a protocol-bearing feature.
