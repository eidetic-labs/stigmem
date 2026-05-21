# OIDC SSO Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `opt-in` |

OIDC SSO exists in the reference node as an opt-in authentication bridge. It
remains experimental because production deployment depends on operator-specific
IdP configuration, domain policy, and security posture decisions.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | OIDC exchange behavior existed in the alpha-era node and was tracked as an experimental surface. | `experimental/oidc-sso/STATUS.md`; `node/tests/auth/test_oidc.py` |
| `v0.9.0a2` | Security review documented OIDC ID-token algorithm allowlist and discovery URL validation dispositions. | `SECURITY.md`; `docs/internal/security-evidence-registry-2026-05-17.md` |
| `0.9.xA` planned | Keep OIDC outside the default surface while tightening operator guidance and explicit production gates. | `ROADMAP.md`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Token-validation coverage | Validate issuer, audience, expiry, and signing-algorithm handling. | Partial | `node/tests/auth/test_oidc.py` |
| Discovery hardening | Validate HTTPS-only discovery, safe JWKS URLs, and redirect behavior. | Partial | `node/tests/auth/test_oidc.py`; `SECURITY.md` |
| Operator guidance | Document production IdP, audience, and domain-allowlist requirements. | Partial | `features/oidc-sso/security.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No public production support guarantee is attached to OIDC in the alpha line.
- Operator IdP setup remains deployment-specific.
- Domain allowlists are optional; operators must set them for organization-only
  deployments.
- OIDC cannot grant `admin` or `federate`; those remain static-key or separate
  capability-token concerns.
