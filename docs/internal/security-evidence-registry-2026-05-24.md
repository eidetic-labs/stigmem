# Security Evidence Registry — 2026-05-24 qs Dependency Advisory

**Scope:** `qs` CVE-2026-8723 / GHSA-q8mj-m7cp-5q26 in Stigmem JavaScript
dependency trees after `v0.9.0a8`.
**Severity:** Moderate / Medium dependency advisory.
**Publication policy:** Documented in `SECURITY.md`; no Stigmem GHSA. Critical
and High Stigmem vulnerabilities use GHSA where applicable, while Medium and
Low findings are documented publicly unless a carve-out applies.

## Finding

`qs.stringify` can throw synchronously when called with
`arrayFormat: "comma"` and `encodeValuesOnly: true` on arrays containing
`null` or `undefined` entries. The upstream fixed release is `qs@6.15.2`.

## Impact Analysis

| Surface | State | Disposition |
| --- | --- | --- |
| Root pnpm workspace | Already resolved `qs@6.15.2` through `pnpm-workspace.yaml` and root `package.json` overrides. | No change required. |
| Docs npm toolchain | `docs/package-lock.json` contained transitive `qs@6.15.1` and `express/node_modules/qs@6.14.2`. | Patched by docs override and lockfile refresh. |
| Python reference node | No JavaScript dependency tree. | Not affected. |
| TypeScript SDK / MCP adapter runtime | Root pnpm lock resolves patched `qs@6.15.2`; no vulnerable `qs.stringify` option usage found. | Not affected after existing root pin. |
| Published static docs | Build output is static HTML/JS; the vulnerable docs dependency is build-time tooling. | No runtime exposure identified. |

## Remediation

| Path | Change |
| --- | --- |
| `docs/package.json` | Added `overrides.qs >=6.15.2`. |
| `docs/package-lock.json` | Refreshed lockfile so all docs-site `qs` resolutions use `6.15.2`; removed the nested Express `qs@6.14.2` copy. |
| `SECURITY.md` | Added the public Medium dependency advisory disposition. |
| `CHANGELOG.md` | Added the release-impact security summary under `Unreleased`. |

## Validation

```bash
npm install --package-lock-only --ignore-scripts
npm install --ignore-scripts
npm ls qs
```

`npm ls qs` confirms Docusaurus, Express/body-parser, and
`docusaurus-theme-openapi-docs` all resolve to `qs@6.15.2`.

## ADR Alignment

- `SECURITY.md` remains the public security posture and advisory disposition
  projection per `docs/internal/documentation-ownership.md`.
- This evidence registry carries path, validation, and disposition detail so
  the public security file does not duplicate proof tables.
- No threat-model R-XX entry is added because this is a patched dependency
  advisory, not a new enduring Stigmem architectural risk class.
