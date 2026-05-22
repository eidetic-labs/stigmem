# PaaS Deployment Evidence

This file records evidence for the PaaS deployment feature. The current record
is source-inventory and documentation evidence only; it does not claim live
platform support.

## Source Inventory

| Path | Evidence |
| --- | --- |
| `experimental/deploy-paas/README.md` | Platform index and common notes. |
| `experimental/deploy-paas/render.md` | Render Web Service recipe. |
| `experimental/deploy-paas/railway.md` | Railway deployment recipe. |
| `experimental/deploy-paas/aws-app-runner.md` | AWS App Runner deployment recipe. |
| `experimental/deploy-paas/gcp-cloud-run.md` | Google Cloud Run deployment recipe. |
| `experimental/deploy-paas/STATUS.md` | Legacy pointer after ADR-020 migration. |

## Validation

| Check | Status | Notes |
| --- | --- | --- |
| Feature record validation | Required per PR | `python3 scripts/check_feature_records.py`. |
| Feature projection validation | Required per PR | `python3 scripts/check_feature_projections.py`. |
| Security projection validation | Required per PR | `python3 scripts/check_feature_security_projection.py`. |
| Changelog projection validation | Required per PR | `python3 scripts/check_feature_changelog_projection.py`. |
| Compatibility projection validation | Required per PR | `python3 scripts/check_feature_compatibility_projection.py`. |
| Protocol projection validation | Required per PR | `python3 scripts/check_feature_protocol_projection.py`. |
| Docs build | Required per PR | `CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs`. |

## Open Evidence

- No live Render, Railway, AWS App Runner, or Google Cloud Run deployment
  evidence is recorded.
- No platform persistence backup and restore validation is recorded.
- No platform-specific security review evidence is recorded.
- No operator ownership evidence is recorded.
