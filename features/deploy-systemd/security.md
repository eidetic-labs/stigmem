# systemd Deployment Security

The systemd recipe is an experimental deployment surface. Its security posture
depends on local-only binding by default, reverse-proxy TLS, protected
environment files, least-privilege service users, systemd hardening, and
operator review before production use.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Service identity | Installer creates a dedicated `stigmem` system user with no login shell. | `experimental/deploy-systemd/install.sh` |
| Environment file | Installer creates `/opt/stigmem/.env` with mode `600` and service-user ownership when absent. | `experimental/deploy-systemd/install.sh`; `experimental/deploy-systemd/.env.example` |
| Network exposure | Service binds to `127.0.0.1` by default and README recommends Caddy or nginx for public HTTPS. | `experimental/deploy-systemd/stigmem-node.service`; `experimental/deploy-systemd/README.md` |
| Writable paths | Service unit restricts writes to `/var/lib/stigmem`. | `experimental/deploy-systemd/stigmem-node.service` |
| systemd hardening | Unit sets `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`, and `ProtectHome=true`. | `experimental/deploy-systemd/stigmem-node.service` |
| Auth and OIDC | Environment template includes auth and OIDC switches. | `experimental/deploy-systemd/.env.example` |

## Security References

No dedicated R-* audit item is assigned to systemd deployment. Related auth,
persistence, federation, host hardening, and container/non-container deployment
risks live in the public security docs and threat model.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Live distro validation has not been recorded.
- The environment template defaults auth to disabled for local setup; public
  deployments must enable auth/OIDC and reverse-proxy TLS.
- Host firewall, OS patching, backup/restore, certificate management, log
  retention, and intrusion detection are operator-owned in the current alpha
  line.
- Hardening directives have not completed release-line review.
- Offline install and upgrade/rollback procedures have not been validated.

## Operator Guidance

- Keep the node bound to `127.0.0.1` unless a reviewed network exposure plan is
  in place.
- Put Caddy, nginx, or equivalent TLS termination in front of public nodes.
- Set `STIGMEM_AUTH_REQUIRED=true` and configure OIDC before exposing a node.
- Keep `/opt/stigmem/.env` mode `600` and avoid placing secrets in shell
  history or shared logs.
- Treat systemd deployment as unsupported until future-alpha promotion gates
  complete.
