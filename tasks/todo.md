# Test Infrastructure Backlog

## Purpose

Track the remaining test-infrastructure follow-up after the merged PR gate tightening pass on `main`.

## Current State Snapshot

- [x] Python fast gates already run in PR CI:
  - Ruff baseline gate
  - mypy baseline gate
  - changed-file strict Ruff gate
  - changed-file strict mypy gate for touched production Python
  - node + Python SDK pytest
  - adapter pytest suites
  - `pip-audit`
  - `bandit`
  - constant-time checks
  - timeout-protected pytest runs with JUnit artifacts
- [x] TypeScript fast gates already run in PR CI:
  - workspace build
  - workspace type-check
  - `stigmem-ts` tests
  - `stigmem-mcp` tests
  - dashboard Vitest tests
  - `pnpm audit`
  - timing artifact capture for the main Node gate
- [x] PR CI already includes:
  - contract drift checks
  - Go SDK tests
  - docs build
  - Obsidian plugin build + tests
  - Helm lint/template checks
  - container smoke + SBOM checks
  - SDK compatibility smoke
  - dashboard Playwright smoke
  - schema migration compatibility
  - quickstart Docker smoke
- [x] Main-branch CI already includes:
  - coverage artifact generation
  - per-package coverage summary generation
- [x] Separate workflows already exist for:
  - wire conformance
  - multi-backend conformance
  - eval-fast
  - nightly dashboard Playwright
  - nightly migration compatibility
  - nightly backward SDK compatibility
  - nightly quickstart smoke
  - nightly federation soak
- [x] Required status checks on `main` now include:
  - `Detect changed surfaces`
  - `Python checks (lint + type + tests + security)`
  - `TypeScript checks (SDK + MCP + dashboard)`
  - `Contract checks (OpenAPI + generated SDK)`
  - `SDK compatibility smoke`
  - `Go SDK tests`
  - `Docs build`
  - `Obsidian plugin build`
  - `Dashboard Playwright smoke`
  - `Schema migration compatibility`
  - `Quickstart Docker smoke`
  - `Helm chart lint`
  - `Container hardening smoke test`
  - `Docs drift watchdog`
  - `CodeQL`
  - `Eval harness (adversarial + recall, ≤5 min)`

## Stale Assumptions Removed

- [x] Dashboard unit tests do exist.
- [x] Dashboard Playwright coverage is PR-gated and also runs nightly.
- [x] MCP tests do exist.
- [x] Obsidian plugin tests/build do exist.
- [x] Go SDK tests are CI-blocking already.
- [x] Adapter tests are CI-blocking already.
- [x] Docs build is CI-blocking already.
- [x] Eval-fast is safe to require because it now always triggers and path-gates at the job level.

## Completed In This Pass

- [x] Gather real timing data for the current PR gates before changing CI structure.
  - Evidence collected:
    - recent CI artifact: Node gate `build` ≈ `44.3s`, all Node tests + type-check combined ≈ `12.3s`
    - recent GitHub Actions job times: eval-fast end-to-end ≈ `21–26s`
    - local timing artifact from `scripts/check.sh python`: core pytest ≈ `115.3s`, `pip-audit` ≈ `9.1s`, everything else sub-second to low-single-digit seconds
  - Implemented:
    - Python CI now emits `artifacts/python-check-timings.json`
    - eval-fast now emits `artifacts/eval-fast-timings.json`

- [x] Decide whether Node, Python, or eval-fast should be structurally split now.
  - Decision:
    - keep the Node gate unified
    - keep the Python gate unified
    - keep eval-fast as a single required job
  - Rationale:
    - Node cost is dominated by `pnpm build`, not duplicated tests
    - Python cost is dominated by the core pytest invocation, not lint/security sidecars
    - eval-fast is already short enough that further splitting would add more overhead than value

- [x] Make recall regressions block on first failure in PR CI.
  - Implemented: `eval/test_recall.py` now fails immediately when the regression threshold is exceeded.

- [x] Enforce `--strict-markers` for the default pytest configuration, not only conformance.
  - Implemented in `pyproject.toml`.

- [x] Make dashboard Playwright smoke PR-blocking for `apps/dashboard/**` changes.
  - Implemented as a path-gated PR CI job.

- [x] Remove or redesign duplicate PR test execution in the coverage job.
  - Implemented: coverage artifact generation now runs on `main` pushes only, not every PR.

- [x] Make `eval-fast.yml` required-check-safe.
  - Implemented:
    - workflow always triggers on PRs and selected pushes
    - `Detect eval surfaces` path filter gates the eval job itself
    - `Eval harness (adversarial + recall, ≤5 min)` is now a required status check on `main`

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

- [x] Start the Python baseline burn-down with a package-level ratchet.
  - Implemented:
    - `sdks/stigmem-py` is now zero-baseline clean under strict Ruff + mypy
    - `scripts/check.sh python` now enforces strict Ruff + mypy on `sdks/stigmem-py`
    - committed Ruff baseline reduced from `881` to `872` entries
  - Remaining debt is now concentrated in:
    - `node/` for almost all mypy debt and most Ruff debt
    - `adapters/` for the remaining non-`node` Ruff debt

- [x] Decide whether coverage should return to the PR path now.
  - Decision: keep coverage main-only for now.
  - Rationale:
    - required PR checks are already broad
    - current timing data does not justify reintroducing duplicate PR execution
    - package-level thresholds should wait until per-package trends have stabilized on `main`

- [x] Clear GitHub-identified npm security alerts in committed manifests/locks.
  - Implemented:
    - upgraded Obsidian plugin `esbuild` to a patched line and regenerated `package-lock.json`
    - pinned the docs tree’s vulnerable nested `openapi-to-postmanv2 -> js-yaml` lock entry to `4.1.1`
  - Verification:
    - `npm audit --package-lock-only --json` is clean for both `docs/` and `adapters/obsidian-plugin/`

- [x] Consolidate branch-protection ownership and clean up workflow runtime drift.
  - Implemented:
    - classic branch protection on `main` now owns only required status checks
    - the `Require PR for main` ruleset remains the single owner for PR review and merge-method policy
    - GitHub Actions versions were refreshed across workflow files to current majors for the action families in use
    - Go setup now points its cache key at `sdks/stigmem-go/go.mod`

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

- [ ] Revisit Node orchestration only if future `node-check-timings.json` artifacts show `pnpm build` can be reduced without losing coverage.
  - Current evidence says the gate is build-dominated, not test-duplication-dominated.

- [ ] Revisit eval-fast setup only if future `eval-fast-timings.json` artifacts show `uv sync --all-packages` dominates the job materially.
  - Current end-to-end runtime is short enough that no structural change is justified yet.

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

- [ ] 1. Continue the Python baseline burn-down, starting with the remaining adapter Ruff debt.
- [ ] 2. Watch future Node and eval timing artifacts before changing orchestration again.
- [ ] 3. Decide whether coverage should become contractual only after per-package trend data accumulates on `main`.
- [ ] 4. Revisit auth-required conformance only if the vector corpus grows in that direction.

## Review

- Implemented:
  - immediate-fail recall regression gating
  - required-check-safe eval-fast topology
  - global pytest strict markers
  - removal of duplicate PR coverage reruns
  - changed-file Python strictness in PR CI
  - Python and eval timing artifacts for future CI decisions
  - zero-baseline strictness for `sdks/stigmem-py`
  - aggregate-safe adapter collection and single-invocation adapter pytest
  - PR-gated dashboard Playwright smoke
  - PR-gated migration compatibility
  - PR-gated quickstart smoke
  - Python timeout protection in CI-sensitive pytest runs
  - JUnit/structured test artifacts for Python, Playwright, and migration jobs
  - per-package coverage summary generation
  - documented Python quality ratchet plan
  - CI Node timing artifact capture
  - required-check-safe eval gating on `main`
  - direct fixes for the two open GitHub Dependabot alerts in committed npm manifests/locks
  - removal of duplicate PR policy between classic branch protection and the `main` ruleset
- Remaining items are intentionally deferred. There are no obvious immediate PR-blocking infrastructure gaps left from this pass; the next work is mostly incremental Python debt burn-down and watching the new timing/coverage signals for a few runs before changing CI structure again.
