# Dashboard Status

The dashboard is deferred for the current alpha artifact set. Source, package
metadata, unit tests, and a Playwright smoke exist, but release-line validation
and deployment posture are not complete.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `internal` |
| Owner | `unowned` |
| Package | `dashboard` |
| Implementation | `experimental/dashboard` |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Experimental dashboard source existed outside the supported artifact set. | `experimental/dashboard/STATUS.md`; `experimental/dashboard/package.json` |
| `0.9.xA` planned | Keep the dashboard discoverable while dependency, auth/session, live-node, and deployment gates remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Source inventory | Complete | Next.js app, UI components, helpers, tests, and Dockerfile exist under `experimental/dashboard`. |
| Feature record | Complete | ADR-020 feature record added under `features/dashboard`. |
| Dependency security | Partial | Recorded Next.js CVE remediation exists, but dependency currency remains an active future-alpha gate. |
| Auth/session validation | Open | Dashboard auth/session behavior needs release-line review before promotion. |
| Live-node validation | Open | No current live-node dashboard validation is recorded. |
| Deployment posture | Open | Dashboard image publication and production deployment remain out of current scope. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- The dashboard is not part of the supported alpha deployment surface.
- Live-node and browser validation need to be refreshed before promotion.
- React, Tailwind, Vite/Vitest, jsdom, and related major-version holds remain
  future hardening work.
