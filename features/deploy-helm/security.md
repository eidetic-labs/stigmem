# Helm Deployment Security

The Helm chart is an experimental Kubernetes deployment recipe. Its security
posture depends on secure-by-default auth values, secret references instead of
committed secrets, container hardening defaults, and operator review before
production use.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Auth default | `stigmem.authRequired` defaults to `true`. | `experimental/deploy-helm/helm/stigmem/values.yaml` |
| Secret references | libSQL, at-rest encryption, and federation private keys can be supplied from Kubernetes Secrets. | `experimental/deploy-helm/helm/stigmem/values.yaml`; `experimental/deploy-helm/helm/stigmem/templates/deployment.yaml` |
| Non-root runtime | Pod security context runs as UID/GID `65532` and requires non-root. | `experimental/deploy-helm/helm/stigmem/values.yaml` |
| Read-only root filesystem | Container security context defaults `readOnlyRootFilesystem` to `true` with explicit `/tmp` and `/run` memory volumes. | `experimental/deploy-helm/helm/stigmem/values.yaml`; `experimental/deploy-helm/helm/stigmem/templates/deployment.yaml` |
| Capabilities | Container drops all Linux capabilities. | `experimental/deploy-helm/helm/stigmem/values.yaml` |
| Seccomp | Pod security context uses `RuntimeDefault`. | `experimental/deploy-helm/helm/stigmem/values.yaml` |

## Security References

No dedicated R-* audit item is assigned to Helm deployment. Related container
hardening guidance lives in the public security docs.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Inline secret values remain possible for local experimentation; production
  operators should use Kubernetes Secrets or an external secrets manager.
- `RuntimeDefault` seccomp may be weaker than a locally loaded Stigmem-specific
  profile.
- Live cluster validation and production hardening review are not complete.
- Mutable image tags should be replaced with digests for production use.

## Operator Guidance

- Use Kubernetes Secrets for federation private keys, libSQL tokens, and
  encryption passphrases.
- Pin production images by digest rather than mutable tags.
- Review ingress, TLS, auth, resource limits, and seccomp posture before any
  production deployment.
- Treat Helm as unsupported until future-alpha promotion gates complete.
