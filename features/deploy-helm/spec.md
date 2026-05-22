# Helm Deployment Spec

The Helm deployment feature packages a single Stigmem node as an experimental
Kubernetes chart. It is intended for platform engineers who want a starting
point for Kubernetes deployments while the supported alpha deployment path
remains Docker Compose.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `helm/stigmem/Chart.yaml` | Helm chart metadata, chart version, and app version. |
| `helm/stigmem/values.yaml` | Default image, service, ingress, persistence, Stigmem env, secret-reference, security-context, probe, resource, and scheduling values. |
| `helm/stigmem/templates/deployment.yaml` | Deployment manifest with Stigmem env vars, secret refs, probes, volumes, and hardening contexts. |
| `helm/stigmem/templates/service.yaml` | Cluster service for the node. |
| `helm/stigmem/templates/ingress.yaml` | Optional ingress surface. |
| `helm/stigmem/templates/pvc.yaml` | Optional persistent volume claim for SQLite/local transparency log state. |
| `helm/README.md` | Operator recipe for install, override, upgrade, uninstall, and federation patterns. |
| `concept.md` | Public-facing deployment concept and values overview. |

## Configuration Areas

| Area | Values |
| --- | --- |
| Image | `image.repository`, `image.tag`, `image.pullPolicy`. |
| Service and ingress | `service.*`, `ingress.*`. |
| Persistence | `persistence.*`, mounted at the Stigmem DB path. |
| Auth and OIDC | `stigmem.authRequired`, `stigmem.oidc*`. |
| Storage | `stigmem.storageBackend`, SQLite path, libSQL URL, and libSQL secret refs. |
| Encryption at rest | `stigmem.atRest*`, `atRestEncryptionSecret.*`. |
| Federation | `stigmem.federation*`, `federationKeypairSecret.*`. |
| Trust and sanitizer | `stigmem.trustMode`, `stigmem.sanitizerMode`, `stigmem.sourceAttestationMode`, `stigmem.attestationRequired`. |
| Hardening | `podSecurityContext`, `containerSecurityContext`, `tmp` and `run` memory volumes. |

## Out of Scope

- Treating the chart as the supported alpha deployment path.
- Publishing or versioning a Helm repository artifact.
- Multi-node topology automation beyond operator-managed multiple releases.
- Production endorsement before ADR-008 reintroduction gates complete.

## Spec Assignment

There is no Spec-X assignment for Helm deployment. It is an experimental
deployment recipe rather than a protocol-bearing feature.
