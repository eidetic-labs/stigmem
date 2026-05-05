# Test Architecture Planning

## Checklist

- [x] Review project instructions and prior lessons.
- [x] Inventory repository languages, packages, and configured quality tools.
- [x] Inspect existing test suites and fixtures.
- [x] Identify coverage gaps and architectural risks.
- [x] Compare practical test architecture options.
- [x] Recommend an implementation plan and verification gates.

## Notes

- `tasks/lessons.md` was not present at session start, so there were no prior lessons to apply.
- This task is planning and architecture analysis only; no production code changes are expected.

## Current State

- Monorepo technologies:
  - Python 3.11 FastAPI reference node in `node/`.
  - Python SDK in `sdks/stigmem-py/`.
  - TypeScript SDK in `sdks/stigmem-ts/`.
  - Go SDK in `sdks/stigmem-go/`.
  - Next.js dashboard in `apps/dashboard/`.
  - TypeScript MCP adapter in `adapters/mcp/`.
  - Obsidian plugin in `adapters/obsidian-plugin/`.
  - Python adapters under `adapters/`.
  - Docusaurus docs under `docs/`.
  - Docker, Helm, Grafana, Prometheus, and soak/eval infrastructure.
- Existing tests and gates:
  - `node/tests/`: broad FastAPI/TestClient behavioral coverage, roughly 874 test declarations across 45 files.
  - `node/src/stigmem_conformance/tests/`: reusable multi-backend conformance suite, roughly 70 test declarations across 8 files.
  - `data/conformance/v1.0/`: 40 wire conformance vectors.
  - `eval/`: 79 adversarial scenarios plus 400 recall probes.
  - `adapters/`: roughly 159 Python adapter test declarations across 10 files.
  - `sdks/stigmem-py/tests/`: 14 Python SDK tests.
  - `sdks/stigmem-ts/tests/`: 18 TypeScript SDK tests.
  - `sdks/stigmem-go/`: 15 Go SDK tests.
  - CI currently runs Python node + Python SDK pytest, pip-audit, bandit, constant-time lint, TS SDK/MCP/dashboard type-check through pnpm/turbo, TS SDK tests, Helm lint/template, container hardening smoke, conformance workflow, eval-fast workflow, nightly federation soak, and publish builds.
- Important gaps:
  - Python mypy and ruff are configured but not currently CI-blocking.
  - Go SDK tests are present but not CI-blocking.
  - Python adapter tests are documented but not CI-blocking.
  - Dashboard has strict TypeScript and build scripts but no unit/component/E2E test suite found.
  - MCP has a Vitest script but no `.test.ts` tests found; only `tests/smoke.sh`.
  - Obsidian plugin has TypeScript build but no test script or tests found.
  - Docs have a build script but no CI docs build found.
  - Root pnpm workspaces exclude `docs/` and `adapters/obsidian-plugin/`.
  - `docs/openapi/stigmem.json` looks stale relative to the current backend and SDK shapes: it reports old app/spec metadata, exposes only 10 paths / 12 operations, and does not match the tagged `{type, v}` `FactValue` model used by the node and SDKs.
  - `sdks/stigmem-ts/package.json` has a `generate` script for `src/generated.ts`, but `sdks/stigmem-ts/src/generated.ts` is not present.
  - Coverage tooling is installed/configured, but no coverage reporting or threshold appears to be CI-blocking.

## Option A: Static Gate First

Build the first architecture around type checks, linting, and the existing fast tests.

What we would use:
- `mypy --strict` for `node/src` and `sdks/stigmem-py/src`.
- `ruff check` for Python source and tests.
- Existing `pnpm type-check` / `tsc --noEmit` for `sdks/stigmem-ts`, `adapters/mcp`, and `apps/dashboard`.
- Add direct build/type checks for `adapters/obsidian-plugin`.
- `go test ./...` and optionally `go vet ./...` for `sdks/stigmem-go`.
- Existing `pytest` and `vitest` suites as fast feedback.

Pros:
- Low implementation cost.
- Directly addresses the collaborator request for type checks.
- Finds many regressions before runtime tests start.
- Good fit for a polyglot monorepo with several shallow SDK/adapters.

Cons:
- Does not prove API/SDK compatibility.
- Does not cover dashboard behavior.
- Strict Python mypy may need a staged rollout with a baseline because the test fixtures rely on patched globals and several dynamic integrations.
- Tooling is currently inconsistent locally unless `uv`, Go, and pnpm dependencies are installed.

Best use:
- Make this the first milestone. It is the cheapest way to raise the floor.

## Option B: Contract-Centric Architecture

Make the API contract the spine of the test system, then test the node, SDKs, adapters, and docs against it.

What we would use:
- Generate OpenAPI from the FastAPI app (`create_app().openapi()`) as the canonical API artifact.
- Add a drift check that fails when generated OpenAPI differs from `docs/openapi/stigmem.json`.
- Use the existing `data/conformance/v1.0/` vectors for normative wire behavior.
- Expand conformance vectors for newer endpoints such as recall, cards, subscriptions, tombstones, audit, identity, and async jobs.
- Add SDK contract tests that replay shared fixtures against TS/Python/Go request/response shapes.
- Consider Schemathesis or OpenAPI response validation after the OpenAPI source of truth is corrected.

Pros:
- Best fit for Stigmem because the project is a protocol plus multiple SDKs/adapters.
- Catches spec/API/SDK/docs drift, which is already visible.
- Gives external implementers a clear compatibility target.
- Turns conformance from a backend-only asset into a release-quality artifact.

Cons:
- Requires resolving the stale OpenAPI/source-of-truth problem first.
- More design work than simply adding tests.
- Contract tests can become noisy if the API is still moving quickly.

Best use:
- Make this the second milestone, after static gates. It has the highest long-term value.

## Option C: Full Test Pyramid

Build a conventional layered suite across backend, SDKs, adapters, dashboard, and deployment.

What we would use:
- Backend unit tests for pure helpers and state machines.
- Backend HTTP behavior tests via FastAPI `TestClient`.
- Storage integration tests for SQLite, libSQL, and Postgres.
- Contract/conformance tests from Option B.
- SDK unit tests with mocked HTTP plus live-node smoke tests.
- Dashboard unit/component tests with Vitest + React Testing Library.
- Dashboard E2E smoke tests with Playwright against a local dashboard and node.
- Docker Compose smoke tests using existing `scripts/quickstart-verify.sh`.

Pros:
- Most balanced architecture.
- Gives each package an appropriate test level instead of overloading backend pytest.
- Makes dashboard and adapter regressions visible.
- Easier to run fast checks on PRs and slower checks on merge/nightly.

Cons:
- Higher setup cost.
- Requires new test dependencies for dashboard/component/E2E testing.
- Needs marker/filter discipline to keep PR checks fast.

Best use:
- Adopt as the target architecture, implemented in phases.

## Option D: Release Matrix / Reliability Architecture

Keep PR checks lean but make release/nightly gates rigorous across deployment, federation, eval, and security.

What we would use:
- Existing multi-backend conformance workflow.
- Existing eval-fast PR workflow and nightly 1-hour federation soak.
- Existing container hardening smoke, SBOM, Helm lint/template checks.
- Add docs build, dashboard image smoke, Go SDK test, adapter suite, and quickstart smoke.
- Add a release checklist that requires static gates, contract drift checks, conformance reports, eval reports, and container/deploy checks.

Pros:
- Good fit for operator-facing infrastructure software.
- Keeps expensive checks out of the inner development loop.
- Builds confidence in real deployment paths.

Cons:
- Does not replace fast local/PR tests.
- Failures can be slower to diagnose.
- Requires CI minutes and artifact hygiene.

Best use:
- Use this as the release/nightly layer after Options A-C are in place.

## Recommendation

Given the added assumption that Stigmem is intended to be a long-term project with more collaborators and users, use a hybrid architecture but tighten the priorities: Option A is still the first implementation step, Option B becomes mandatory rather than optional, Option C becomes the steady-state architecture, and Option D becomes the release/reliability layer.

The key change is that this is no longer just about catching regressions. The test system should make the repository contributor-safe, API-compatible over time, and predictable for external users.

Compatibility policy:
- Use API path versions, package SemVer, and spec versions together.
- The current code is the starting baseline for compatibility planning.
- Strict backward compatibility is not required for the current state, but every release after the baseline must have a clear forward migration path.
- Breaking changes are allowed only with explicit versioning, migration guidance, and a two-minor-release deprecation window.
- Old SDK versions should be tested against newer server versions in nightly/release compatibility jobs.
- Public conformance is not required yet because third-party implementations are not expected immediately, but conformance should be structured so it can become public later.

Coverage policy:
- Aim for 100% coverage as an architectural goal.
- Track both line and branch coverage.
- Optimize for behavioral coverage of public contracts, auth boundaries, storage/migration behavior, and SDK/API compatibility.
- Do not enforce repo-wide 100% immediately; start with reporting, add package-level thresholds, then ratchet upward.
- Require very high or 100% coverage for new small modules, pure logic, security-sensitive code, and migration helpers where practical.

Recommended phases:

1. Static/type-check baseline:
   - Add CI steps for `ruff check`, `mypy`, Go tests, adapter tests, Obsidian plugin build, docs build, and dashboard build/type-check.
   - Keep Python mypy strict, but allow a short staged rollout if the current baseline is too noisy.
   - Add a `make check` or `scripts/check.sh` entrypoint that mirrors PR gates.

2. Contributor-safe local workflow:
   - Provide one documented local command for fast PR-equivalent checks.
   - Add package-specific commands for focused work: backend, SDKs, adapters, dashboard, docs, deploy.
   - Make failures actionable for new contributors by avoiding hidden environment assumptions.
   - Document required local tools: `uv`, Python 3.11, pnpm/Corepack, Node 20, Go 1.22, Docker, Helm.

3. Test taxonomy:
   - Add pytest markers: `unit`, `integration`, `conformance`, `postgres`, `libsql`, `docker`, `eval`, `slow`, `network`.
   - Make PR default `unit + fast integration`.
   - Keep Postgres/libSQL/docker/eval/soak separated into matrix or scheduled jobs.
   - Add `--strict-markers` once markers are assigned.

4. Contract source of truth:
   - Use FastAPI-generated OpenAPI for wire schema, versioned conformance vectors for behavior, and spec markdown for human semantics.
   - Add a committed OpenAPI artifact drift check.
   - Fix `docs/openapi/stigmem.json` and the TS SDK generation script so they agree.
   - Expand vectors for newer endpoints and remove auth vector skips by creating a dedicated auth-enabled vector runner.
   - Treat conformance vectors as a compatibility promise, not only internal tests.

5. Backward compatibility and migration safety:
   - Keep versioned conformance fixtures for public wire behavior.
   - Add compatibility tests for old clients against supported server behavior.
   - Add migration tests that exercise upgrades from prior schema versions.
   - Require explicit deprecation tests for behavior that is being phased out.
   - Add SDK compatibility smoke tests for Python, TypeScript, and Go against the same live-node fixture.

6. Package-specific test coverage:
   - Add MCP Vitest tests around tool schema generation, argument validation, tool dispatch, and Stigmem error mapping.
   - Add Obsidian plugin tests for parser/syncer/settings using mocked Vault/Stigmem clients.
   - Add dashboard unit/component tests for auth/session/api proxy/forms and one Playwright happy path.
   - Add live-node smoke tests for TS/Python/Go SDKs against the same conformance smoke fixture.

7. Ownership and CI governance:
   - Add `CODEOWNERS` or documented ownership by package/domain once collaborators grow.
   - Require core checks before merge: static gates, fast tests, contract drift, wire conformance, security checks.
   - Use path-aware CI to run focused jobs quickly while still protecting shared contracts.
   - Define a flaky-test policy: quarantine only with an issue, owner, and expiration date.
   - Upload conformance, eval, coverage, and soak reports as artifacts for release traceability.

8. Coverage and reporting:
   - Start with coverage reporting only.
   - Add thresholds once the baseline is stable, scoped by package instead of one repo-wide number.
   - Keep coverage meaningful: API behavior, auth boundaries, storage backends, and adapter parsing/serialization matter more than line chasing.

## Public Surface Classification

The remaining policy decision should be resolved by separating protocol promises from product surfaces. Not every repository package should carry the same compatibility burden.

Recommended classification:

- Public and stable:
  - HTTP API exposed by the reference node under `/v1/...`.
  - Canonical spec markdown in `spec/` and versioned conformance vectors in `data/conformance/`.
  - Published SDK APIs for Python, TypeScript, and Go.
  - Generated OpenAPI artifact as the machine-readable wire contract.
- Public but evolving:
  - MCP adapter tool surface and request/response mapping.
  - Obsidian plugin behavior, note-sync semantics, and settings model.
  - Docs examples and quickstart flows that users are expected to copy.
- Internal or non-contract surfaces:
  - Dashboard internals and UI structure while the dashboard remains private and `0.1.0`.
  - Internal CLI implementation details used only as repo/deploy tooling.
  - CI wiring, deployment helpers, test harnesses, and local scripts.

Rationale:

- The README and spec already describe the HTTP API and spec as stable, so the test architecture should treat them as the highest-order contract.
- The SDKs are explicit client products and should be treated as stable public APIs even if some generated details are allowed to shift behind SemVer rules.
- The MCP adapter and Obsidian plugin are user-facing, but their current package versions (`0.x`) and thinner test coverage make them poor candidates for full stability guarantees today.
- The dashboard package is private and should be tested for regressions, but not yet treated as an externally versioned compatibility contract.
- Docs examples are not APIs, but they are still public promises in practice; broken examples should fail docs/quickstart gates.

Compatibility obligations by class:

- Public and stable:
  - Require SemVer discipline, deprecation coverage, migration notes, versioned contract fixtures, and old-client/new-server compatibility jobs.
  - Block releases on contract drift, conformance failures, and SDK smoke failures.
- Public but evolving:
  - Version explicitly, document behavioral changes, and test core workflows.
  - Allow faster iteration, but require changelog notes and upgrade guidance when defaults, commands, tool names, or sync semantics change.
- Internal or non-contract:
  - Optimize for maintainability and correctness, not backward compatibility.
  - Test for behavior and operability, but do not freeze implementation shape.

Immediate consequence for the test plan:

1. Treat HTTP API + spec + conformance + SDKs as the formal compatibility perimeter.
2. Treat MCP, Obsidian, and docs quickstarts as supported public integration surfaces with strong regression coverage but lighter compatibility guarantees until they are promoted out of `0.x`.
3. Treat dashboard and internal CLI/deploy tooling as release-quality software without binding compatibility promises.
4. Wire CI and release rules around those tiers instead of applying one uniform policy to every package.

Promotion criteria for evolving surfaces:

- A public-but-evolving surface should be promoted to stable only after:
  - versioned release ownership is clear,
  - compatibility expectations are documented,
  - contract or workflow fixtures exist,
  - deprecation handling is defined,
  - and CI covers its critical user flows.

Applied to current packages:

- Promote MCP to stable first if it becomes a primary integration path for external agents.
- Promote the Obsidian plugin only after registry distribution, fixture-backed sync tests, and a documented data-migration story.
- Keep the dashboard non-contract until it is published as an intended long-lived user/admin surface with explicit support guarantees.

## Proposed PR Gate Shape

Fast PR gates:
- Python: `uv sync --all-packages`, `ruff check`, `mypy`, `pytest node/tests sdks/stigmem-py/tests adapters -m "not slow and not docker and not eval"`.
- Node/TS: `pnpm install --frozen-lockfile`, `pnpm type-check`, `pnpm --filter stigmem-ts test`, MCP tests once added, dashboard build/type-check.
- Go: `go test ./...` under `sdks/stigmem-go`.
- Contract: OpenAPI drift check and v1 wire vectors.
- Security: keep `pip-audit`, `bandit`, `pnpm audit`, constant-time lint.
- Contributor ergonomics: `make check` or equivalent must run the same fast gate set locally.

Slower PR matrix or required-on-touch:
- Multi-backend conformance for SQLite/libSQL/Postgres.
- Docker image smoke and Helm template.
- Eval-fast adversarial/recall.
- SDK live-node smoke tests when API or SDK code changes.
- Docs build when docs, OpenAPI, or generated API references change.

Nightly/release:
- Federation soak.
- Quickstart Docker Compose E2E.
- Dashboard Playwright E2E.
- Docs build and generated API docs check.
- Full conformance reports uploaded as artifacts.
- Backward compatibility matrix for supported previous client/server contracts.
- Migration checks from supported previous schema versions.

## Packages And Tools

Use existing packages first, then add only the missing pieces needed for package-specific coverage and contract validation.

Python backend, SDK, and adapters:
- Already present: `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis`, `respx`, `ruff`, `mypy`, `bandit`, `pip-audit`.
- Add: `pytest-xdist` for parallel local/CI test runs once markers are stable.
- Add: `pytest-timeout` to prevent hung async/federation tests from blocking CI.
- Add: `pytest-randomly` or `pytest-random-order` only after fixtures are isolated enough; useful for catching hidden global-state coupling.
- Add: `schemathesis` for OpenAPI-driven API contract checks once `docs/openapi/stigmem.json` is corrected.
- Optional add: `openapi-spec-validator` for a cheap OpenAPI artifact sanity check before generated docs/SDKs run.
- Why: the Python side already has the right core stack; the main missing capabilities are parallelism, timeout safety, fixture-order detection, and contract fuzzing.

TypeScript SDK and MCP adapter:
- Already present: `typescript`, `vitest`, `@vitest/coverage-v8`, `vite`, `zod`, `openapi-typescript`.
- Add: no new SDK test framework; continue with `vitest`.
- Add for MCP tests: `tsx` is already present in MCP, plus Vitest tests around exported schema/dispatch helpers after refactoring import-safe boundaries.
- Optional add: `msw` only if SDK/dashboard tests need fetch-level HTTP mocking beyond the current hand-written mock fetch.
- Why: Vitest is already in the repo and fits SDK/MCP unit tests; avoid Jest unless there is a strong reason to split test runners.

Dashboard:
- Already present: Next.js, React, TypeScript, React Query, Radix UI, Tailwind.
- Add: `vitest` for unit/component tests.
- Add: `@testing-library/react`, `@testing-library/user-event`, and `@testing-library/jest-dom` for React component behavior.
- Add: `jsdom` as the Vitest browser-like test environment.
- Add: `@playwright/test` for one or two end-to-end smoke flows.
- Add: `msw` for API mocking in component tests, especially auth/session/API proxy behavior.
- Why: dashboard currently has type/build coverage but no behavioral tests; Testing Library covers components, Playwright covers real routing/browser behavior, and MSW keeps tests close to actual HTTP flows.

Obsidian plugin:
- Already present: TypeScript, esbuild, Obsidian types.
- Add: `vitest`.
- Add: `@types/node` is already present; keep using it for mocked filesystem/runtime behavior.
- Consider `jsdom` only if UI-facing plugin views need DOM tests; parser/syncer/settings tests can stay pure Vitest.
- Why: plugin logic is mostly parser/syncer/settings code and should be testable without a full Obsidian runtime by mocking `Vault`, `TFile`, and `App`.

Go SDK:
- Already present: standard `testing`, `httptest`, and `go test`.
- Add: no required runtime dependency.
- Add CI tool: `go vet ./...`.
- Optional CI tool: `govulncheck` via `golang.org/x/vuln/cmd/govulncheck` for dependency/security checks.
- Why: the Go SDK is small enough that the standard library is sufficient; avoid adding a test framework unless table tests become unreadable.

Contract and generated artifacts:
- Already present: `openapi-typescript` for TypeScript generation.
- Add: a small Python script or module using FastAPI `create_app().openapi()` to regenerate/check `docs/openapi/stigmem.json`.
- Add: `schemathesis` once the OpenAPI artifact is trustworthy.
- Optional add: `dredd` or Prism-style mock validation is not recommended initially; it adds another toolchain when FastAPI + conformance vectors already give better signal.
- Why: the project needs one API source of truth. Generated OpenAPI plus conformance vectors should drive SDKs, docs, and external compatibility.

E2E, deploy, and release:
- Already present: Docker/Compose scripts, Helm lint/template in CI, eval harness, federation soak, SBOM generation with Syft, container signing with Cosign.
- Add: `@playwright/test` for dashboard/browser E2E only.
- Keep: shell/Python smoke scripts for Docker quickstart and federation because they exercise real deployment paths well.
- Why: deployment checks should stay close to operator workflows; browser E2E belongs only where UI behavior matters.

Not recommended initially:
- Jest: duplicates Vitest without clear benefit.
- Cypress: Playwright is better aligned for CI browser smoke and multi-browser growth.
- Heavy mutation testing: useful later for critical pure logic, but too expensive before coverage and contract drift are stable.
- A single repo-wide coverage threshold: package-scoped thresholds are less brittle in this monorepo.

## Verification

- Repository inventory was gathered with `rg --files`, package config reads, workflow reads, and structured JSON counts.
- Local execution of `pnpm type-check` failed because `node_modules` is not installed. Running through `corepack pnpm` works for pnpm itself, but `turbo` is missing until dependencies are installed.
- Local Python checks are blocked because `uv` is not on `PATH`.
- Local Go checks are blocked because `go` is not on `PATH`.
- No production code was changed.

## Review

- Quality review: the recommendation favors existing tools and repo patterns before introducing new dependencies.
- Edge-case review: the plan calls out dynamic Python fixtures, optional backends, stale OpenAPI drift, missing package workspace coverage, slow Docker/eval checks, backward compatibility, and contributor governance as separate risk areas instead of collapsing them into one CI job.
- Verification review: no runtime tests could be completed locally because required toolchain/dependency setup is missing; the documented plan is based on committed config, workflow, and source inspection.
- Next implementation step: add the static/type-check baseline first, add a contributor-friendly `make check` entrypoint, then resolve OpenAPI as the contract source of truth.
