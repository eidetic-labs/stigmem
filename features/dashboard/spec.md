# Dashboard Spec

The dashboard is an experimental web UI for curating and inspecting Stigmem
state. It is implemented as a Next.js application with authenticated routes,
client providers, API helpers, UI primitives, and browser smoke coverage.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `src/app/login/page.tsx` | Login entry point for the curator dashboard. |
| `src/app/(authed)/layout.tsx` | Authenticated application shell. |
| `src/app/page.tsx` | Main dashboard route. |
| `src/components/nav.tsx` | Navigation UI for the dashboard shell. |
| `src/components/providers.tsx` | Client-side provider setup. |
| `src/lib/api.ts` | Dashboard API helper code. |
| `src/lib/session.ts` | Session helper code. |
| `src/lib/oidc.ts` | OIDC helper code. |
| `src/proxy.ts` | Next.js proxy/middleware boundary. |

## Runtime Configuration

The dashboard uses the `experimental/dashboard/.env.local.example` template for
local environment configuration. The package metadata and scripts live in
`experimental/dashboard/package.json`.

## Test Surfaces

| Path | Coverage |
| --- | --- |
| `src/components/nav.test.tsx` | Navigation component behavior. |
| `src/lib/api.test.ts` | API helper behavior. |
| `src/lib/session.test.ts` | Session helper behavior. |
| `src/lib/utils.test.ts` | Utility behavior. |
| `tests/e2e/auth.spec.ts` | Playwright authentication smoke path. |

## Out of Scope

- Production deployment in the current alpha artifact set.
- Publishing a dashboard container image.
- Replacing operator CLI/API workflows.
- Declaring the dashboard stable before dependency, auth/session, and
  live-node validation gates complete.

## Spec Assignment

There is no Spec-X assignment for the dashboard. It is experimental internal
tooling rather than a protocol-bearing feature.
