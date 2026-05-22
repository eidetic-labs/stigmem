# Dashboard Security

The dashboard is a deferred authenticated web UI. Its security posture depends
on session handling, OIDC configuration, dependency security, careful deployment
gates, and least-privilege access to Stigmem APIs.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Deferred deployment | The dashboard is not deployed to production in the current alpha surface. | `SECURITY.md`; `experimental/dashboard/STATUS.md` |
| Dependency remediation | Next.js dependency alerts were remediated through `next@16.2.6`. | `SECURITY.md`; `experimental/dashboard/package.json` |
| Session handling | Session helper code and tests exist under the dashboard source tree. | `experimental/dashboard/src/lib/session.ts`; `experimental/dashboard/src/lib/session.test.ts` |
| OIDC helper surface | OIDC helper code exists under the dashboard source tree. | `experimental/dashboard/src/lib/oidc.ts` |
| Browser smoke | A Playwright auth smoke exists for the login path. | `experimental/dashboard/tests/e2e/auth.spec.ts` |

## Security References

The dashboard has no dedicated R-* audit item, but it has a recorded
dependency-security history in `SECURITY.md` for resolved Next.js advisories and
deployment gating.

## Advisories and Findings

No active dashboard advisory is recorded. Historical Next.js dependency alerts
for `experimental/dashboard` are documented as resolved in `SECURITY.md`.

## Residual Risk

- Auth/session behavior has not been revalidated for promotion in the current
  release line.
- Live-node browser validation is not complete.
- Major-version holds for dashboard runtime and test tooling remain future
  hardening work.
- Deployment posture remains undefined because the dashboard is not a supported
  alpha artifact.

## Operator Guidance

- Do not deploy the dashboard from an older Next.js version than the patched
  version documented in `SECURITY.md`.
- Treat dashboard deployment as unsupported until the future-alpha promotion
  gates are complete.
- Review auth/session, OIDC, and API access scope before enabling the dashboard
  against a live Stigmem node.
