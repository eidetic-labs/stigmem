---
title: Per-Agent Keypair Registration
sidebar_label: Agent Keypairs
audience: Integrator
---

# Per-Agent Keypair Registration

<p className="stigmem-meta"><span>4 min read</span><span>Agent developers</span><span>Track C · C1</span></p>

<div className="stigmem-lead">

**What this page is**

Agents register an Ed25519 public key with the node, then sign each
fact payload. The node verifies the signature before writing —
cryptographically verifiable source provenance on asserted facts.

</div>

<div className="stigmem-keypoint">

**Keypair attestation is opt-in per assertion.**

The existing Bearer-key model is unaffected. Set
<code>STIGMEM_ATTESTATION_REQUIRED=true</code> to make it mandatory
node-wide.

</div>

Stigmem's `source` field identifies who asserted a fact
(`agent:settings-sync`, `oidc:alice@example.com`, etc.), but prior to
Track C the node accepted any `source` value the caller provided. C1
closes this gap.

## How it works

```
Agent                              Stigmem node
  │                                     │
  │  POST /v1/auth/agent-keys           │
  │  { public_key, description }  ───►  │  stores public key against entity_uri
  │                                     │
  │  POST /v1/facts                     │
  │  { ...fact, attestation: {          │
  │      key_id, signature } }    ───►  │  verifies sig → stores attested_key_id
  │                                     │
  │                                     │  GET /v1/audit returns full trail:
  │                                     │  principal → attested key → fact
```

## Endpoints

### `POST /v1/auth/agent-keys` · register a key

Register an Ed25519 public key for the calling entity. Requires
`write` permission.

**Request body:**

```json
{
  "public_key": "<base64url-encoded 32-byte Ed25519 public key>",
  "description": "my-coding-assistant prod keypair"
}
```

`description` is optional but recommended for audit readability.

**Response (201 Created):**

```json
{
  "id": "uuid",
  "entity_uri": "agent:my-service",
  "public_key": "base64url...",
  "description": "my-coding-assistant prod keypair",
  "registered_at": "2026-05-03T01:00:00Z",
  "status": "active"
}
```

<div className="stigmem-keypoint">

**Save the `id` — it is the `key_id` you include in every attestation token.**

</div>

### `GET /v1/auth/agent-keys` · list my keys

Returns all keys (active and revoked) registered by the calling entity.

```bash
curl -H 'Authorization: Bearer stgm_...' \
  http://localhost:8000/v1/auth/agent-keys | jq .
```

### `DELETE /v1/auth/agent-keys/{key_id}` · revoke a key

Marks the key as `revoked`. Revoked keys are rejected at attestation
verification. Callers may only revoke their own keys.

```bash
curl -s -X DELETE \
  -H 'Authorization: Bearer stgm_...' \
  http://localhost:8000/v1/auth/agent-keys/<key-id>
# → 204 No Content
```

**Error responses:**

<div className="stigmem-fields">

<div>
<dt>Status</dt>
<dt><span className="stigmem-fields__type">When</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>403</code></dt>
<dt><span className="stigmem-fields__type">wrong owner</span></dt>
<dd>The key belongs to a different entity.</dd>
</div>

<div>
<dt><code>404</code></dt>
<dt><span className="stigmem-fields__type">not found</span></dt>
<dd>Key id does not exist.</dd>
</div>

<div>
<dt><code>409</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Already revoked.</dd>
</div>

</div>

## Attesting a fact assertion

Include an `attestation` object in the `POST /v1/facts` body:

```json
{
  "entity": "user:alice",
  "relation": "memory:context",
  "value": { "type": "str", "v": "working on stigmem docs" },
  "source": "agent:my-service",
  "confidence": 1.0,
  "scope": "local",
  "attestation": {
    "key_id": "<uuid from registration>",
    "signature": "<base64url Ed25519 signature>"
  }
}
```

### Canonical message

Sign the following UTF-8 string with your private key:

```
{entity}\n{relation}\n{value.type}\n{encoded_v}\n{source}
```

<div className="stigmem-fields">

<div>
<dt>Value type</dt>
<dt><span className="stigmem-fields__type">Encoding</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>str</code></dt>
<dt><span className="stigmem-fields__type">verbatim</span></dt>
<dd>The string itself.</dd>
</div>

<div>
<dt><code>float</code></dt>
<dt><span className="stigmem-fields__type"><code>repr(float)</code></span></dt>
<dd>As Python formats it (use the same encoding the node uses when storing).</dd>
</div>

<div>
<dt><code>bool</code></dt>
<dt><span className="stigmem-fields__type"><code>"true"</code> / <code>"false"</code></span></dt>
<dd></dd>
</div>

<div>
<dt><code>json</code></dt>
<dt><span className="stigmem-fields__type">compact JSON string</span></dt>
<dd></dd>
</div>

</div>

**Python example (using the `cryptography` library):**

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64, json

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Register the public key once
pub_bytes = public_key.public_bytes_raw()
pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()

# Per-assertion: build canonical message and sign
entity   = "user:alice"
relation = "memory:context"
val_type = "str"
val_v    = "working on stigmem docs"
source   = "agent:my-service"

canonical = f"{entity}\n{relation}\n{val_type}\n{val_v}\n{source}".encode("utf-8")
sig_bytes = private_key.sign(canonical)
sig_b64   = base64.urlsafe_b64encode(sig_bytes).rstrip(b"=").decode()

payload = {
    "entity": entity,
    "relation": relation,
    "value": {"type": val_type, "v": val_v},
    "source": source,
    "confidence": 1.0,
    "scope": "local",
    "attestation": {"key_id": "<registered-key-id>", "signature": sig_b64},
}
```

## Making attestation mandatory

Set `STIGMEM_ATTESTATION_REQUIRED=true` in the node environment. With
this flag:

<div className="stigmem-grid">

<div><h4>Every assert needs attestation</h4><p>Every <code>POST /v1/facts</code> must include a valid <code>attestation</code> object.</p></div>
<div><h4>Unattested requests rejected</h4><p>Returns <code>400 Bad Request</code>: <em>"attestation required; register an agent key at POST /v1/auth/agent-keys"</em>.</p></div>

</div>

Default is `false` for backward compatibility with clients that
predate Track C.

## Migration path

<div className="stigmem-fields">

<div>
<dt>Phase</dt>
<dt><span className="stigmem-fields__type">Posture</span></dt>
<dd>How to adopt</dd>
</div>

<div>
<dt>Optional (default)</dt>
<dt><span className="stigmem-fields__type">backward-compatible</span></dt>
<dd>Existing agents work unchanged. Agents that want attested provenance generate a keypair, register it, and add <code>attestation</code> to each assertion.</dd>
</div>

<div>
<dt>Enforced</dt>
<dt><span className="stigmem-fields__type"><code>STIGMEM_ATTESTATION_REQUIRED=true</code></span></dt>
<dd>All agents must register a key before asserting facts. API-key auth continues; only the <code>attestation</code> field becomes required.</dd>
</div>

</div>

## See also

<div className="stigmem-next">

<a href="./authentication">
<strong>Security</strong>
<span>Authentication</span>
<small>Bearer-key model and OIDC-issued keys.</small>
</a>

<a href="./human-key-issuance">
<strong>Security</strong>
<span>Human key issuance</span>
<small>C2: per-garden key scoping for human principals.</small>
</a>

<a href="./audit-log">
<strong>Security</strong>
<span>Audit log</span>
<small>C3: principal → attested-source → fact-id trail.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/oidc-sso">
<strong>Experimental</strong>
<span>OIDC / SSO integration</span>
<small>How human principals receive their <code>entity_uri</code>.</small>
</a>

</div>
