# Cross-Phase Evidence Maintenance

This document is the owner/trigger map for Stigmem's recurring evidence
maintenance. It complements the detailed runbooks in:

- `docs/internal/dependency-currency.md`
- `docs/internal/security-evidence-registry.md`
- `docs/internal/release-cadence.md`
- `docs/internal/major-version-holds.md`

## Maintenance Matrix

| Control | Owner | Trigger | Artifact | Mechanical check |
|---|---|---|---|---|
| Dependency currency | Maintainers | Weekly Monday workflow; before every release candidate; after relevant ecosystem advisories | `dependency-currency-*` workflow artifact and any dated scan report under `docs/internal/` | `.github/workflows/dependency-currency.yml` |
| Major-version holds | Maintainers | Start of each phase; before every release candidate; whenever an intentional hold changes | `docs/internal/major-version-holds.md` | `scripts/check_evidence_maintenance.py` verifies the register exists and is referenced |
| Security evidence registry | Maintainers and reviewers for the mitigating PR | Same PR that moves a threat-model risk to `Mitigated`; quarterly path drift sweep | `spec/security/evidence-registry.json` | `scripts/validate_security_evidence.py` in CI |
| Per-feature security docs | Feature owner | Any experimental feature security delta; ADR-008 gate 1 | `experimental/<feature>/security.md` and threat-model cross-reference | `scripts/check_security_documentation.py` in CI |
| Release security artifacts | Release owner | Every tagged release and every release-candidate readiness review | risk-count summary, threat-model status header, `CHANGELOG.md` `### Security` subsection when security state changed, SBOM/signature verification evidence where applicable | `scripts/check_evidence_maintenance.py` verifies the release runbook names these steps |

## Disposition Rules

Every dependency-currency row gets one disposition:

- **update now** — patch/minor or security-sensitive update with low migration risk;
- **evaluate in compatibility PR** — meaningful API/runtime migration that needs a
  focused branch;
- **hold with rationale** — intentional major-version hold recorded in
  `docs/internal/major-version-holds.md` with owner and review date;
- **lockfile-confirm latest** — manifest looks behind but the lockfile already
  resolves to the intended/latest compatible version.

Every security-evidence change gets one review decision:

- **accept** — implementation, tests, docs, and version evidence are sufficient;
- **patch** — mitigation is present but needs a follow-up before release exit;
- **replace** — mitigation is not acceptable and the risk remains open or in review.

## Release-Candidate Gate

Before any release-candidate tag:

1. Run the dependency-currency workflow or local equivalent.
2. Disposition all security-sensitive stale dependencies.
3. Review every major-version hold row and update stale review dates.
4. Run:

   ```bash
   python3 scripts/check_evidence_maintenance.py
   python3 scripts/validate_security_evidence.py
   python3 scripts/check_security_documentation.py
   ```

5. Confirm `CHANGELOG.md` has a `### Security` subsection when security work or
   risk-status changes landed in the release.
6. Confirm release notes link to SBOM/signature verification evidence for the
   artifacts being published.

## Quarterly Drift Sweep

Once per quarter, run the evidence validators and inspect:

- all registry paths still exist;
- `version_introduced` values match release vocabulary;
- threat-model mitigated risks still have registry entries;
- dependency hold review dates are not stale;
- release-cadence docs still match the actual publish workflow.
