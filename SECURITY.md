# Security Policy

**Security resources:**
- [Community Pen-Test Handbook](https://docs.stigmem.dev/security/pen-test) — scope, safe harbor, report template, disclosure timeline, and recognition.
- [Threat Model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md) — trust boundaries, STRIDE analysis, risk register.

## Supported Versions

Stigmem follows the alpha-beta-rc pre-release convention per [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The first build of stigmem is `v0.9.0a1`; stable v1.0 has not shipped.

| Version | Supported |
| ------- | --------- |
| `0.9.0a*` (Phase A alpha series — current) | Yes — current pre-release line. **No stability guarantee.** Breaking changes during the hardening window are expected and documented in [CHANGELOG.md](CHANGELOG.md). |
| `0.9.0b*` (Phase B beta series — future) | Will be supported when published. |
| `1.0.0rc*` / `1.0.0` (Phase C / GA — future) | Will be supported when published. |
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

> **Posture-reset note.** Stigmem's `v1.0` announcement was withdrawn on 2026-05-08; the canonical version line was reset to `v0.9.0a1` per [ADR-001](docs/adr/001-versioning.md) and [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The dependency-alert triage in this section was originally compiled for `v1.0-rc` on 2026-05-03 and is **carried forward to v0.9.0a1** because the underlying dependency upgrades remain in effect — the same fixed package versions that resolved the alerts at v1.0-rc are still installed at v0.9.0a1. The supported-version posture changed (see "Supported Versions" above); the dependency-fix evidence did not.
>
> **Open security gaps named explicitly:** several controls our threat model identifies as required for stable production — mTLS-default federation, persistent audit log, per-principal rate limits, capability-level validation for cross-org instructions, bounded HLC skew enforcement, the storage-immutability stack ([ADR-016](docs/adr/016-storage-immutability-enforcement.md)) — are scheduled for Phase B and are **not yet in effect at v0.9.0a1**. Adopters running federation across organizational boundaries should wait for Phase B per [LIMITATIONS.md](LIMITATIONS.md).

This section documents the current security posture of the stigmem `v0.9.0a1` release, including a triage of all open Dependabot alerts against Eidetic-Labs/stigmem as of the 2026-05-03 v1.0-rc snapshot (carried forward; see note above).

### Summary

| Category | Count |
| -------- | ----- |
| Alerts addressed by the v1.0-rc dep upgrade sweep — pending GitHub rescan | 20 |
| Alerts in docs build toolchain (non-exploitable, suppressed) | 7 |
| Unaddressed / escalated blockers | 0 |

**Net result: zero unaddressed Dependabot alerts at v0.9.0a1** (same dependency-fix posture carried forward from the v1.0-rc 2026-05-03 snapshot). Note that Dependabot alerts are a *dependency* concern — separately from the threat-model risks named in the posture-reset banner above.

---

### Group A — Resolved by the dep upgrade sweep that landed pre-v0.9.0a1 (20 alerts)

The `chore(deps): TypeScript dep upgrade sweep + Node CVE remediation` commit upgraded the following packages to patched versions. Dependabot alerts will auto-close on the next GitHub rescan after the branch merges.

#### Next.js (apps/dashboard) — 16 alerts

The `apps/dashboard` Next.js curator dashboard was pinned at Next.js 14 and accumulated CVEs from three major Next.js disclosure cycles. The dep sweep upgraded it to `next@15.5.15`, which is the patched release for all outstanding CVEs.

| Alert | Severity | CVE | Summary | Resolution |
| ----- | -------- | --- | ------- | ---------- |
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

> **Deployment gate:** The `apps/dashboard` is marked "In progress" and is not deployed to production at v0.9.0a1. Even so, all CVEs above are fixed in the installed version. No deployment should occur on any prior version.

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

### Core Node (Python/FastAPI)

The stigmem reference node (`stigmem/node/`) is implemented in Python with FastAPI and SQLite. It has no JavaScript dependency tree. No Python Dependabot alerts are open as of 2026-05-03. Python dependencies are managed via `uv` and `pyproject.toml`; `uv.lock` is checked in.

---

### Security Controls in Effect (v0.9.0a1)

> The controls listed here are **dependency- and code-level controls** that are in effect at v0.9.0a1. **Federation-level and threat-model-level controls** named in the posture-reset banner at the top of this section (mTLS-default, audit log, rate limits, capability validation, bounded HLC skew, storage-immutability stack) are **not yet in effect** and are scheduled for Phase B.

- **Authentication:** API keys enforced on all write endpoints; per-scope restrictions supported (§3.5).
- **Federation:** Peer handshake uses Ed25519 signing; replay attack resistance via HLC timestamps (§6).
- **Input validation:** Pydantic models on all HTTP endpoints; malformed payloads return 422 before reaching business logic.
- **Secrets:** No credentials are committed to the repository. Docker Compose uses environment variable injection.
- **CI:** Dependabot alerts are monitored; `pip-audit`, `pnpm audit`, and `bandit` run as blocking CI steps on every PR (see Audit Tooling below).

---

### Audit Tooling

All three tools run as blocking steps in `.github/workflows/ci.yml` on every push and pull request.

| Tool | Scope | What it checks | CI step |
| ---- | ----- | -------------- | ------- |
| `pip-audit` | Python dependencies (`uv.lock`) | Known CVEs in installed packages via PyPI advisory database | `python-tests` job — exits non-zero on any moderate+ finding |
| `pnpm audit` | Node.js dependencies (`pnpm-lock.yaml`) | Known CVEs via npm advisory database | `node-tests` job — `--audit-level=moderate` |
| `bandit` | Python source (`node/src/`, `sdks/stigmem-py/src/`) | Common Python security anti-patterns (injection, weak crypto, unsafe deserialization) | `python-tests` job — configured via `[tool.bandit]` in `pyproject.toml`; `B101` (assert usage) suppressed for test code |

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
