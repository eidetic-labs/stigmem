# Helm Deployment Evidence

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/deploy-helm/helm/stigmem/Chart.yaml` | Chart metadata, chart version, and app version. |
| `experimental/deploy-helm/helm/stigmem/values.yaml` | Default deployment, secret, hardening, and runtime values. |
| `experimental/deploy-helm/helm/stigmem/templates/deployment.yaml` | Deployment template for node env, probes, volumes, security contexts, and scheduling. |
| `experimental/deploy-helm/helm/stigmem/templates/service.yaml` | Service template. |
| `experimental/deploy-helm/helm/stigmem/templates/ingress.yaml` | Optional ingress template. |
| `experimental/deploy-helm/helm/stigmem/templates/pvc.yaml` | Optional PVC template. |
| `experimental/deploy-helm/helm/stigmem/templates/_helpers.tpl` | Chart naming and label helpers. |

## Documentation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/deploy-helm/concept.md` | Operator-facing Helm concept and values overview. |
| `experimental/deploy-helm/helm/README.md` | Install, override, upgrade, uninstall, and federation recipe. |
| `experimental/deploy-helm/STATUS.md` | Legacy status pointer to this feature record. |

## Validation Commands

Use Helm and docs checks:

```bash
helm lint experimental/deploy-helm/helm/stigmem
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

## Missing Evidence

- Live Kubernetes install, upgrade, rollback, and uninstall validation is not
  complete.
- Helm repository publication evidence is not complete.
- Production hardening review evidence is not complete.
