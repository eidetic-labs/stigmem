# PaaS Deployment Security

The PaaS recipe set is an experimental deployment surface. Its security posture
depends on platform-native secret stores, HTTPS ingress, auth and OIDC
configuration, safe persistence choices, and review of platform networking
before production use.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Secrets | Guides direct operators to platform secret stores or variable managers rather than committed secrets. | `experimental/deploy-paas/README.md`; platform guides |
| Auth | Guides recommend `STIGMEM_AUTH_REQUIRED=true` and include OIDC settings. | `experimental/deploy-paas/render.md`; `experimental/deploy-paas/railway.md`; `experimental/deploy-paas/aws-app-runner.md`; `experimental/deploy-paas/gcp-cloud-run.md` |
| Persistence | Guides distinguish ephemeral containers from persistent volumes and recommend libSQL/Turso for stateless workloads. | `experimental/deploy-paas/README.md`; platform guides |
| Health checks | Guides point platform health checks at `/healthz`. | `experimental/deploy-paas/render.md`; `experimental/deploy-paas/aws-app-runner.md`; `experimental/deploy-paas/gcp-cloud-run.md` |
| Public URL | Guides require `STIGMEM_NODE_URL` to match the public HTTPS platform URL. | `experimental/deploy-paas/README.md`; platform guides |

## Security References

No dedicated R-* audit item is assigned to PaaS deployment. Related auth,
persistence, federation, and container hardening risks live in the public
security docs and threat model.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Live platform validation has not been recorded.
- Public platform ingress may expose a node if auth/OIDC is not configured
  correctly.
- Platform volumes and network attachments differ materially; persistence and
  backup/restore behavior must be validated per platform.
- Cloud provider IAM, service-account, VPC, and secret-access scopes are
  operator-owned in the current alpha line.
- Autoscaling and scale-to-zero can affect latency, quota behavior, and storage
  backend assumptions.

## Operator Guidance

- Enable `STIGMEM_AUTH_REQUIRED` and OIDC before exposing a non-local node.
- Use platform-native secret stores for OIDC, libSQL, and encryption material.
- Prefer libSQL/Turso for stateless scale-to-zero platforms unless platform
  volume semantics have been validated.
- Treat PaaS deployment as unsupported until future-alpha promotion gates
  complete.
