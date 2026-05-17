# Major-Version Dependency Holds

This register records intentional major-version holds identified by the
2026-05-06 dependency-currency scan. It is a maintenance control, not a
vulnerability finding: a package can be advisory-clean and still represent
upgrade debt that needs an owner and review date.

| Package | Surface | Current major | Latest major at scan | Owner | Reason held | Security impact | Required tests before bump | Review by |
|---|---|---:|---:|---|---|---|---|---|
| `react`, `react-dom` | Experimental dashboard | 18 | 19 | Maintainers | Coupled to dashboard rendering and Docusaurus compatibility. | UI/runtime framework drift can hide future security fixes behind migration work. | Dashboard unit tests, Playwright smoke, docs build when docs React is included. | Before beta hardening complete |
| `react`, `react-dom` | Docusaurus docs | 18 | 19 | Maintainers | Docusaurus compatibility must be verified before React 19 adoption. | Docs-site dependency lag; no node runtime impact. | Docs build, search plugin smoke, OpenAPI docs rendering. | Before beta hardening complete |
| `tailwindcss` | Experimental dashboard | 3 | 4 | Maintainers | Tailwind 4 requires configuration and visual migration. | Low direct security impact; build-chain drift. | Dashboard build, component visual smoke, Playwright smoke. | Before beta hardening complete |
| `tailwind-merge` | Experimental dashboard | 2 | 3 | Maintainers | Class merge behavior can affect UI state styling. | Low direct security impact; accessibility/status styling should be checked. | Dashboard unit tests and targeted component smoke. | Before beta hardening complete |
| `lucide-react` | Experimental dashboard | 0 | 1 | Maintainers | Icon package API compatibility needs a focused UI pass. | Low direct security impact. | Dashboard build and visual smoke. | Before beta hardening complete |
| `zod` | MCP adapter and TypeScript SDK | 3 | 4 | Maintainers | Validation API compatibility affects external protocol boundaries. | Medium: validation behavior is security-relevant for untrusted inputs. | MCP validation tests, TS SDK tests, generated SDK type-check, contract smoke. | Before beta hardening complete |
| `typescript` | Root, MCP, dashboard, TS SDK, docs | 5 | 6 | Maintainers | TypeScript 6 can surface broad type-system and build changes. | Low direct runtime impact; high build confidence impact. | Full TypeScript type-check/build/test lanes. | Before beta hardening complete |
| `vite` | MCP, dashboard, TS SDK | 6 | 8 | Maintainers | Vite/Vitest ecosystem migration should be isolated. | Build/test tooling drift can delay security patches. | MCP, dashboard, and TS SDK tests plus package builds. | Before beta hardening complete |
| `jsdom` | Experimental dashboard tests | 26 | 29 | Maintainers | Test-environment migration can change DOM behavior. | Low direct runtime impact; affects reliability of UI regression tests. | Dashboard unit tests and Playwright smoke. | Before beta hardening complete |
| `@types/node` | MCP adapter | 20 | 25 | Maintainers | Kept aligned with supported runtime policy; repo runtime has since moved to Node 24 where applicable. | Type surface only; review when runtime policy changes. | MCP type-check and build. | Before beta hardening complete |

When one of these packages is upgraded, update or remove its row in the same PR
that validates the required tests.
