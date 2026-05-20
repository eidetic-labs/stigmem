---
title: Human Key Issuance — Garden-Scoped Permissions
sidebar_label: Human Key Issuance
audience: Integrator
---

# Human Key Issuance — Garden-Scoped Permissions

<p className="stigmem-meta"><span>3 min read</span><span>Node operators</span><span>Track C · C2</span></p>

<div className="stigmem-lead">

**What this page is**

Track C — C2 adds a permission ceiling to the OIDC exchange: the
scoped key issued to a human is capped by that person's garden
membership role. Node operators no longer manage permission grants
manually — they flow from the curator roster.

</div>

This page covers the garden membership scoping layer. For the full
OIDC bridge configuration (env vars, IdP setup, token exchange flow),
see [OIDC / SSO Integration](https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso).

## How garden membership gates key permissions

When a human calls `POST /v1/auth/oidc/exchange`, the node:

<ol className="stigmem-steps">
<li>Validates the <code>id_token</code> and derives <code>entity_uri = oidc:&lt;sub&gt;</code>.</li>
<li>Looks up the caller's rows in <code>garden_members</code> to determine their <strong>permission ceiling</strong>: <code>admin</code> or <code>writer</code> in any garden → ceiling is <code>{"read", "write"}</code>; <code>reader</code> only or no membership → ceiling is <code>{"read"}</code>.</li>
<li>Intersects the caller's requested <code>permissions</code> with that ceiling.</li>
<li>Returns the key scoped to the intersection.</li>
</ol>

```
Requested permissions: ["read", "write"]
Garden role: reader only
Issued permissions: ["read"]          ← write silently dropped
```

```
Requested permissions: ["read", "write"]
Garden role: writer in at least one garden
Issued permissions: ["read", "write"] ← full grant
```

<div className="stigmem-keypoint">

**The `federate` permission is never grantable via OIDC exchange.**

Garden membership or not. Operators who need <code>federate</code>
must provision static keys out-of-band.

</div>

## Exchange response includes granted permissions

The `ExchangeResponse` now includes a `permissions` field:

```json
{
  "api_key": "stgm_...",
  "entity_uri": "oidc:alice@example.com",
  "permissions": ["read", "write"],
  "expires_at": "2026-05-03T17:00:00Z"
}
```

Clients should read `permissions` on each exchange to know what access
they were granted — do not cache the previous value across token
rotations.

## Setting up garden membership for human users

Grant a human OIDC principal membership in a garden before they
exchange a token:

```bash
# Add alice as a writer in the team garden
curl -s -X POST http://localhost:8000/v1/gardens/team/members \
  -H 'Authorization: Bearer <admin-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "entity_uri": "oidc:alice@example.com",
    "role": "writer"
  }'
```

Role values:

<div className="stigmem-fields">

<div>
<dt>Role</dt>
<dt><span className="stigmem-fields__type">Effect on key permissions</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>admin</code></dt>
<dt><span className="stigmem-fields__type">ceiling: read + write</span></dt>
<dd></dd>
</div>

<div>
<dt><code>writer</code></dt>
<dt><span className="stigmem-fields__type">ceiling: read + write</span></dt>
<dd></dd>
</div>

<div>
<dt><code>reader</code></dt>
<dt><span className="stigmem-fields__type">ceiling: read only</span></dt>
<dd></dd>
</div>

<div>
<dt>(no membership)</dt>
<dt><span className="stigmem-fields__type">ceiling: read only</span></dt>
<dd></dd>
</div>

</div>

A single `admin` or `writer` role in **any** garden grants the full
ceiling — it is not per-garden.

## Minimal example · OIDC exchange with garden membership

```bash
# 1. Obtain an id_token from your IdP (exact command is IdP-specific)
ID_TOKEN="<id_token from Google / GitHub / etc.>"

# 2. Exchange for a scoped Stigmem key
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/auth/oidc/exchange \
  -H 'Content-Type: application/json' \
  -d "{\"id_token\": \"$ID_TOKEN\"}")

API_KEY=$(echo $RESPONSE | jq -r .api_key)
PERMS=$(echo $RESPONSE | jq -r '.permissions | join(",")')
echo "Issued permissions: $PERMS"

# 3. Use the key
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/facts
```

## Security notes

<div className="stigmem-grid">

<div><h4>Membership checked at exchange time</h4><p>Not at API request time. Changing a member's role in the garden does not immediately revoke an active key; the new ceiling applies on the next exchange.</p></div>
<div><h4>Single-session-per-principal</h4><p>Every successful exchange revokes all prior OIDC keys for the same <code>sub</code>. Revoking garden membership and waiting for the current token to expire (or exchanging immediately to pick up the reduced ceiling) is the recommended offboarding flow.</p></div>
<div><h4>No-membership default</h4><p>Users who are not in any garden receive read-only access. Safe default for pilot users or self-hosted nodes without curated gardens.</p></div>

</div>

## See also

<div className="stigmem-next">

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso">
<strong>Experimental</strong>
<span>OIDC / SSO integration</span>
<small>Full OIDC bridge configuration and exchange flow.</small>
</a>

<a href="./authentication">
<strong>Security</strong>
<span>Authentication</span>
<small>Bearer-key model overview.</small>
</a>

<a href="./agent-keypairs">
<strong>Security</strong>
<span>Agent keypairs</span>
<small>C1: Ed25519 keypair registration for agent principals.</small>
</a>

<a href="./audit-log">
<strong>Security</strong>
<span>Audit log</span>
<small>C3: principal → attested-source → fact-id trail.</small>
</a>

</div>
