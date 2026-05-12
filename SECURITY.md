# Security Policy

**Security resources:**
- [Community Pen-Test Handbook](https://docs.stigmem.dev/security/pen-test) — scope, safe harbor, report template, disclosure timeline, and recognition.
- [Threat Model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md) — trust boundaries, STRIDE analysis, risk register.

## Supported Versions

Stigmem follows the alpha-beta-rc pre-release convention per [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The first build of stigmem is `v0.9.0a1`; stable v1.0 has not shipped.

| Version | Supported |
| ------- | --------- |
| `0.9.0a*` (the v0.9.0aN alpha series — current) | Yes — current pre-release line. **No stability guarantee.** Breaking changes during the hardening window are expected and documented in [CHANGELOG.md](CHANGELOG.md). |
| `0.9.0b*` (the v0.9.0bN beta series — future) | Will be supported when published. |
| `1.0.0rc*` / `1.0.0` (v1.0.0rcN / v1.0.0 GA — future) | Will be supported when published. |
| `1.0.0rc1` (retracted label, never shipped) | **N/A.** The label was announced publicly in 2026-05-03 but the package was never actually published to PyPI (audit 2026-05-08: `pypi.org/pypi/stigmem` returns 404). Nothing to install; nothing to yank. The label was withdrawn — see the retraction post linked from [README §Why v0.9.0a1 and not v1.0](README.md#why-v090a1-and-not-v10). |
| `< 0.9.0a1` (development checkpoints — `v0.2` through `v2.0`) | **No.** These were internal development checkpoints, not tagged releases. The canonical version line begins at `v0.9.0a1`. |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues via GitHub's private advisory path:

1. Go to the [Security Advisories](https://github.com/eidetic-labs/stigmem/security/advisories) page.
2. Click **"Report a vulnerability"**.
3. Fill in the details: description, reproduction steps, potential impact, and suggested fix if known.

We will acknowledge your report within **48 hours** and aim to release a patch within **14 days** for critical vulnerabilities.

## Scope

In-scope:

- Remote code execution or injection vulnerabilities
- Authentication or authorization bypasses
- Data exposure or exfiltration
- Supply chain attacks on our published packages

Out-of-scope:

- Issues in third-party dependencies (report to the upstream project)
- Rate limiting or resource exhaustion without a clear security impact

## Disclosure Policy

We follow coordinated disclosure. We ask reporters to give us 90 days before public disclosure, except for issues already being actively exploited in the wild.

---

## Security Posture — v0.9.0a1 (2026-05-08)

> **Posture-reset note.** Stigmem's `v1.0` announcement was withdrawn on 2026-05-08; the canonical version line was reset to `v0.9.0a1` per [ADR-001](docs/adr/001-versioning.md) and [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The dependency-alert triage in this section was originally compiled for `the pre-reset v1.0-rc snapshot` on 2026-05-03 and is **carried forward to v0.9.0a1** because the underlying dependency upgrades remain in effect — the same fixed package versions that resolved the alerts at the pre-reset v1.0-rc snapshot are still installed at v0.9.0a1. The supported-version posture changed (see "Supported Versions" above); the dependency-fix evidence did not.
>
> **Open security gaps named explicitly:** several controls our threat model identifies as required for stable production — mTLS-default federation, persistent audit log, per-principal rate limits, capability-level validation for cross-org instructions, bounded HLC skew enforcement, the storage-immutability stack ([ADR-016](docs/adr/016-storage-immutability-enforcement.md)) — are scheduled for the v0.9.0bN beta series and are **not yet in effect at v0.9.0a1**. Adopters running federation across organizational boundaries should wait for the v0.9.0bN beta series per [LIMITATIONS.md](LIMITATIONS.md).

This section documents the current security posture of the stigmem `v0.9.0a1` release, including a triage of all open Dependabot alerts against Eidetic-Labs/stigmem as of the 2026-05-03 pre-reset v1.0-rc snapshot (carried forward; see note above).

### Summary

| Category | Source | Count |
| -------- | ------ | ----- |
| Dependabot — alerts addressed by the pre-reset v1.0-rc snapshot dep upgrade sweep + follow-up patch sweep | Dependency advisories | 22 |
| Dependabot — alerts in docs build toolchain (non-exploitable, suppressed) | Dependency advisories | 7 |
| CodeQL — conditional SQL-fragment assembly (false positives, closed by structural constant-SQL refactor) | Static dataflow analysis | 8 |
| Unaddressed / escalated blockers | — | 0 |

**Net result: zero unaddressed security alerts at v0.9.0a1.** Dependabot alerts are a *dependency* concern and CodeQL alerts are a *static-analysis* concern — both are separate from the threat-model risks named in the posture-reset banner above.

---

### Group A — Resolved by the dep upgrade sweep that landed pre-v0.9.0a1 (20 alerts)

The `chore(deps): TypeScript dep upgrade sweep + Node CVE remediation` commit upgraded the following packages to patched versions. Dependabot alerts will auto-close on the next GitHub rescan after the branch merges.

#### Next.js (`experimental/dashboard/`, deferred per ADR-002) — 17 alerts

The Next.js curator dashboard (`experimental/dashboard/`) was pinned at Next.js 14 and accumulated CVEs from three major Next.js disclosure cycles. The pre-v0.9.0a1 dep sweep upgraded it to `next@15.5.15`. A follow-up upgrade to `next@15.5.16` lands the patch for [GHSA-8h8q-6873-q5fj](https://github.com/advisories/GHSA-8h8q-6873-q5fj) (alerts #38 and #39, which Dependabot tracked separately for `experimental/dashboard/package.json` and `pnpm-lock.yaml`).

| Alert | Severity | CVE / GHSA | Summary | Resolution |
| ----- | -------- | --- | ------- | ---------- |
| #38, #39 | HIGH | GHSA-8h8q-6873-q5fj | (See advisory) | `next@15.5.16` ≥ patched `15.5.16` |
| #17 | HIGH | — | DoS with Server Components | `next@15.5.15` ≥ patched `15.5.15` |
| #16 | MEDIUM | CVE-2026-27980 | Unbounded next/image disk cache growth | `next@15.5.15` ≥ patched `15.5.14` |
| #15 | MEDIUM | CVE-2026-29057 | HTTP request smuggling in rewrites | `next@15.5.15` ≥ patched `15.5.13` |
| #14 | HIGH | — | DoS via insecure React Server deserialization | `next@15.5.15` ≥ patched `15.5.10` |
| #13 | MEDIUM | CVE-2025-59471 | DoS via Image Optimizer remotePath | `next@15.5.15` ≥ patched `15.5.10` |
| #12 | HIGH | — | DoS with Server Components (incomplete fix follow-up) | `next@15.5.15` ≥ patched `15.5.9` |
| #11 | HIGH | — | DoS with Server Components | `next@15.5.15` ≥ patched `15.5.8` |
| #10 | LOW | CVE-2025-32421 | Race condition → cache poisoning | `next@15.5.15` ≥ patched `15.1.6` |
| #9 | MEDIUM | CVE-2025-57822 | Improper middleware redirect → SSRF | `next@15.5.15` ≥ patched `15.4.7` |
| #8 | MEDIUM | CVE-2025-55173 | Content injection via Image Optimization | `next@15.5.15` ≥ patched `15.4.5` |
| #7 | MEDIUM | CVE-2025-57752 | Cache key confusion for Image Optimization routes | `next@15.5.15` ≥ patched `15.4.5` |
| #6 | LOW | CVE-2025-48068 | Info exposure via missing origin check in dev server | `next@15.5.15` ≥ patched `15.2.2` |
| #5 | CRITICAL | CVE-2025-29927 | Authorization bypass in Next.js middleware | `next@15.5.15` ≥ patched `15.2.3` |
| #4 | MEDIUM | CVE-2024-56332 | DoS via Server Actions | `next@15.5.15` ≥ patched `15.1.2` |
| #3 | HIGH | CVE-2024-51479 | Authorization bypass | `next@15.5.15` ≥ patched `14.2.15` |
| #2 | MEDIUM | CVE-2024-47831 | DoS via image optimization | `next@15.5.15` ≥ patched `14.2.7` |
| #1 | HIGH | CVE-2024-46982 | Cache poisoning | `next@15.5.15` ≥ patched `14.2.10` |

> **Deployment gate:** The dashboard at `experimental/dashboard/` is deferred per ADR-002 and is not deployed to production at v0.9.0a1. Even so, all CVEs above are fixed in the installed version. No deployment should occur on any prior version.

#### vite — 1 alert

| Alert | Severity | CVE | Summary | Resolution |
| ----- | -------- | --- | ------- | ---------- |
| #27 | MEDIUM | CVE-2026-39365 | Path traversal in optimized deps `.map` handling | `vite@6.4.2` in `pnpm-lock.yaml` ≥ patched `6.4.2` |

This vulnerability requires the Vite dev server to be explicitly exposed to the network (`--host`). Stigmem does not use `vite --host` in any deployed environment.

#### esbuild — 1 alert

| Alert | Severity | CVE | Summary | Resolution |
| ----- | -------- | --- | ------- | ---------- |
| #26 | MEDIUM | — | esbuild dev server allows cross-origin requests | `esbuild@0.25.12` and `0.27.7` in `pnpm-lock.yaml` ≥ patched `0.25.0` |

esbuild's dev server is never exposed in production builds. This is exclusively a local development tooling concern.

---

### Group B — Docs build toolchain (7 alerts, suppressed)

These 7 alerts exist in transitive dependencies of `docusaurus-plugin-openapi-docs@5.0.2`, which is used to generate the API reference section of the documentation site. All are **build-time only** — they are not included in the static HTML/JS output that browsers load from the deployed docs site.

The vulnerable code paths all require **attacker-controlled input** to be processed by these libraries (prototype-pollution gadgets, YAML parser depth bombs, etc.). In the stigmem docs build, the only input to these parsers is our own OpenAPI spec committed to source control. There is no user-supplied input pathway.

`npm audit fix` can resolve these only by downgrading `docusaurus-plugin-openapi-docs` to `2.1.3`, which is a breaking change incompatible with Docusaurus 3.10. The fix will be taken when an upstream non-breaking patch is released.

| Alert | Severity | CVE | Package | Suppression rationale |
| ----- | -------- | --- | ------- | --------------------- |
| #18 | MEDIUM | CVE-2025-64718 | `js-yaml@4.1.0` (via openapi-to-postmanv2) | Build-time parser; input is trusted OpenAPI spec in source control. No user-controlled input path. |
| #19 | MEDIUM | CVE-2025-13465 | `lodash@4.17.21` (via openapi-to-postmanv2) | Build-time utility; prototype-pollution requires attacker-controlled object key. Source input is trusted. |
| #20 | HIGH | — | `serialize-javascript@6.0.2` (via copy-webpack-plugin) | Webpack serialization; runs only in CI build environment. RCE requires attacker-controlled input to the serializer during build — not applicable to our trusted-source docs build. |
| #21 | MEDIUM | CVE-2026-33532 | `yaml@1.10.2` (via openapi-to-postmanv2) | Build-time YAML parser; stack overflow requires a deeply-nested YAML file. Our OpenAPI spec is a trusted static file. |
| #22 | MEDIUM | CVE-2026-34043 | `serialize-javascript@6.0.2` (via copy-webpack-plugin) | Same as #20. CPU-exhaustion DoS requires crafted input to build step — not applicable. |
| #23 | MEDIUM | CVE-2026-2950 | `lodash@4.17.23` (via postman-collection) | Same rationale as #19. `_.unset`/`_.omit` not called on attacker-supplied keys during docs build. |
| #24 | HIGH | CVE-2026-4800 | `lodash@4.17.21` (via openapi-to-postmanv2) | Same rationale as #19. `_.template` code-injection requires attacker-controlled template string. Docs build uses fixed templates. |

**Tracking:** These suppressed findings will be re-evaluated when `docusaurus-plugin-openapi-docs@5.x` ships a version that resolves its `openapi-to-postmanv2` and `postman-collection` dependency pins.

---

### Group C — CodeQL static-analysis alerts (8 alerts, closed by structural refactor)

GitHub code-scanning (CodeQL) raised 8 open high-severity alerts against `node/src/stigmem_node/routes/` and `node/src/stigmem_node/storage/`. All 8 were **false positives** caused by a single root cause: CodeQL's taint analyzer cannot reason about Python's conditional-string-fragment assembly pattern (`if entity: conditions.append("AND f.entity = ?")`) — it treats any f-string concatenation reachable from a FastAPI `Query` param as a SQL sink, even though the user values themselves are parameter-bound and only literal SQL fragments are interpolated.

The existing `# nosec B608` suppression comments satisfied bandit but **CodeQL does not honor `# nosec` or `# noqa`**. The durable remediation is structural: refactor the SQL builders so the SQL text is a module-level constant and optional filters are gated by bound parameters using the `(? IS NULL OR col = ?)` pattern (or a `? = 1` sentinel for boolean flags). The constant-SQL form makes safety obvious to the analyzer and removes the need for any suppression comment.

The structural refactor landed on main; CodeQL re-scan closed all 8 alerts at the source.

| Alert | Rule | Location | Rationale | Resolution |
| ----- | ---- | -------- | --------- | ---------- |
| #18 | `py/sql-injection` | `routes/lint.py:124` (was) | Stale-fact check builder; conditional-fragment assembly. Safe at runtime — only literal SQL fragments interpolated; user values parameter-bound. | Constant-SQL refactor using the `_STALE_SQL` module constant. |
| #19 | `py/sql-injection` | `routes/lint.py:185` (was) | Broken-ref check builder; same pattern as #18. | Constant-SQL refactor using the `_REF_SQL` module constant. |
| #21 | `py/polynomial-redos` | `storage/postgres_backend.py:146` | Transitive taint: CodeQL traced f-string-built SQL from routes into `_pg_translate`'s `_STRFTIME_EPOCH_RE.sub()` call. In practice the regex only sees migration-file SQL (developer-authored, trusted), but the analyzer cannot prove that. | Closed by breaking the false taint chain. Belt-and-suspenders: bounded quantifiers on the regex (`\s{0,16}`, `[^)]{1,256}?`) to satisfy the polynomial-ReDoS heuristic permanently. |
| #22 | `py/sql-injection` | `routes/facts.py:246` (was) | `as_of` facts query builder; conditional-fragment assembly. | Constant-SQL refactor using the `_AS_OF_SELECT_SQL` module constant; `_build_as_of_query()` returns `(sql, params)` directly with no caller-side f-string. |
| #23 | `py/sql-injection` | `routes/lint.py:94` (was) | Contradiction check builder; same pattern as #18. | Constant-SQL refactor using the `_CONFLICT_SQL` module constant. |
| #24 | `py/sql-injection` | `routes/lint.py:220` (was) | Namespacing check builder; same pattern. | Constant-SQL refactor using the `_NS_SQL` module constant. |
| #25 | `py/sql-injection` | `routes/lint.py:254` (was) | Fact-count query; same pattern. | Constant-SQL refactor using the `_COUNT_SQL` module constant. |
| #26 | `py/sql-injection` | `routes/synthesize.py:105` (was) | Scope synthesize query; boolean `include_expired` toggled a fragment. | Constant-SQL refactor using the `_SYNTHESIZE_SQL` module constant; `? = 1` sentinel for the boolean toggle. |

**No new R-XX risk entries** in the threat model: the conditions for exploitation do not exist (every user value parameter-bound; every interpolated fragment a string literal). The alerts were precision-gap artifacts, not vulnerabilities. See [`spec/security/threat-model.md`](spec/security/threat-model.md) § 10 Rev 2.2 and [`spec/security/audit-triage.md`](spec/security/audit-triage.md) for the permanent rationale.

**Tracking:** Future CodeQL alerts on Python source paths will be triaged under this Group C pattern. Path-level CodeQL config exclusions are deliberately avoided so that real future bugs remain visible.

---

### Core Node (Python/FastAPI)

The stigmem reference node (`stigmem/node/`) is implemented in Python with FastAPI and SQLite. It has no JavaScript dependency tree. No Python Dependabot alerts are open as of 2026-05-03. Python dependencies are managed via `uv` and `pyproject.toml`; `uv.lock` is checked in.

---

### Security Controls in Effect (v0.9.0a1)

> The controls listed here are **dependency- and code-level controls** that are in effect at v0.9.0a1. **Federation-level and threat-model-level controls** named in the posture-reset banner at the top of this section (mTLS-default, audit log, rate limits, capability validation, bounded HLC skew, storage-immutability stack) are **not yet in effect** and are scheduled for the v0.9.0bN beta series.

- **Authentication:** API keys enforced on all write endpoints; per-scope restrictions supported (§3.5).
- **Federation:** Peer handshake uses Ed25519 signing; replay attack resistance via HLC timestamps (§6).
- **Input validation:** Pydantic models on all HTTP endpoints; malformed payloads return 422 before reaching business logic.
- **Secrets:** No credentials are committed to the repository. Docker Compose uses environment variable injection.
- **Container image retention:** Every released container image (`:0.9.0aN`, `:0.9.0bN`, `:1.0.0rcN`, `:1.0.0`, plus the semver-strict spellings) is **retained on GHCR indefinitely**, so an audit trail back to any historical release remains verifiable. Rolling pointers (`:latest`, `:edge`) are retained forever; short-SHA forensics tags are pruned after 90 days. Sigstore signatures are retained alongside their target image. See [`docs/internal/release-cadence.md`](docs/internal/release-cadence.md#rule-7--ghcr-image-retention) Rule 7 for the operational details, and the [tag-selection guide](https://docs.stigmem.dev/operators/deployment/install#image-tags) for choosing the right pin for your deployment.
- **CI:** Dependabot alerts are monitored; `pip-audit`, `pnpm audit`, `bandit`, and CodeQL run as blocking CI steps on every PR (see Audit Tooling below).

---

### Audit Tooling

All four tools run as blocking steps in `.github/workflows/ci.yml` on every push and pull request.

| Tool | Scope | What it checks | CI step |
| ---- | ----- | -------------- | ------- |
| `pip-audit` | Python dependencies (`uv.lock`) | Known CVEs in installed packages via PyPI advisory database | `python-tests` job — exits non-zero on any moderate+ finding |
| `pnpm audit` | Node.js dependencies (`pnpm-lock.yaml`) | Known CVEs via npm advisory database | `node-tests` job — `--audit-level=moderate` |
| `bandit` | Python source (`node/src/`, `sdks/stigmem-py/src/`) | Common Python security anti-patterns (injection, weak crypto, unsafe deserialization) | `python-tests` job — configured via `[tool.bandit]` in `pyproject.toml`; `B101` (assert usage) suppressed for test code |
| `CodeQL` | Python + JavaScript/TypeScript + Go + GitHub Actions sources | Semantic dataflow / taint analysis: SQL injection, ReDoS, hardcoded secrets, prototype pollution, … (via GitHub Advanced Security) | `analyze (python / javascript-typescript / go / actions)` jobs — alerts surfaced in [Security → Code scanning](https://github.com/Eidetic-Labs/stigmem/security/code-scanning); triage rationale recorded in Group C above and in [`spec/security/audit-triage.md`](spec/security/audit-triage.md) |

**Running locally:**

```bash
# Python dependency audit
uv run pip-audit

# Python static analysis
uv run bandit -r node/src/ sdks/stigmem-py/src/ -c pyproject.toml

# Node.js dependency audit
pnpm audit --audit-level=moderate
```

The docs build toolchain (`docusaurus-plugin-openapi-docs` and its transitive dependencies) generates known alerts in `pnpm audit` output. These are suppressed per the Group B analysis above — they are build-time only and have no user-controlled input pathway.
