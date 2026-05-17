# Dependency Currency — Best Practices

> Dependency currency is not the same as vulnerability management. Vulnerability scanners answer "is this known-bad?" Currency checks answer "are we accumulating upgrade debt that may hide future security fixes?"

## Policy

- Runtime dependencies behind latest are tracked.
- Security-sensitive dependencies behind latest are prioritized even if transitive.
- Major-version holds are allowed only with a documented rationale and review date.
- Lockfile refreshes happen on regular maintenance branches, not only during feature work.
- Currency checks run weekly, before release candidates, and after security advisories in relevant ecosystems.
- Every package reported below latest gets an explicit disposition: update now, evaluate in a compatibility PR, document as an intentional hold, or confirm that the lockfile already resolves to latest.

## Security-Sensitive Package Classes

Treat these as high-priority currency targets:

- cryptography, TLS, JWT, signing, key-management packages
- HTTP clients and server frameworks
- auth/session/cookie packages
- OpenAPI/code-generation packages that shape wire contracts
- container/image/SBOM tooling
- database drivers
- cloud SDKs that receive sensitive data
- LLM/embedding SDKs
- protocol adapter SDKs and validation libraries at trust boundaries
- bundlers, CSS/processors, and JavaScript build tools that parse untrusted or semi-trusted project input

## Required Checks

JavaScript workspace:

```bash
pnpm outdated -r --format json
pnpm audit --audit-level=moderate
```

Non-workspace npm packages:

```bash
cd docs && npm outdated --json
cd adapters/obsidian-plugin && npm outdated --json
```

Python:

```bash
uv tree --outdated --all-groups --no-progress
uv run pip-audit --progress-spinner off
```

Go:

```bash
go list -m -u all
govulncheck ./...
```

Run Go checks only when the Go toolchain is installed and the module has dependencies.

## Major-Version Hold Register

Create a table in the repo or release tracker for every intentional hold:

| Package | Current major | Latest major | Surface | Reason held | Security impact | Required tests before bump | Owner | Review by |
|---|---:|---:|---|---|---|---|---|---|

Stigmem's active hold table lives in
[`docs/internal/major-version-holds.md`](major-version-holds.md).

Examples from the 2026-05-06 scan:

- React 18 while Docusaurus/dashboard compatibility is validated.
- Next 15 while Next 16 migration is planned.
- Tailwind 3 while Tailwind 4 migration is planned.
- Zod 3 while schema API compatibility is reviewed.
- TypeScript 5 while TypeScript 6 is validated against all packages.
- Vite 6 while Vite 8/Vitest compatibility is reviewed.
- Node 20 typings while Node 20 remains the support floor.

## Upgrade Order

1. Patch/minor updates for runtime security-sensitive packages.
2. Patch/minor updates for build and test tooling.
3. Optional-cloud SDKs that handle sensitive data.
4. Major-version framework migrations, each as its own PR with focused tests.
5. Transitive-only lag through upstream-compatible dependency bumps.

## Node/JavaScript Security-Hardening Disposition

For each `pnpm outdated` or `npm outdated` row, record:

- package and dependent workspace
- whether it is runtime, build/test, docs, or transitive-only
- whether it touches auth/session, protocol validation, contract generation, parsing/bundling, or web framework behavior
- latest-version gap and whether the gap is patch/minor or major
- decision: update, evaluate, hold, or lockfile-confirm
- tests required for that decision

Recommended Stigmem Node review groups:

- **Patch/build update:** `postcss`, `turbo`, then `esbuild` after TS SDK bundling smoke.
- **Runtime security review:** `next`, `iron-session`, `@modelcontextprotocol/sdk`, `zod`, Radix dashboard components, and TanStack Query.
- **Framework migrations:** React 19, Next 16, Tailwind 4, TypeScript 6, Vite 8, and jsdom 29 as separate focused PRs.
- **Runtime-aligned holds:** `@types/node` while Node 20 remains the supported runtime.
- **Docs compatibility holds:** React 18 in Docusaurus until docs build and plugin compatibility validate React 19.

## Reporting

Each currency scan should produce:

- command/date
- direct runtime packages behind latest
- dev/build packages behind latest
- transitive security-sensitive packages behind latest
- intentional major-version holds
- disposition for every package not confirmed on latest
- recommended next PRs

Store dated scan reports under `docs/internal/` or `stigmem/analyses/` while planning is still internal.
