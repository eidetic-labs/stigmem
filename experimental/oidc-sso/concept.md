---
title: OIDC / SSO Integration
sidebar_label: OIDC / SSO
audience: Integrator
status: Beta
---

# OIDC / SSO Integration

**Audience:** Node operators configuring human identity, and developers integrating Stigmem with an identity provider.

The OIDC bridge lets human users authenticate with their organisation's IdP and receive a scoped, short-lived Stigmem API key. MFA, session revocation, and offboarding are handled by the IdP — Stigmem inherits them automatically.

The static bearer-key path (see [Authentication](./authentication)) is unaffected. OIDC is opt-in and disabled by default.

## How it works

```
Human browser  →  IdP (OIDC)  →  POST /v1/auth/oidc/exchange  →  scoped API key  →  Stigmem node
```

1. User authenticates with the IdP and receives an `id_token`.
2. The client sends the `id_token` to `POST /v1/auth/oidc/exchange`.
3. The node validates the token (JWKS discovery, issuer, audience, domain allowlist), then mints a Stigmem API key bound to the OIDC `sub` claim.
4. The minted key is returned; all previous OIDC keys for the same `sub` are atomically revoked (single-session-per-principal guarantee).
5. The client uses the key as a normal Bearer token: `Authorization: Bearer <api_key>`.

## Configuration

Enable OIDC with the following environment variables:

| Env var | Default | Description |
|---------|---------|-------------|
| `STIGMEM_OIDC_ENABLED` | `false` | Master switch; must be `true` to use the bridge |
| `STIGMEM_OIDC_ISSUER_URL` | `""` | IdP issuer URL; discovery doc fetched from `{issuer_url}/.well-known/openid-configuration` |
| `STIGMEM_OIDC_AUDIENCE` | `""` | Expected value in the `aud` claim of incoming `id_token`s |
| `STIGMEM_OIDC_TOKEN_TTL_HOURS` | `8` | Lifetime of issued API keys in hours (default: one working-day session) |
| `STIGMEM_OIDC_ALLOWED_DOMAINS` | `""` | Comma-separated email domain allowlist; empty = allow any domain |

**Minimal example (Google Workspace):**

```bash
STIGMEM_OIDC_ENABLED=true
STIGMEM_OIDC_ISSUER_URL=https://accounts.google.com
STIGMEM_OIDC_AUDIENCE=<your-client-id>.apps.googleusercontent.com
STIGMEM_OIDC_ALLOWED_DOMAINS=example.com
```

## Endpoints

### POST /v1/auth/oidc/exchange

Exchange an OIDC `id_token` for a scoped Stigmem API key.

**Request body:**

```json
{
  "id_token": "<JWT from IdP>",
  "permissions": ["read", "write"]
}
```

`permissions` defaults to `["read", "write"]` if omitted. The `federate` permission cannot be granted via OIDC.

**Response (201 Created):**

```json
{
  "api_key": "stgm_...",
  "entity_uri": "oidc:<sub>",
  "expires_at": "2026-05-03T09:00:00Z"
}
```

- `api_key` — raw key; use as `Authorization: Bearer <api_key>`. Not stored in plain text on the server.
- `entity_uri` — derived from the `sub` claim; used as the `source` principal for facts asserted by this key.
- `expires_at` — wall-clock expiry; determined by `STIGMEM_OIDC_TOKEN_TTL_HOURS`.

**Error responses:**

| Status | Cause |
|--------|-------|
| `401 Unauthorized` | `id_token` invalid, expired, wrong issuer, or wrong audience |
| `403 Forbidden` | Email domain not in `STIGMEM_OIDC_ALLOWED_DOMAINS` |
| `503 Service Unavailable` | `STIGMEM_OIDC_ENABLED=false` or JWKS endpoint unreachable |

**Session rotation:** Every successful exchange atomically revokes all prior OIDC-issued keys for the same `sub`. If the user is terminated in the IdP, the next exchange attempt fails (expired or revoked `id_token`) and no new key is minted — the old key was already revoked by the previous exchange.

**`curl` example:**

```bash
OIDC_TOKEN=$(curl -s ... | jq -r .id_token)   # obtain from your IdP flow

curl -s -X POST http://localhost:8000/v1/auth/oidc/exchange \
  -H 'Content-Type: application/json' \
  -d "{\"id_token\": \"$OIDC_TOKEN\"}" | jq .
```

---

### GET /v1/auth/keys

List all non-expired API keys belonging to the authenticated caller.

**Response (200 OK):**

```json
[
  {
    "id": "uuid",
    "entity_uri": "oidc:<sub>",
    "permissions": ["read", "write"],
    "description": null,
    "created_at": "2026-05-03T01:00:00Z",
    "expires_at": "2026-05-03T09:00:00Z",
    "oidc_sub": "<sub>"
  }
]
```

`oidc_sub` is non-null for OIDC-issued keys; null for static keys.

```bash
curl -H 'Authorization: Bearer stgm_...' http://localhost:8000/v1/auth/keys | jq .
```

---

### DELETE /v1/auth/keys/\{key\_id\}

Revoke one of your own keys immediately. Callers cannot revoke another entity's keys.

```bash
curl -s -X DELETE \
  -H 'Authorization: Bearer stgm_...' \
  http://localhost:8000/v1/auth/keys/uuid-of-key
# → 204 No Content
```

**Error responses:** `403` if the key belongs to a different entity; `404` if the key does not exist.

---

### GET /v1/me

Returns the authenticated caller's identity. Useful for verifying a key and checking permissions without querying facts.

```bash
curl -H 'Authorization: Bearer stgm_...' http://localhost:8000/v1/me
# → {"entity_uri": "oidc:<sub>", "permissions": ["read", "write"]}
```

## JWKS caching

The node fetches the IdP's JWKS on the first `exchange` call and caches it for 10 minutes. Subsequent calls within the cache window do not make an outbound request. If the IdP rotates keys, the cache refreshes on the next cache miss.

## Supported IdPs

Any OIDC-compliant IdP works. Verified configurations:

- **Google Workspace** — issuer: `https://accounts.google.com`
- **GitHub** (via OIDC) — issuer: `https://token.actions.githubusercontent.com`

Any IdP that exposes `{issuer}/.well-known/openid-configuration` with a `jwks_uri` is compatible (Okta, Auth0, Keycloak, Microsoft Entra ID, etc.).

## Security notes

- `STIGMEM_OIDC_AUDIENCE` should be set to your specific client ID. An empty audience allows any `aud` value — acceptable in private deployments, not recommended in multi-tenant or public-facing ones.
- `STIGMEM_OIDC_ALLOWED_DOMAINS` is the primary guard against access by users outside your organisation. Set it explicitly in production.
- The node stores only the SHA-256 digest of issued keys (consistent with §3.5). The raw key is returned once at issuance and never stored in plain text.
- The OIDC bridge issues keys with `read+write` at most. Operators who need `federate` permission must provision static keys out-of-band.

## Self-hosted / no-IdP deployments

Set `STIGMEM_OIDC_ENABLED=false` (the default). Users obtain static API keys directly from the node operator via `create_api_key` (admin API). The Web UI accepts these keys in the API Key field of the Connection bar.

## See also

- [Authentication](./authentication) — API key and bearer-key model (§3.5)
- [Human Surface (Web UI)](./human-surface) — browser UI that uses OIDC-issued keys
- [Human Key Issuance](./human-key-issuance) — Track C: per-garden key scoping on top of the OIDC bridge
