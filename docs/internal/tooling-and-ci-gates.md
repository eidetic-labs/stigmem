# Tooling and CI Gates — Best Practices

> Codifies the local/CI pattern Stigmem is already using: one local entrypoint, package-specific lanes, path-filtered CI, contract drift checks, and nightly reliability gates.

## Core Rule

Every CI gate should be reproducible locally through a script in `scripts/`. GitHub Actions may select when to run a gate, install toolchains, and upload artifacts, but the actual check logic belongs in the repository.

## Required Local Entrypoint

Maintain one PR-equivalent command:

```bash
bash scripts/check.sh all
```

Maintain focused lanes for common work surfaces:

```bash
bash scripts/check.sh python
bash scripts/check.sh node
bash scripts/check.sh contract
bash scripts/check.sh go
bash scripts/check.sh docs
bash scripts/check.sh obsidian
```

When a new package surface is added, it must either join an existing lane or get a new lane before it is considered supported.

## Toolchain Prerequisites

`CONTRIBUTING.md` should name the supported local toolchain:

- Python 3.11
- `uv`
- Node 20
- `pnpm` through Corepack or the pinned package manager
- Go, if Go packages have dependencies or tests
- Docker, for container and quickstart smoke checks
- Helm, when Helm charts are in scope
- npm, when packages sit outside the pnpm workspace

## Path-Filtered CI Governance

Path filters are part of the architecture, not incidental CI plumbing. Every file move, package addition, or experimental extraction must update:

- `.github/workflows/ci.yml` path filters
- `scripts/check.sh`
- workspace manifests (`pnpm-workspace.yaml`, `pyproject.toml`, `turbo.json`)
- artifact paths for coverage, Playwright, SDK compatibility, and soak results

Review checklist:

- Does this PR add or move a package?
- Does CI still run when files under that package change?
- Does default CI intentionally skip `experimental/`?
- Is there a manual or scheduled job for skipped experimental checks?

## Contract Drift Gates

Protocol repositories need contract drift checks as first-class gates:

- FastAPI-generated OpenAPI is the canonical API artifact.
- `docs/openapi/stigmem.json` is committed and diff-checked.
- Generated SDK files are regenerated and diff-checked.
- OpenAPI metadata participates in version-consistency checks.
- CI fails if committed generated artifacts differ from generator output.

Generated files must carry an `AUTO-GENERATED` marker and name their generator command.

## Reliability Gates

PR gates should stay fast. Nightly/manual gates should cover expensive realism:

- docs build artifact
- quickstart smoke
- browser smoke / Playwright report
- SDK backward compatibility report
- schema migration compatibility
- federation soak artifacts
- container SBOM and seccomp validation

Every nightly artifact should have a retention window and an owner who knows how to read it.

## Dependency and Security Gates

Run vulnerability checks separately from currency checks:

- Vulnerability: `pip-audit`, `pnpm audit`, container SBOM/audit tooling.
- Currency: package-manager outdated checks and major-version hold review.

A package can be vulnerability-clean and still stale enough to be a maintenance risk.

## Branch and Publish Verification

Before pushing or publishing:

1. Confirm `git rev-parse --show-toplevel`.
2. Confirm `git status --short --branch`.
3. Confirm target branch (`main`, review branch, release branch).
4. Fetch and compare ahead/behind.
5. Push the branch the reviewer expects.
6. Verify the live remote with `git ls-remote`.

This prevents review-branch updates from being mistaken for main-branch updates.
