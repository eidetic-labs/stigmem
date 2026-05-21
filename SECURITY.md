# Security Policy

**Security resources:**
- [Community Pen-Test Handbook](https://docs.stigmem.dev/security/pen-test) — scope, safe harbor, report template, disclosure timeline, and recognition.
- [Threat Model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md) — trust boundaries, STRIDE analysis, risk register.

## Supported Versions

Stigmem follows the alpha-beta-rc pre-release convention per [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The first build of stigmem is `v0.9.0a1`; stable v1.0 has not shipped.

| Version | Supported |
| ------- | --------- |
| `0.9.0a*` (the v0.9.0aN alpha series — current) | Yes — current pre-release line. **No stability guarantee.** Breaking changes during the hardening window are expected and documented in [CHANGELOG.md](CHANGELOG.md). |
| Future beta line | Will be supported if and when a beta artifact is published; no active beta milestone exists today. |
| Future release-candidate / GA lines | Will be supported if and when those artifacts are published; no active RC or GA milestone exists today. |
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

## Advisory Publication Policy

Stigmem uses **CVSS 4.0** as the primary severity signal for GitHub Security Advisories (GHSAs). For the supported alpha line:

- Critical and High vulnerabilities that affect a published artifact are disclosed with a GitHub repository security advisory after a patched version is available.
- Medium and Low vulnerabilities are documented in release notes, security posture docs, or operator guidance unless there is known exploitation, third-party reporter coordination, or a downstream compliance need that makes a formal advisory appropriate.
- CVE requests are optional. Stigmem reserves CVE requests for broadly deployed stable releases, known exploitation, third-party reporter coordination, or explicit partner/customer compliance needs.

---

## Security Posture — v0.9.0a2 (2026-05-18)

> **Posture-reset note.** Stigmem's `v1.0` announcement was withdrawn on 2026-05-08; the canonical version line was reset to `v0.9.0a1` per [ADR-001](docs/adr/001-versioning.md) and [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The dependency-alert triage in this section was originally compiled for `the pre-reset v1.0-rc snapshot` on 2026-05-03 and is **carried forward to v0.9.0a2** because the underlying dependency upgrades remain in effect — the same or newer fixed package versions that resolved the alerts at the pre-reset v1.0-rc snapshot are installed at v0.9.0a2. The supported-version posture changed (see "Supported Versions" above); the dependency-fix evidence did not.
>
> **Open security gaps named explicitly:** several controls our threat model identifies as required for stable production — mTLS-default federation, persistent audit log, per-principal rate limits, capability-level validation for cross-org instructions, bounded HLC skew enforcement, the storage-immutability stack ([ADR-016](docs/adr/016-storage-immutability-enforcement.md)) — remain future hardened-core work and are **not yet in effect at v0.9.0a2**. Adopters running federation across organizational boundaries should wait until those controls ship in a later hardened-core line per [LIMITATIONS.md](LIMITATIONS.md). No beta, release-candidate, or GA milestone is active today.

This section documents the current security posture of the stigmem `v0.9.0a2` release, including Dependabot and CodeQL triage carried forward from the 2026-05-03 pre-reset v1.0-rc snapshot plus follow-up dependency patches through 2026-05-18.

### Summary

| Category | Source | Count |
| -------- | ------ | ----- |
| Dependabot — alerts addressed by the pre-reset v1.0-rc snapshot dep upgrade sweep + follow-up patch sweeps | Dependency advisories | 27 |
| Dependabot — alerts in docs build toolchain (non-exploitable, suppressed) | Dependency advisories | 7 |
| CodeQL — conditional SQL-fragment assembly (false positives, closed by structural constant-SQL refactor) | Static dataflow analysis | 8 |
| Unaddressed / escalated blockers | — | 0 |

**Net result: zero unaddressed security alerts at v0.9.0a2.** Dependabot alerts are a *dependency* concern and CodeQL alerts are a *static-analysis* concern — both are separate from the threat-model risks named in the posture-reset banner above.

### Internal audit dispositions — v0.9.0a2

The v0.9.0a2 hardening release includes a batch of findings identified during internal audit. Critical and High findings that affect published artifacts are disclosed as GitHub Security Advisories (GHSAs). Medium and Low findings are documented here rather than published as formal GHSAs unless their risk profile changes. All listed findings are patched by `stigmem-node 0.9.0a2`; upgrade with:

```bash
pip install --upgrade --pre stigmem-node
```

If you install through the meta-package, use:

```bash
pip install --upgrade --pre 'stigmem[node]'
```

| Finding | Severity | Advisory | Resolution |
| ---- | -------- | -------- | ------- |
| C1 — Federation peer token timestamp handling | High (CVSS 4.0 — 7.1) | [GHSA-xh5j-xjfq-qvvx](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-xh5j-xjfq-qvvx) | Canonical millisecond token contract with regression coverage for valid and seconds-shaped tokens. |
| C2 — Non-loopback insecure federation startup | Critical (CVSS 4.0 — 9.1) | [GHSA-jmfc-hfjq-pxcp](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-jmfc-hfjq-pxcp) | Startup refuses insecure federation mode on non-loopback deployments. |
| H1 — Non-loopback auth-disabled deployment | Critical (CVSS 4.0 — 9.2) | [GHSA-fp6w-8wpg-74g5](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-fp6w-8wpg-74g5) | Startup refuses anonymous full-permission mode outside local development. |
| H2 — Federation peer registration approval gate | Critical (CVSS 4.0 — 9.1) | [GHSA-9vp8-3hmv-8fgh](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-9vp8-3hmv-8fgh) | Peer registration requires explicit out-of-band approval before activation. |
| H3 — Unsigned plugin override acknowledgement | High (CVSS 4.0 — 7.3) | [GHSA-w7pm-9g55-mxfm](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-w7pm-9g55-mxfm) | Unsigned plugin override requires explicit operator acknowledgement. |
| H5 — Postgres schema identifier handling | High (CVSS 4.0 — 7.5) | [GHSA-9pc9-4crj-mhpj](https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-9pc9-4crj-mhpj) | Backend schema handling uses identifier-safe SQL composition and validation. |
| M1 — Federation nonce cache lifetime | Medium | None; documented per policy | Nonce cache lifetime is at least as long as the accepted token lifetime. |
| M2 — Federation token issuer validation | Medium | None; documented per policy | Issuer handling has explicit validation coverage. |
| M3 — Federation token time-claim validation | Medium | None; documented per policy | Time-claim handling has explicit validation coverage, including Hypothesis fuzz coverage. |
| M4 — Legacy SHA-256 API key acceptance deadline | Medium | None; documented per policy | Legacy SHA-256 API key acceptance has a configurable deadline and regression coverage. |
| M5 — OIDC ID-token algorithm allowlist | Medium | None; documented per policy | OIDC ID-token algorithm handling uses a configurable allowlist. |
| M6 — SQLite database and sidecar permissions | Medium | None; documented per policy | SQLite database and sidecar files use restrictive permissions at creation time. |
| M7 — CLI write-out path permissions | Medium | None; documented per policy | CLI write-out paths use restrictive permissions. |
| M8 — Rate-limit kill-switch acknowledgement | Medium | None; documented per policy | Production-risky quota-disablement requires explicit operator acknowledgement and remains covered by deployment guidance. |
| M9 — Federation message validation | Medium | None; documented per policy | Federation message state transitions have validation coverage and are documented as a Medium security disposition. |
| L1 — Development CORS startup warning | Low | None; documented per policy | Development CORS posture emits a startup warning when enabled. |
| L2 — Embedding-provider error redaction | Low | None; documented per policy | Embedding-provider errors no longer log sensitive provider detail. |
| L3 — Audit posture documentation by trust mode | Low | None; documented per policy | Audit evidence posture is documented by trust mode and backend. |
| L4 — Federation clock-skew leeway | Low; folded into M2/M3 | None; documented per policy | Clock-skew behavior is covered by federation token validation hardening. |
| L5 — OIDC discovery URL validation | Low | None; documented per policy | OIDC discovery URL handling validates outbound locations and is documented as a Low security disposition. |

Detailed PR, path, test, and evidence lineage for this audit is recorded in [`docs/internal/security-evidence-registry-2026-05-17.md`](docs/internal/security-evidence-registry-2026-05-17.md). Architectural risk classes derived from C2, H1, and H2 are registered as R-24, R-25, and R-26 in [`spec/security/threat-model.md`](spec/security/threat-model.md).

---

### Group A — Resolved by dependency upgrade sweeps (27 alerts)

The dependency upgrade sweeps upgraded the following packages to patched versions. Dependabot alerts will auto-close on the next GitHub rescan after the relevant branch merges.

#### Next.js (`experimental/dashboard/`, deferred per ADR-002) — 18 alerts

The Next.js curator dashboard (`experimental/dashboard/`) was pinned at Next.js 14 and accumulated CVEs from three major Next.js disclosure cycles. The pre-v0.9.0a1 dep sweep upgraded it to `next@15.5.15`. Follow-up upgrades to `next@15.5.16` and then `next@16.2.6` landed the patches for [GHSA-8h8q-6873-q5fj](https://github.com/advisories/GHSA-8h8q-6873-q5fj) and [GHSA-26hh-7cqf-hhc6](https://github.com/advisories/GHSA-26hh-7cqf-hhc6).

| Alert | Severity | CVE / GHSA | Summary | Resolution |
| ----- | -------- | --- | ------- | ---------- |
| #44 | HIGH | GHSA-26hh-7cqf-hhc6 / CVE-2026-45109 | Middleware / Proxy bypass in App Router applications via segment-prefetch routes | `next@16.2.6` ≥ patched `16.2.6` |
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

> **Deployment gate:** The dashboard at `experimental/dashboard/` is deferred per ADR-002 and is not deployed to production at v0.9.0a2. Even so, all CVEs above are fixed in the installed version. No deployment should occur on any prior version.

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

#### Mermaid (`docs/package-lock.json`) — 4 alerts

The documentation site uses Mermaid through Docusaurus to render diagrams from repository-controlled Markdown/MDX sources. A 2026-05-12 follow-up lockfile refresh resolves Mermaid to `11.15.0`, which contains the upstream fixes for the following advisories.

| Alert | Severity | CVE / GHSA | Summary | Resolution |
| ----- | -------- | ---------- | ------- | ---------- |
| #43 | MEDIUM | GHSA-6m6c-36f7-fhxh / CVE-2026-41150 | Gantt chart infinite loop denial of service | `mermaid@11.15.0` ≥ patched `11.15.0` |
| #42 | MEDIUM | GHSA-ghcm-xqfw-q4vr / CVE-2026-41149 | State diagram `classDef` HTML injection | `mermaid@11.15.0` ≥ patched `11.15.0` |
| #41 | MEDIUM | GHSA-xcj9-5m2h-648r / CVE-2026-41148 | Diagram `classDef` CSS injection | `mermaid@11.15.0` ≥ patched `11.15.0` |
| #40 | MEDIUM | GHSA-87f9-hvmw-gh4p / CVE-2026-41159 | Mermaid configuration CSS injection | `mermaid@11.15.0` ≥ patched `11.15.0` |

**No new R-XX risk entries** in the threat model: these were dependency advisories that have been patched in the installed dependency tree. The docs build still renders trusted, repository-controlled sources; there is no new residual architectural risk to track in `spec/security/threat-model.md`.

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

#### Group C, sub-category: acknowledged risks (ADR-tracked remediation)

Some CodeQL alerts are **not** precision-gap false positives — the analyzer is correct, but the flagged code is a deliberate, documented choice whose retirement is committed in an ADR. These are tracked separately because their lifecycle is different: they remain open or dismissed-as-acknowledged until the ADR's retirement milestone, at which point the code disappears and the alert auto-closes on the next scan.

| Alert | Rule | Location | Severity | Rationale | Retirement milestone |
| ----- | ---- | -------- | -------- | --------- | -------------------- |
| [#34](https://github.com/eidetic-labs/stigmem/security/code-scanning/34) | `py/weak-sensitive-data-hashing` | `auth.py:67` — `_legacy_sha256(raw)` and the legacy branch in `_verify_key_hash` | High | [PR #172](https://github.com/eidetic-labs/stigmem/pull/172) implemented the [ADR-007](docs/adr/007-argon2id.md) Argon2id migration with a dual-mode verification window. New keys use Argon2id; legacy v0.9.0a1 SHA-256 rows verify against `_legacy_sha256` on first use, then opportunistically re-hash to Argon2id (`api_key_rehashed` audit event). Deleting the function today would invalidate every v0.9.0a1-issued API key. | **v1.0.0 GA** — bulk re-hash migration deletes `_legacy_sha256`; CodeQL re-scan auto-closes alert. |

**Disposition:** Alert #34 dismissed in GitHub UI with reason `won't fix`; dismissal comment points at [`spec/security/audit-triage.md`](spec/security/audit-triage.md) § "CodeQL — acknowledged risks" for the full rationale.

**Audit-trail visibility for operators:** track Argon2id migration progress with
```sql
SELECT COUNT(*) FROM fact_audit_log WHERE event_type = 'api_key_rehashed';
```
Every legacy row that gets used at least once during the v0.9.x window contributes one row. At v1.0.0 GA the remaining un-used legacy rows are forced through rotation as part of the retirement migration.

---

### Core Node (Python/FastAPI)

The stigmem reference node (`stigmem/node/`) is implemented in Python with FastAPI and SQLite. It has no JavaScript dependency tree. No Python Dependabot alerts are open as of 2026-05-03. Python dependencies are managed via `uv` and `pyproject.toml`; `uv.lock` is checked in.

---

### Security Controls in Effect (v0.9.0a2)

> The controls listed here are **dependency- and code-level controls** that are in effect at v0.9.0a2. **Federation-level and threat-model-level controls** named in the posture-reset banner at the top of this section (mTLS-default, audit log, rate limits, capability validation, bounded HLC skew, storage-immutability stack) are **not yet in effect** and remain future hardened-core work, not an active beta milestone.

- **Authentication:** API keys enforced on all write endpoints; per-scope restrictions supported by `Spec-02-Scopes-and-ACL` and `Spec-06-Capability-Tokens`.
- **Federation:** Peer handshake uses Ed25519 signing; replay attack resistance via HLC timestamps per `Spec-05-Federation-Trust` and `Spec-11-Replay-Protection`.
- **Input validation:** Pydantic models on all HTTP endpoints; malformed payloads return 422 before reaching business logic.
- **Secrets:** No credentials are committed to the repository. Docker Compose uses environment variable injection.
- **Container image retention:** Every released container image (`:0.9.0aN`, `:0.9.0bN`, `:1.0.0rcN`, `:1.0.0`, plus the semver-strict spellings) is **retained on GHCR indefinitely**, so an audit trail back to any historical release remains verifiable. Rolling pointers (`:latest`, `:edge`) are retained forever; short-SHA forensics tags are pruned after 90 days. Sigstore signatures are retained alongside their target image. See the [tag-selection guide](https://docs.stigmem.dev/operators/deployment/install#image-tags) for choosing the right pin for your deployment.
- **CI:** Dependabot alerts are monitored; `pip-audit`, `pnpm audit`, `bandit`, and CodeQL run as blocking CI steps on every PR (see Audit Tooling below).

---

### Audit Tooling

All four tools run as blocking steps in `.github/workflows/ci.yml` on every push and pull request.

| Tool | Scope | What it checks | CI step |
| ---- | ----- | -------------- | ------- |
| `pip-audit` | Python dependencies (`uv.lock`) | Known CVEs in installed packages via PyPI advisory database | `python-tests` job — exits non-zero on any moderate+ finding |
| `pnpm audit` | Node.js dependencies (`pnpm-lock.yaml`) | Known CVEs via npm advisory database | `node-tests` job — `--audit-level=moderate` |
| `bandit` | Python source (`node/src/`, `sdks/stigmem-py/src/`) | Common Python security anti-patterns (injection, weak crypto, unsafe deserialization) | `python-tests` job — configured via `[tool.bandit]` in `pyproject.toml`; `B101` (assert usage) suppressed for test code |
| `CodeQL` | Python + JavaScript/TypeScript + Go + GitHub Actions sources | Semantic dataflow / taint analysis: SQL injection, ReDoS, hardcoded secrets, prototype pollution, … (via GitHub Advanced Security) | `analyze (python / javascript-typescript / go / actions)` jobs — alerts surfaced in [Security → Code scanning](https://github.com/eidetic-labs/stigmem/security/code-scanning); triage rationale recorded in Group C above and in [`spec/security/audit-triage.md`](spec/security/audit-triage.md) |

**Running locally:**

```bash
# Python dependency audit
uv run pip-audit

# Python static analysis
uv run bandit -r node/src/ sdks/stigmem-py/src/ -c pyproject.toml

# Node.js dependency audit
pnpm audit --audit-level=moderate
```

The docs build toolchain (`docusaurus-plugin-openapi-docs` and its transitive dependencies) generates known alerts in `pnpm audit` output. These are suppressed per the Group B analysis above — they are build-time only and have no user-controlled input pathway. The root `turbo` development tool advisory [GHSA-hcf7-66rw-9f5r](https://github.com/advisories/GHSA-hcf7-66rw-9f5r) is also suppressed until a patched stable package is available on npm; it is a local/CI orchestration dependency and is not included in published Stigmem artifacts.
