# Node Dependency Security Hardening Review — 2026-05-06

**Source scan:** `dependency-currency-scan-2026-05-06.md` against Stigmem `origin/main` at `6cad138`.

> 2026-05-17 adoption note: this disposition review is the latest completed
> Internal-Comms artifact. It remains useful as the work-split baseline, but rows
> should be rechecked against the scheduled dependency-currency workflow before
> starting each upgrade PR.

## Purpose

Evaluate each Node/JavaScript package that is not clearly on latest, and decide whether it should be updated as part of security hardening, held with rationale, or confirmed through lockfile refresh.

Security hardening should not mean blindly taking every major version. It should mean:

- no unreviewed runtime package is behind latest
- every security-sensitive package has an explicit update or hold decision
- every major-version hold has an owner, rationale, test scope, and review date
- low-risk patch/minor updates are handled before larger framework migrations

## Recommended Work Split

1. **Lockfile confirmation PR:** run clean installs and lockfile refreshes for packages where `wanted == latest`.
2. **Low-risk update PR:** update `postcss`, `turbo`, and evaluate `esbuild` with SDK bundling tests.
3. **Runtime security review PR:** evaluate `next`, `iron-session`, `@modelcontextprotocol/sdk`, Radix packages, TanStack Query, and Zod from a security and compatibility standpoint.
4. **Framework migration planning PRs:** separately evaluate React 19, Next 16, Tailwind 4, TypeScript 6, Vite 8, and jsdom 29.
5. **Hold-register PR:** document any package that remains below latest after review.

## Runtime Dependencies

| Package | Surface | Wanted | Latest | Security-hardening decision |
|---|---|---:|---:|---|
| `@modelcontextprotocol/sdk` | MCP adapter protocol boundary | `1.29.0` | `1.29.0` | Confirm installed/lockfile state; keep on weekly currency report because this is a protocol-facing adapter. |
| `@radix-ui/react-dialog` | Dashboard UI | `1.1.15` | `1.1.15` | Confirm lockfile state; low direct security risk, but include in dashboard smoke. |
| `@radix-ui/react-label` | Dashboard UI | `2.1.8` | `2.1.8` | Confirm lockfile state; low direct security risk. |
| `@radix-ui/react-select` | Dashboard UI | `2.2.6` | `2.2.6` | Confirm lockfile state; include in dashboard interaction smoke. |
| `@radix-ui/react-slot` | Dashboard UI | `1.2.4` | `1.2.4` | Confirm lockfile state; low direct security risk. |
| `@tanstack/react-query` | Dashboard API state | `5.100.9` | `5.100.9` | Confirm lockfile state; include auth/API dashboard smoke because query caching can affect stale privileged views. |
| `iron-session` | Dashboard auth/session | `8.0.4` | `8.0.4` | Confirm lockfile state; security-sensitive despite being latest by range. Keep in vulnerability and currency gates. |
| `next` | Dashboard web framework | `15.5.15` | `16.2.5` | Evaluate as security-hardening candidate, but do not batch with unrelated migrations. Review Next 16 security notes, run dashboard build, auth/session tests, and Playwright smoke. |
| `react` | Dashboard runtime | `18.3.0` | `19.2.6` | Hold only with documented compatibility rationale. Evaluate after Next 16/Docusaurus compatibility is known. |
| `react-dom` | Dashboard runtime | `18.3.0` | `19.2.6` | Same as React. |
| `tailwind-merge` | Dashboard class merging | `2.6.1` | `3.5.0` | Evaluate with visual regression or focused component smoke; likely lower security priority than framework/auth packages. |
| `lucide-react` | Dashboard icons | `0.469.0` | `1.14.0` | Evaluate as maintenance debt; low security priority unless advisory appears. |
| `zod` | MCP and TS SDK validation | `3.25.76` | `4.4.3` | High-priority compatibility/security review because validation shapes API boundaries. Test MCP input validation, generated SDK types, and schema error behavior before upgrading. |

## Development and Build Dependencies

| Package | Surface | Wanted | Latest | Security-hardening decision |
|---|---|---:|---:|---|
| `@playwright/test` | Browser tests | `1.59.1` | `1.59.1` | Confirm lockfile state; keep current because browser automation ships frequent security-related dependency updates. |
| `@testing-library/react` | Component tests | `16.3.2` | `16.3.2` | Confirm lockfile state. |
| `@vitest/coverage-v8` | Test coverage | `4.1.5` | `4.1.5` | Confirm lockfile state. |
| `autoprefixer` | CSS build | `10.5.0` | `10.5.0` | Confirm lockfile state. |
| `openapi-typescript` | Contract generation | `7.13.0` | `7.13.0` | Confirm lockfile state; treat as contract-sensitive because generator changes can affect SDK output. |
| `postcss` | CSS processing | `8.5.13` | `8.5.14` | Update in low-risk patch PR; CSS parsers/processors should not lag without reason. |
| `turbo` | Monorepo build orchestration | `2.9.7` | `2.9.9` | Update in low-risk patch PR; run all local lanes and CI path-filter smoke. |
| `tsx` | TS execution tooling | `4.21.0` | `4.21.0` | Confirm lockfile state. |
| `vitest` | Test runner | `4.1.5` | `4.1.5` | Confirm lockfile state. |
| `esbuild` | TS SDK bundling | `0.25.12` | `0.28.0` | Evaluate soon; bundlers receive security-relevant fixes. Run TS SDK build and generated package smoke. |
| `jsdom` | Dashboard test environment | `26.1.0` | `29.1.1` | Evaluate as a separate test-infra PR; major changes can alter DOM behavior. |
| `tailwindcss` | CSS framework | `3.4.19` | `4.2.4` | Major migration; hold only with owner/review date and visual regression plan. |
| `typescript` | Type checker/compiler | `5.9.3` | `6.0.3` | Major migration; evaluate with all workspace type checks and SDK generation. |
| `vite` | Build/test tooling | `6.4.2` | `8.0.10` | Major migration; evaluate with MCP, dashboard, and TS SDK builds/tests. |
| `@types/node` | Node type surface | `20.19.39` | `25.6.0` | Document as an intentional hold if Node 20 remains the support floor. Revisit when runtime support policy changes. |
| `@types/react` | React type surface | `18.3.0` | `19.2.14` | Hold only while React 18 is held. |
| `@types/react-dom` | React DOM type surface | `18.3.0` | `19.2.3` | Hold only while React 18 is held. |

## Docs and Obsidian Packages

| Package/surface | Finding | Security-hardening decision |
|---|---|---|
| Docs React / React DOM | Docs hold React 18 while latest is React 19. | Evaluate with Docusaurus build and docs search/openapi plugin smoke. Document hold until Docusaurus compatibility is proven. |
| Obsidian plugin | `npm outdated --json` returned `{}`. | No direct package update required from this scan. Keep npm audit and lockfile freshness in scheduled checks. |

## Required Acceptance Criteria

- Every Node package in this review has one of: updated, lockfile-confirmed latest, or documented hold.
- Security-sensitive packages (`iron-session`, `next`, `zod`, `@modelcontextprotocol/sdk`, `openapi-typescript`, `esbuild`) have explicit changelog/advisory review notes.
- Major holds include owner and review date.
- Dashboard build, Playwright smoke, MCP tests, TS SDK build/tests, and docs build pass for the relevant PRs.
- Dependency currency workflow publishes the current report artifact after the decisions land.
