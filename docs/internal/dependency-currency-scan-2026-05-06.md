# Dependency Currency Scan — 2026-05-06

**Repository scanned:** Stigmem `origin/main` at `6cad138` via a temporary archive export from `/Users/bjones/Desktop/stigmem`  
**Purpose:** identify packages that resolve below the latest registry version and should be tracked as possible security-maintenance work.  
**Commands used:**

- `pnpm outdated -r --format json`
- `npm outdated --json` in `docs/`
- `npm outdated --json` in `adapters/obsidian-plugin/`
- `uv tree --outdated --all-groups --no-progress`

`go` was not installed in the local environment, and `sdks/stigmem-go/go.mod` has no third-party module requirements beyond the module declaration. The local Stigmem working tree was not modified.

> 2026-05-17 adoption note: this report is committed as the latest completed
> scan artifact from Internal-Comms. Some package rows have already changed in
> code, including the dashboard move to Next 16 and Node 24 support. Current
> intentional major-version holds are tracked in
> `docs/internal/major-version-holds.md`; future scheduled workflow artifacts
> supersede this snapshot.

---

## Summary

Stigmem already runs vulnerability-oriented checks (`pip-audit`, `pnpm audit`, container SBOM smoke). The gap is **currency tracking**: several packages are intentionally or accidentally below latest even when no advisory is present. Currency is not the same as vulnerability status, but stale dependencies increase future patch pressure and can hide security fixes behind "routine upgrade" work.

Recommended policy:

- Track direct runtime dependencies behind latest as maintenance/security risk.
- Treat pinned major-version holds as intentional only when documented with rationale and review date.
- Review transitive-only lag through existing audit/SBOM tooling unless an advisory or ecosystem risk requires direct action.
- Run dependency-currency checks at least weekly and before release candidates.
- Evaluate each Node/JavaScript latest-version gap as part of security hardening, using `node-dependency-security-hardening-2026-05-06.md` as the package-by-package disposition register.

---

## JavaScript / TypeScript Workspace (`pnpm outdated -r`)

`pnpm outdated -r --format json` reported `wanted` and `latest`; it did not include an installed `current` field in this environment. Rows where `wanted == latest` are not latest-version holds; they indicate the declared range can resolve to latest and the lockfile/install state should be refreshed or confirmed.

### Runtime dependency currency report

| Package | Wanted | Latest | Dependent package | Notes |
|---|---:|---:|---|---|
| `@modelcontextprotocol/sdk` | `1.29.0` | `1.29.0` | `adapters/mcp` | Range allows latest; lock/update may be needed if installed version is older. |
| `@radix-ui/react-dialog` | `1.1.15` | `1.1.15` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@radix-ui/react-label` | `2.1.8` | `2.1.8` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@radix-ui/react-select` | `2.2.6` | `2.2.6` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@radix-ui/react-slot` | `1.2.4` | `1.2.4` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@tanstack/react-query` | `5.100.9` | `5.100.9` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `iron-session` | `8.0.4` | `8.0.4` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `next` | `15.5.15` | `16.2.5` | `apps/dashboard` | Major-version hold; document rationale or plan upgrade. |
| `react` | `18.3.0` | `19.2.6` | `apps/dashboard` | Major-version hold; coupled to Next and Docusaurus compatibility. |
| `react-dom` | `18.3.0` | `19.2.6` | `apps/dashboard` | Major-version hold; coupled to React. |
| `tailwind-merge` | `2.6.1` | `3.5.0` | `apps/dashboard` | Major-version hold; review changelog. |
| `lucide-react` | `0.469.0` | `1.14.0` | `apps/dashboard` | Major-version hold; review icon API compatibility. |
| `zod` | `3.25.76` | `4.4.3` | `adapters/mcp`, `sdks/stigmem-ts` | Major-version hold; schema API compatibility review needed. |

### Development dependency currency report

| Package | Wanted | Latest | Dependent package(s) | Notes |
|---|---:|---:|---|---|
| `@playwright/test` | `1.59.1` | `1.59.1` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@testing-library/react` | `16.3.2` | `16.3.2` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `@vitest/coverage-v8` | `4.1.5` | `4.1.5` | `adapters/mcp`, `apps/dashboard`, `sdks/stigmem-ts` | Range allows latest; lock/update may be needed. |
| `autoprefixer` | `10.5.0` | `10.5.0` | `apps/dashboard` | Range allows latest; lock/update may be needed. |
| `openapi-typescript` | `7.13.0` | `7.13.0` | `sdks/stigmem-ts` | Range allows latest; lock/update may be needed. |
| `postcss` | `8.5.13` | `8.5.14` | `apps/dashboard` | Patch update; should be low-risk. |
| `turbo` | `2.9.7` | `2.9.9` | root | Patch update; should be low-risk. |
| `tsx` | `4.21.0` | `4.21.0` | `adapters/mcp` | Range allows latest; lock/update may be needed. |
| `vitest` | `4.1.5` | `4.1.5` | `adapters/mcp`, `apps/dashboard`, `sdks/stigmem-ts` | Range allows latest; lock/update may be needed. |
| `esbuild` | `0.25.12` | `0.28.0` | `sdks/stigmem-ts` | Minor update; review bundling smoke. |
| `jsdom` | `26.1.0` | `29.1.1` | `apps/dashboard` | Major update; test environment compatibility review. |
| `tailwindcss` | `3.4.19` | `4.2.4` | `apps/dashboard` | Major-version hold; Tailwind 4 migration required. |
| `typescript` | `5.9.3` | `6.0.3` | root, MCP, dashboard, TS SDK | Major-version hold; type-check all packages before upgrade. |
| `vite` | `6.4.2` | `8.0.10` | MCP, dashboard, TS SDK | Major-version hold; review plugin/test compatibility. |
| `@types/node` | `20.19.39` | `25.6.0` | `adapters/mcp` | Intentional if Node 20 is the support floor; document as runtime-aligned hold. |
| `@types/react` | `18.3.0` | `19.2.14` | `apps/dashboard` | Intentional while React 18 is held. |
| `@types/react-dom` | `18.3.0` | `19.2.3` | `apps/dashboard` | Intentional while React 18 is held. |

### Docs package (`npm outdated` in `docs/`)

`npm outdated --json` also reported `wanted` and `latest`. Most docs packages are already at latest by range; the only true latest-version holds are React and React DOM:

| Package | Wanted | Latest | Notes |
|---|---:|---:|---|
| `react` | `18.3.1` | `19.2.6` | Docusaurus 3.10 is commonly React-18 compatible; document hold until docs build validates React 19. |
| `react-dom` | `18.3.1` | `19.2.6` | Same. |

### Obsidian plugin package

`npm outdated --json` returned `{}`. No outdated direct package was reported for `adapters/obsidian-plugin`.

---

## Python (`uv tree --outdated --all-groups`)

Direct or security-relevant packages behind latest:

| Package | Resolved | Latest | Surface | Notes |
|---|---:|---:|---|---|
| `pydantic` | `2.13.3` | `2.13.4` | runtime | Patch update; low-risk but touches API models. |
| `pydantic-core` | `2.46.3` | `2.46.4` | transitive runtime | Follows `pydantic`. |
| `cryptography` | `47.0.0` | `48.0.0` | runtime via `PyJWT[crypto]` | Security-sensitive dependency; review changelog and run auth/federation tests. |
| `openai` | `2.33.0` | `2.35.0` | optional cloud embedding | Optional feature, but external-service SDKs should stay current. |
| `mypy` | `1.20.2` | `2.0.0` | dev tooling | Major update; review baseline behavior before bump. |
| `librt` | `0.9.0` | `0.10.0` | transitive dev | Follows mypy/runtime dependency chain. |
| `protobuf` | `6.33.6` | `7.34.1` | transitive observability | Major update through OpenTelemetry stack; do not bump independently without OTel compatibility review. |
| `importlib-metadata` | `8.7.1` | `9.0.0` | transitive observability | Low direct risk on Python 3.11+, but appears in OTel stack. |
| `pip` | `26.1` | `26.1.1` | transitive dev via `pip-audit` | Patch update in tooling environment. |
| `markdown-it-py` | `4.0.0` | `4.1.0` | transitive dev via `rich`/`bandit` | Tooling only. |

The root `infra/soak/requirements.txt` is range-based (`cryptography>=42.0`, `PyJWT[crypto]>=2.8`, `requests>=2.32`), so currency depends on the environment resolver. The security-sensitive item is still `cryptography`; the scan above resolved `47.0.0` while latest is `48.0.0`.

---

## Go

`sdks/stigmem-go/go.mod` declares only:

```text
module github.com/eidetic-labs/stigmem-go
go 1.22
```

No third-party Go modules were present to check. Local `go` was not installed, so no registry command was run.

---

## Recommended Follow-Up Issues

1. **Dependency currency gate:** add a scheduled/manual workflow that runs `pnpm outdated -r`, `npm outdated` for non-workspace packages, and `uv tree --outdated --all-groups`; uploads a report artifact.
2. **Runtime patch bump:** evaluate and update `pydantic`, `pydantic-core`, `cryptography`, `openai`, `postcss`, and `turbo` first.
3. **Node security-hardening review:** evaluate every Node package listed above and record an explicit disposition: update, evaluate in focused PR, hold with owner/review date, or lockfile-confirm latest.
4. **Major-version holds register:** document intentional holds for React 18, Next 15, Tailwind 3, Zod 3, TypeScript 5, Vite 6, Node 20 typings, and Docusaurus React 18.
5. **Security-sensitive dependency policy:** treat `cryptography`, auth/token libraries, HTTP clients, web frameworks, OpenAPI generators, validation libraries, bundlers/parsers, container tooling, and embedding/cloud SDKs as high-priority currency targets.
6. **Lockfile refresh cadence:** run lockfile refreshes on a regular maintenance branch rather than letting them accumulate behind feature work.
