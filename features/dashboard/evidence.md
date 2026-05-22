# Dashboard Evidence

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/dashboard/src/app/` | Next.js app routes, layouts, login route, and global styles. |
| `experimental/dashboard/src/components/` | Navigation, provider, and UI primitive components. |
| `experimental/dashboard/src/lib/` | API, OIDC, session, and utility helpers. |
| `experimental/dashboard/src/proxy.ts` | Proxy/middleware boundary for the dashboard app. |
| `experimental/dashboard/package.json` | Package metadata and build/test scripts. |
| `experimental/dashboard/Dockerfile` | Experimental container build path. |

## Test Evidence

| Path | Evidence |
| --- | --- |
| `experimental/dashboard/src/components/nav.test.tsx` | Navigation component unit test. |
| `experimental/dashboard/src/lib/api.test.ts` | API helper unit test. |
| `experimental/dashboard/src/lib/session.test.ts` | Session helper unit test. |
| `experimental/dashboard/src/lib/utils.test.ts` | Utility unit test. |
| `experimental/dashboard/tests/e2e/auth.spec.ts` | Playwright authentication smoke test. |

## Documentation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/dashboard/STATUS.md` | Legacy status pointer to this feature record. |
| `SECURITY.md` | Resolved Next.js dependency alert history and deployment gate for the deferred dashboard. |
| `docs/internal/dependency-currency.md` | Dependency-currency context for dashboard major-version holds. |
| `docs/internal/major-version-holds.md` | React, Tailwind, Vite, TypeScript, and jsdom hold rationale. |

## Validation Commands

Use repository docs checks for feature-record and projection validation:

```bash
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

Use dashboard-local checks when dependencies are installed:

```bash
npm --prefix experimental/dashboard run type-check
npm --prefix experimental/dashboard run test
npm --prefix experimental/dashboard run build
```

## Missing Evidence

- Current live-node browser validation is not complete.
- Current production-like deployment validation is not complete.
- Major-version hold migration evidence is not complete.
