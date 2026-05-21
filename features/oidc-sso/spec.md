# OIDC SSO Spec

## Scope

OIDC SSO defines the node-local exchange from an external OIDC `id_token` to a
Stigmem API key. It is an opt-in authentication bridge, not the default
authentication mode.

The feature covers:

- OIDC provider discovery from the configured issuer URL;
- JWKS URI validation and cached signing-key lookup;
- ID-token validation for issuer, audience, expiry, and configured signing
  algorithms;
- optional email-domain allowlist enforcement;
- scoped API-key minting and same-subject key rotation;
- OIDC identity exposure through normal key, identity, and audit surfaces.

This feature does not define IdP-hosted login flows, browser session handling,
or federation capability grants.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `STIGMEM_OIDC_ENABLED` | `false` | Enables the OIDC exchange endpoint. |
| `STIGMEM_OIDC_ISSUER_URL` | empty | Expected issuer and discovery base URL. |
| `STIGMEM_OIDC_AUDIENCE` | empty | Expected `aud` claim. |
| `STIGMEM_OIDC_TOKEN_TTL_HOURS` | `8` | Lifetime of minted API keys. |
| `STIGMEM_OIDC_ALLOWED_DOMAINS` | empty | Optional email-domain allowlist. |

The node also uses the configured OIDC ID-token algorithm allowlist. Operators
can narrow the default set through settings.

## Exchange Contract

```http
POST /v1/auth/oidc/exchange
```

The request carries an `id_token` and optional permissions. OIDC exchange can
grant only `read` and `write`; `federate`, `admin`, and other static-key
permissions are not granted through this feature.

Successful exchange returns a raw Stigmem API key, `entity_uri` of the form
`oidc:<sub>`, granted permissions, and key expiry. The raw key is returned once
and is not stored in plain text.

Every successful exchange revokes previous OIDC-issued keys for the same `sub`
before minting the new key. This preserves a single active OIDC session key per
subject.

## Discovery and Token Validation

Provider discovery uses:

```text
{issuer_url}/.well-known/openid-configuration
```

The discovery URL and returned JWKS URI must pass safe outbound URL validation
and use HTTPS. Redirects are not followed during discovery.

Token validation requires:

- a signing key from the configured provider JWKS;
- an allowed signing algorithm;
- matching issuer;
- matching audience;
- unexpired token claims.

## Canonical Spec Assignment

There is no Spec-X assignment for OIDC SSO. The feature is an experimental
authentication bridge implemented by the reference node rather than a standalone
protocol module.
