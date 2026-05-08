# Contributing to Stigmem

Thanks for your interest in contributing. Stigmem is a community spec — the goal is to get smart people with production experience to stress-test the design before it ossifies.

## Ways to contribute

| Track | What it is | Who it's for |
|---|---|---|
| **RFC** | Propose a spec change via issue + PR | Anyone with a concrete problem or proposed improvement |
| **Implementation** | Build an alternative node or client | Developers who want to validate the wire format against real workloads |
| **Bug / gap report** | File an issue about a spec ambiguity or prototype bug | Anyone reading the spec |

## RFC process

Use this when you want to propose a spec change, add a new field or endpoint, change semantics, or resolve an open question from §8.

1. **Open an RFC issue** using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml). Include:
   - The problem you're solving
   - Your proposed change
   - Alternatives you considered
   - Open questions
2. **Discuss** on the issue. Aim for at least one week of async discussion before calling for merge.
3. **Submit a PR** against the active spec file (e.g., `spec/stigmem-spec-v0.2.md`). Reference the issue.
4. **Merge criteria:** ≥2 approvals from contributors who have merged at least one prior PR. The spec maintainer may veto with a written rationale.

For small fixes (typos, clarity, example corrections), skip the RFC issue and send a PR directly.

## Conformance suite

**Contract:** every new spec section or wire-format change MUST include at least one new conformance vector in `data/conformance/v1.0/`. PRs that add or modify spec text without a corresponding vector will not be merged.

The `data/conformance/v1.0/` directory contains machine-readable test vectors that every conforming implementation must pass. The CI job **Stigmem v1.0 Conformance Suite** runs on every push to `main` and on pull requests that touch `node/`, `spec/`, `data/conformance/`, or the workflow file itself.

**Run locally:**

```bash
uv run pytest node/tests/test_conformance_v1.py -v
```

**Adding a new test vector:**

1. Open (or create) a numbered file in `data/conformance/v1.0/` (e.g., `06_new_feature.json`). The runner loads all files matching `0*.json` in sorted order.
2. Use this top-level structure:

```json
{
  "spec_section": "§X.Y",
  "title": "Short group title",
  "description": "Optional longer description",
  "vectors": [...]
}
```

3. Each vector must include at minimum `id`, `description`, `method`, `path`, and one of the `expected_*` assertion fields:

```json
{
  "id": "unique-kebab-id",
  "description": "What this vector tests",
  "method": "POST",
  "path": "/v1/facts",
  "body": { "entity": "stigmem://node/user/alice", "relation": "memory:role", "..." },
  "expected_status": 201,
  "expected_body_contains": { "entity": "stigmem://node/user/alice" },
  "expected_body_has_keys": ["id", "timestamp"]
}
```

4. Use `expected_nested` for deep assertions without matching the full response. Keys are dotted paths:

```json
"expected_nested": { "value.type": "number", "value.v": 42.5 }
```

   This checks `response["value"]["type"] == "number"` and `response["value"]["v"] == 42.5`.

5. Use `requires_setup` (another vector's `id`) to declare ordering dependencies — the runner will execute the prerequisite first within the same DB session.

6. **Do not add vectors with `requires_auth: true` to files in `data/conformance/v1.0/`.** Zero skips are enforced by CI; auth-dependent scenarios belong in the dedicated auth test module.

## CLI reference docs

Regenerate the CLI reference pages (under `docs/docs/reference/cli/`) after changing CLI flags or adding subcommands: `make gen-cli-docs`.

## Per-phase docs-delta requirement

Every phase of the roadmap MUST ship a docs-improvement deliverable. This is a board mandate (2026-05-03).

**What counts as a docs-delta:**

- A new guide, reference page, or conceptual doc added to the docs site.
- A substantive update to existing content (not just typo fixes).
- A new working code example for a feature that shipped in the phase.
- An updated architecture diagram reflecting the phase's changes.
- A Features-table row update (see below).

**How to declare it in a PR:**

Include a `docs-delta:` line in the PR body listing what docs shipped with the phase. Example:

```
docs-delta: Added federation-trust guide (docs/docs/build/guides/federation-trust.md),
updated Features table row for org manifests.
```

Phase PRs without a docs-delta line will be flagged during review.

## Features page update procedure

The [Features page](docs/docs/learn/features.md) status table is the **single source of truth** for what Stigmem can do today. When a feature ships:

1. Open `docs/docs/learn/features.md`.
2. Find or add the row for the capability in the appropriate section table.
3. Set its **Status** column to one of: `Stable`, `Beta`, `Experimental`, or `Planned`.
4. Fill the **Spec** column with the relevant spec section (e.g., `§20.3`).
5. Fill the **Docs** column with a relative link to the guide or reference page.
6. If a previously `Planned` or `Experimental` feature is promoted, update the row in place — do not add a duplicate.

The Features page intentionally avoids calendar dates. Do not add target-quarter references.

## Docs versioning snapshot procedure

Stigmem docs use [Docusaurus versioned docs](https://docusaurus.io/docs/versioning). The `current` (in-development) docs live in `docs/docs/`; released snapshots live in `docs/versioned_docs/version-<tag>/` with matching sidebars in `docs/versioned_sidebars/`.

When a new spec version ships (post v1.1), create a versioned snapshot:

1. Merge all docs IA restructuring, de-duplication, and content updates for the release.
2. From the `docs/` directory:

```bash
npm run docusaurus docs:version <version-tag>
```

This copies `docs/docs/` → `docs/versioned_docs/version-<version-tag>/` and `docs/sidebars.js` → `docs/versioned_sidebars/version-<version-tag>-sidebars.json`, then prepends the tag to `docs/versions.json`.

3. Update `docusaurus.config.js` → `docs.versions`:
   - Set `lastVersion` to the new tag (e.g., `'v2.0'`) so bare `/docs/*` URLs resolve to the released version.
   - Add the new version entry: `'v2.0': { label: 'v2.0', badge: true }`.
   - Relabel `current`: `{ label: 'v2.1-draft', path: 'next', badge: true, banner: 'unreleased' }`.

4. Run `npm run build` — must exit 0 with no broken links.

**Version naming:** use `v<major>.<minor>` matching spec releases (e.g., `v0.2`, `v1.1`, `v2.0`). The `current` label is always `<next>-draft`.

## Audience and status frontmatter conventions

Every docs page must include an `audience` field in its YAML frontmatter:

```yaml
---
id: my-page
title: My Page
audience: Integrator
---
```

**Allowed audience values:**

| Value         | Who it addresses                                     |
|---------------|------------------------------------------------------|
| `Curious`     | Evaluators, newcomers deciding whether to adopt      |
| `Integrator`  | Developers building on Stigmem (agent devs, SDK consumers) |
| `Operator`    | Node operators running and maintaining a Stigmem node |
| `Spec`        | Spec contributors and reference-node developers      |

Pages under `learn/` default to `Curious`; pages under `build/` default to `Integrator`; pages under `operate/` default to `Operator`; spec and architecture pages use `Spec`. Always set the field explicitly rather than relying on defaults.

The build-time validation plugin (`docs/plugins/validate-audience.js`) will fail the build if any doc page is missing a valid `audience` field. Auto-generated API reference pages (under `reference/api/generated/`) are exempt.

**Optional `status` field:**

Pages describing non-stable features may include a `status` field, which renders a prominent admonition banner:

| Value          | Admonition type | Meaning |
|----------------|-----------------|---------|
| `Experimental` | caution         | Behind a flag, breaking changes expected |
| `Beta`         | warning         | Early adopters, minor breaking changes possible |
| `Planned`      | info            | Spec draft exists, not yet implemented |

Stable features do not need a `status` field. The Features page table remains the single source of truth for overall feature status.

## Docs drift watchdog

CI runs `docs/scripts/check_drift.py` on every push and PR to catch stale or forbidden content in the docs tree. It checks for:

- **Forbidden strings** — product names or terms that must not appear (e.g., references to unrelated products).
- **Calendar quarter dates** — `Q1 2025`-style strings outside exempt historical/roadmap files, which go stale quickly.
- **Stale claims** — absolute statements that are no longer true (e.g., "no vector search" after that feature shipped).
- **Bare tracker IDs** — internal issue tracker references (e.g., `ACM-123`) that leaked into public docs.

Rules live in `docs/scripts/drift-rules.json`. To add a new rule, edit the appropriate section in that file — no code changes required. Run locally:

```bash
python docs/scripts/check_drift.py
```

To exempt a file from the calendar-quarter check (e.g., a new changelog page), add its path to the `exempt_globs` array in `drift-rules.json`.

### Rule types in `drift-rules.json`

| Key                  | Purpose                                               | How to add a new entry                                        |
|----------------------|-------------------------------------------------------|---------------------------------------------------------------|
| `forbidden_strings`  | Block specific terms from the docs tree               | Add `{ "pattern": "...", "flags": "i", "description": "..." }` to the array |
| `calendar_quarters`  | Flag `Q1 2025`-style refs that go stale               | Update `exempt_globs` to whitelist new historical pages       |
| `stale_claims`       | Catch absolute negatives disproved by shipped features | Add `{ "pattern": "...", "flags": "i", "description": "..." }` to the array |
| `bare_ticket_ids`    | Prevent internal tracker IDs from leaking             | Add the prefix string to `tracker_prefixes`                   |

After editing `drift-rules.json`, run `python docs/scripts/check_drift.py` locally to verify no false positives before pushing.

## Prototype contributions

The prototype in `prototype/` is a minimal reference implementation — not production software. Contributions that validate spec behavior are welcome; contributions that add production-hardening, auth, or persistence layers should wait until Phase 2 scope is set.

To run it:

```bash
cd prototype
pip install -r requirements.txt
python main.py        # starts the local node on :8000
python seed_memory.py # loads example facts
```

Tests: `pytest` (when test coverage exists — contributions welcome).

## Local verification

Install the same core toolchain the CI jobs expect:

- `uv` with Python 3.11
- Node 20 with Corepack / `pnpm`
- Go 1.22+
- Docker and Helm for container/deploy checks

Fast PR-equivalent checks:

```bash
make check
```

Focused package checks:

```bash
make check-python
make check-node
make check-contract
make check-go
make check-docs
make check-obsidian
make check-sdk-compat
```

Notes:

- Python lint and mypy are on a staged baseline. New findings fail CI even though historical debt is still being burned down.
- `make check-sdk-compat` starts a local node with auth disabled and smoke-tests the Python, TypeScript, and Go SDKs against the same server.
- Slower suites such as eval, federation soak, and multi-backend deployment checks remain outside the default PR loop.

## Test policy

The repository is converging on a shared marker taxonomy:

- `unit`
- `integration`
- `conformance`
- `postgres`
- `libsql`
- `docker`
- `eval`
- `slow`
- `network`

Fast PR checks should stay in `unit` plus fast `integration`. New slow or environment-dependent coverage should be marked accordingly.

## Flaky tests

Do not silently quarantine flaky tests.

- If a test is quarantined or temporarily skipped, link an issue in the skip reason.
- Assign an owner in the issue.
- Include an expiration or review date in the issue/PR so the quarantine is not permanent.
- Re-enabling the test is preferred over broad retries that hide regressions.

## Spec authorship and attribution

The spec file records authors in its header. RFC contributors who make substantive changes to spec content are listed. Implementation-only contributors are acknowledged in CHANGELOG.

## AI-authorship disclosure

Stigmem is built by two contributors with heavy AI-coding assistance. We disclose this because a category whose product is trust shouldn't quietly hide where the work came from. The same disclosure appears in [README.md](README.md#ai-authorship-disclosure).

**Paths with deeper human review (line-by-line):**
- `spec/` — protocol specification text
- `docs/adr/` — Architecture Decision Records
- `LIMITATIONS.md`, `SECURITY.md`, `MAINTAINERS.md`, root `README.md`
- All threat-model entries (`spec/security/`, `docs/security/`)

**Paths with lighter human review (high-level direction + spot-checks):**
- `node/src/` — implementation
- `adapters/` — adapter implementations
- `sdks/` — SDK stubs
- `apps/` — UI scaffolding
- Test suites
- Documentation pages outside the spec and ADRs

**What we ask of contributors:**
- When submitting a PR that includes AI-generated code, say so in the PR description. We don't reject AI-generated contributions — we calibrate review effort. Code in deeper-review paths gets line-by-line attention regardless of authorship.
- When reviewing a PR, treat lighter-reviewed paths as you would any AI-written code: verify behavior against the spec, run the conformance suite, and audit before merging.
- Disclosing AI assistance is a calibration aid, not a defect notice.

## Code of conduct

Be direct and technically rigorous. Assume good faith. Disagree with arguments, not people. There is no formal CoC document yet; interim standard is the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree your contributions are licensed under Apache-2.0 (same as the project).
