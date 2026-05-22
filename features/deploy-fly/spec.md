# Fly.io Deployment Spec

The Fly.io deployment feature packages Stigmem deployment guidance for Fly
Machines. It is intended for operators who want a starting point for a hosted
single-node alpha deployment while the supported alpha deployment path remains
Docker Compose.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `README.md` | Operator recipe for app creation, persistent volume setup, secrets, deployment, health checks, scale-to-zero, libSQL/Turso, multi-region reads, encryption-at-rest configuration, and metrics. |
| `fly.toml` | Reference Stigmem node configuration with Docker build, SQLite volume mount, health checks, concurrency limits, metrics, optional auth, optional federation, optional libSQL, and optional scale-to-zero comments. |
| `infra-fly.toml` | Hosted-node configuration variant with auth and OIDC enabled by default. |
| `fly.dashboard.toml` | Dashboard deployment configuration with Next.js build args, session/OIDC secret expectations, service ports, and health checks. |
| `STATUS.md` | Legacy status pointer; this feature record owns lifecycle truth after migration. |

## Configuration Areas

| Area | Values |
| --- | --- |
| Build | `node/Dockerfile` for the node and `apps/dashboard/Dockerfile` for the dashboard. |
| Runtime binding | `STIGMEM_HOST`, `STIGMEM_PORT`, Fly service ports, and `/healthz` checks. |
| Persistence | Fly volume `stigmem_data` mounted at `/data` with `STIGMEM_DB_PATH=/data/stigmem.db`. |
| Auth and OIDC | `STIGMEM_AUTH_REQUIRED`, `STIGMEM_OIDC_ENABLED`, issuer, audience, allowed domains, dashboard OIDC client settings. |
| Storage | SQLite by default, optional libSQL/Turso configuration through secrets. |
| Encryption at rest | `STIGMEM_AT_REST_ENCRYPTION` and passphrase-env pointer. |
| Federation | `STIGMEM_FEDERATION_ENABLED` gate for peering scenarios. |
| Metrics | Fly metrics scrape configuration for `:9091/metrics`. |
| Scale-to-zero | Optional Fly Machines auto-stop and auto-start settings. |

## Out of Scope

- Treating Fly.io as the supported alpha deployment path.
- Publishing a managed Fly.io app template or one-click deployment.
- Claiming production readiness before live deployment, backup/restore,
  secrets, auth, and ownership gates complete.
- Guaranteeing multi-region write behavior; the current recipe names
  libSQL/Turso as the multi-region option rather than solving topology
  automatically.

## Spec Assignment

There is no Spec-X assignment for Fly.io deployment. It is an experimental
deployment recipe rather than a protocol-bearing feature.
