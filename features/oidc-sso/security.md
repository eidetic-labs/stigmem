# OIDC SSO Security

## Security Posture

OIDC SSO introduces an external identity-provider trust boundary. It is disabled
by default and must be explicitly configured by the operator. Static API-key
authentication remains available for deployments that do not use an IdP.

OIDC exchange can grant at most `read` and `write` permissions. It does not
grant `admin` or `federate`.

## Threat Model Deltas

| Risk | Current mitigation |
| --- | --- |
| Unsafe provider discovery URL | Discovery and JWKS URLs must pass safe URL validation and use HTTPS. |
| Token accepted under an unexpected algorithm | ID-token decoding uses the configured algorithm allowlist. |
| Token accepted for the wrong audience or issuer | Token validation checks configured issuer and audience. |
| Organization-external identity accepted | Operators can configure `STIGMEM_OIDC_ALLOWED_DOMAINS`; production organization-only deployments should set it. |
| Stale OIDC session key remains active | Successful exchange deletes previous OIDC-issued keys for the same `sub` before minting the replacement key. |
| Excessive permission grant | OIDC exchange filters requested permissions to `read` and `write`; optional advanced ACL plugin gates can further cap permissions. |

## Advisories and Findings

No public GHSA is currently owned by this feature record.

Related v0.9.0a2 public security posture entries:

- M5: OIDC ID-token algorithm allowlist, documented in `SECURITY.md`.
- L5: OIDC discovery URL validation, documented in `SECURITY.md`.

These entries are documented per the Medium/Low publication policy and are not
future GHSA publication work.

## Security Gaps

- Operators must configure `STIGMEM_OIDC_AUDIENCE` and domain allowlists
  correctly for production organization boundaries.
- No stable-line external IdP certification matrix exists.
- No feature-specific rate limit for OIDC exchange is documented here.
