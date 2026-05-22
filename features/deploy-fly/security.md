# Fly.io Deployment Security

The Fly.io recipe is an experimental deployment surface. Its security posture
depends on Fly edge TLS, secret configuration through `fly secrets`, restrictive
node runtime defaults, safe persistence handling, and operator review before
production use.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Edge TLS | Public service ports use Fly TLS handlers. | `experimental/deploy-fly/fly.toml`; `experimental/deploy-fly/infra-fly.toml`; `experimental/deploy-fly/fly.dashboard.toml` |
| Secrets | OIDC, libSQL, encryption, and dashboard secret values are documented as `fly secrets set` inputs rather than committed config values. | `experimental/deploy-fly/README.md`; `experimental/deploy-fly/fly.dashboard.toml` |
| Node persistence | SQLite state is mounted on a Fly volume at `/data`; `STIGMEM_DB_PATH` points to `/data/stigmem.db`. | `experimental/deploy-fly/fly.toml`; `experimental/deploy-fly/infra-fly.toml` |
| Auth posture | The hosted-node variant enables auth and OIDC by default; the reference variant documents auth as production-required. | `experimental/deploy-fly/infra-fly.toml`; `experimental/deploy-fly/fly.toml` |
| Encryption at rest | Recipe documents enabling Stigmem at-rest encryption with a passphrase stored as a Fly secret. | `experimental/deploy-fly/README.md`; `experimental/deploy-fly/fly.toml` |
| Metrics | Metrics are exposed on the configured metrics port for Fly scraping. | `experimental/deploy-fly/fly.toml`; `experimental/deploy-fly/infra-fly.toml` |

## Security References

No dedicated R-* audit item is assigned to Fly.io deployment. Related auth,
persistence, federation, and container hardening risks live in the public
security docs and threat model.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Live Fly validation has not been recorded.
- The reference node config leaves auth disabled for local experimentation;
  production deployments must enable auth and OIDC.
- Persistent volume backup, restore, and data-retention procedures are not
  validated in this feature record.
- Dashboard session and OIDC secret posture has not completed release-line
  review.
- Multi-region behavior depends on the selected storage backend; SQLite volume
  deployments should not be treated as multi-writer.

## Operator Guidance

- Set OIDC, libSQL, encryption, and dashboard credentials with `fly secrets`;
  do not commit real secret values into Fly config files.
- Enable `STIGMEM_AUTH_REQUIRED` and OIDC before exposing a non-local node.
- Validate backup and restore for any persistent Fly volume before relying on
  the deployment.
- Treat Fly.io as unsupported until future-alpha promotion gates complete.
