# Test Infrastructure Backlog

## Purpose

Track the remaining test-infrastructure follow-up after the current PR gate tightening pass.

## Current State Snapshot

- [x] Python fast gates already run in PR CI:
  - Ruff baseline gate
  - mypy baseline gate
  - node + Python SDK pytest
  - adapter pytest suites
  - `pip-audit`
  - `bandit`
  - constant-time checks
- [x] TypeScript fast gates already run in PR CI:
  - workspace build
  - workspace type-check
  - `stigmem-ts` tests
  - `stigmem-mcp` tests
  - dashboard Vitest tests
  - `pnpm audit`
- [x] PR CI already includes:
  - contract drift checks
  - Go SDK tests
  - docs build
  - Obsidian plugin build + tests
  - Helm lint/template checks
  - container smoke + SBOM checks
  - SDK compatibility smoke
- [x] Main-branch CI already includes:
  - coverage artifact generation
- [x] Separate workflows already exist for:
  - wire conformance
  - multi-backend conformance
  - eval-fast
  - nightly dashboard Playwright
  - nightly migration compatibility
  - nightly backward SDK compatibility
  - nightly quickstart smoke
  - nightly federation soak

## Stale Assumptions Removed

- [x] Dashboard unit tests do exist.
- [x] Dashboard Playwright coverage does exist, but only nightly.
- [x] MCP tests do exist.
- [x] Obsidian plugin tests/build do exist.
- [x] Go SDK tests are CI-blocking already.
- [x] Adapter tests are CI-blocking already.
- [x] Docs build is CI-blocking already.

## Completed In This Pass

- [x] Make recall regressions block on first failure in PR CI.
  - Implemented: `eval/test_recall.py` now fails immediately when the regression threshold is exceeded.

- [x] Enforce `--strict-markers` for the default pytest configuration, not only conformance.
  - Implemented in `pyproject.toml`.

- [x] Make dashboard Playwright smoke PR-blocking for `apps/dashboard/**` changes.
  - Implemented as a path-gated PR CI job.

- [x] Remove or redesign duplicate PR test execution in the coverage job.
  - Implemented: coverage artifact generation now runs on `main` pushes only, not every PR.

- [x] Add path filters to `eval-fast.yml`.
  - Implemented for PRs and pushes.

- [ ] Benchmark the Turbo task graph before changing Node CI orchestration further.
  - `build`, `type-check`, and package tests may overlap through dependency execution.
  - Local benchmarking is not yet trustworthy enough because the current shell environment does not reproduce the CI `pnpm`/`turbo` setup cleanly.
  - No safe simplification is queued until there is timing data showing real duplicate work in a CI-like environment.

- [x] Fix Python adapter test package collisions so adapters can be collected in one pytest invocation.
  - Implemented:
    - removed adapter `tests/__init__.py` package coupling
    - gave adapter suites unique test module filenames
    - widened `adapters/conftest.py` isolation hook
    - collapsed adapter pytest execution into a single repo-root invocation

- [x] Evaluate parallelizing adapter tests further if CI time still justifies it.
  - Decision: do not add more parallelization in this PR.
  - Evidence:
    - `pytest adapters/` currently runs in about `0.36s` locally for `157 passed, 2 skipped`
    - the large win was eliminating repeated pytest startup, which is already done

## Remaining Backlog

### Debt Burn-Down

- [ ] Move Python quality gates from baseline-only to zero-baseline strictness.
  - Already implemented:
    - changed-file strict Ruff enforcement in PR CI
    - changed-file strict mypy enforcement for production Python touched by the PR
    - documented ratchet plan in `tasks/python-quality-ratchet.md`
  - Remaining staged debt:
    - Ruff baseline: 895 entries
    - mypy baseline: 126 entries
  - Candidate rollout shapes:
    - zero-baseline cleanup,
    - changed-files-only strictness plus ratchet,
    - package-by-package zero-baseline rollout.

### Measurement-Driven Optimization

- [ ] Benchmark the Turbo task graph before changing Node CI orchestration further.
  - `build`, `type-check`, and package tests may overlap through dependency execution.
  - CI now captures a `node-check-timings.json` artifact for the main Node gate.
  - No orchestration change is queued until those timings show real duplicate work.

- [ ] Add package-level coverage thresholds only if coverage becomes a merge gate again.
  - Prefer package-scoped thresholds over a single repo-wide threshold.
  - Track line and branch coverage separately.
  - Main-branch coverage now emits a per-package summary.

### Future Contract / Conformance Work

- [ ] Revisit conformance auth-vector handling only if auth-required vectors are added back.
  - Current corpus contains `0` vectors with `"requires_auth": true`.
  - The earlier follow-up is stale for the current corpus.

- [x] Make migration compatibility PR-gated when migration files or storage internals change.
  - Implemented as a path-gated PR CI job.

- [x] Make quickstart smoke PR-gated when Docker/deploy/quickstart surfaces change.
  - Implemented as a path-gated PR CI job.

## Suggested Next Order

- [ ] 1. Define the Python baseline burn-down strategy.
- [ ] 2. Gather CI timing data for Node/Turbo work before changing orchestration.
- [ ] 3. Decide whether coverage should return to the PR path with thresholds or stay main-only.
- [ ] 4. Revisit auth-required conformance only if the vector corpus grows in that direction.

## Review

- Implemented:
  - immediate-fail recall regression gating
  - eval-fast path filtering
  - global pytest strict markers
  - removal of duplicate PR coverage reruns
  - changed-file Python strictness in PR CI
  - aggregate-safe adapter collection and single-invocation adapter pytest
  - PR-gated dashboard Playwright smoke
  - PR-gated migration compatibility
  - PR-gated quickstart smoke
  - Python timeout protection in CI-sensitive pytest runs
  - JUnit/structured test artifacts for Python, Playwright, and migration jobs
  - per-package coverage summary generation
  - documented Python quality ratchet plan
  - CI Node timing artifact capture
- Remaining items are intentionally deferred. There are no obvious immediate PR-blocking infrastructure gaps left from this pass.
