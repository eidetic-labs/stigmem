# PaaS Deployment Spec

The PaaS deployment feature packages managed-platform deployment recipes for a
single Stigmem node. It is intended for operators who want starting points for
managed container environments while the supported alpha deployment path
remains Docker Compose.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `README.md` | Platform index and cross-platform notes for persistence, secrets, node URL, and port behavior. |
| `render.md` | Render Web Service recipe with Docker settings, persistent disk, environment variables, libSQL/Turso, OIDC, and health check guidance. |
| `railway.md` | Railway GitHub-connected deployment recipe with Docker settings, variables, volume, libSQL/Turso, OIDC, and rollback notes. |
| `aws-app-runner.md` | AWS App Runner recipe with ECR image build/push, Secrets Manager, service creation, health checks, EFS persistence option, autoscaling, and OIDC notes. |
| `gcp-cloud-run.md` | Google Cloud Run recipe with Artifact Registry, Secret Manager, deployment command, Filestore option, OIDC notes, scale-to-zero, and health-check notes. |
| `STATUS.md` | Legacy status pointer; this feature record owns lifecycle truth after migration. |

## Configuration Areas

| Area | Values |
| --- | --- |
| Build | `node/Dockerfile` from the repo root. |
| Runtime binding | `STIGMEM_PORT=8765`, public `STIGMEM_NODE_URL`, and `/healthz` checks. |
| Persistence | Platform volume options for SQLite or stateless libSQL/Turso. |
| Secrets | Platform-native secrets managers or variable stores. |
| Auth and OIDC | `STIGMEM_AUTH_REQUIRED`, `STIGMEM_OIDC_ENABLED`, issuer, audience, and allowed-domain settings. |
| Scaling | Render/Railway platform scaling, App Runner autoscaling, and Cloud Run scale-to-zero. |

## Out of Scope

- Treating PaaS recipes as the supported alpha deployment path.
- Claiming production readiness before live validation on each platform.
- Guaranteeing portable persistence behavior across platforms.
- Providing a managed, one-click, or vendor-certified deployment.

## Spec Assignment

There is no Spec-X assignment for PaaS deployment. It is an experimental
deployment recipe rather than a protocol-bearing feature.
