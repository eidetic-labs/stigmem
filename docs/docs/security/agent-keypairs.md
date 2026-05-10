---
title: Per-Agent Keypair Registration
sidebar_label: Agent Keypairs
audience: Integrator
---

# Per-Agent Keypair Registration

**Audience:** Agent developers who need cryptographically verifiable source provenance on asserted facts.

Stigmem's `source` field identifies who asserted a fact (`agent:settings-sync`, `oidc:alice@example.com`, etc.), but prior to Track C the node accepted any `source` value the caller provided. C1 closes this gap: agents register an Ed25519 public key with the node, then sign each fact payload. The node verifies the signature before writing.

The existing Bearer-key model is unaffected. Keypair attestation is opt-in per assertion; it can be made mandatory node-wide with `STIGMEM_ATTESTATION_REQUIRED=true`.

---

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

---

## Endpoints

### POST /v1/auth/agent-keys — register a key

Register an Ed25519 public key for the calling entity. Requires `write` permission.

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

Save the `id` — it is the `key_id` you include in every attestation token.

---

### GET /v1/auth/agent-keys — list my keys

Returns all keys (active and revoked) registered by the calling entity.

```bash
curl -H 'Authorization: Bearer stgm_...' \
  http://localhost:8000/v1/auth/agent-keys | jq .
```

---

### DELETE /v1/auth/agent-keys/\{key\_id\} — revoke a key

Marks the key as `revoked`. Revoked keys are rejected at attestation verification. Callers may only revoke their own keys.

```bash
curl -s -X DELETE \
  -H 'Authorization: Bearer stgm_...' \
  http://localhost:8000/v1/auth/agent-keys/<key-id>
# → 204 No Content
```

**Error responses:** `403` if the key belongs to a different entity; `404` if not found; `409` if already revoked.

---

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

Where `encoded_v` is:
- `str` value → the string itself
- `float` value → `repr(float)` as Python formats it (use the same encoding the node uses when storing)
- `bool` value → `"true"` or `"false"`
- `json` value → compact JSON string

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

---

## Making attestation mandatory

Set `STIGMEM_ATTESTATION_REQUIRED=true` in the node environment. With this flag:

- Every `POST /v1/facts` must include a valid `attestation` object.
- Requests without attestation are rejected with `400 Bad Request`:
  ```
  "attestation required; register an agent key at POST /v1/auth/agent-keys"
  ```

Default is `false` for backward compatibility with clients that predate Track C.

---

## Migration path

| Phase | How to adopt |
|-------|-------------|
| **Optional (default)** | Existing agents work unchanged. Agents that want attested provenance generate a keypair, register it, and add `attestation` to each assertion. |
| **Enforced** | Set `STIGMEM_ATTESTATION_REQUIRED=true`. All agents must register a key before asserting facts. API-key auth continues; only the `attestation` field becomes required. |

---

## See also

- [Authentication](./authentication) — Bearer-key model and OIDC-issued keys
- [Human Key Issuance](./human-key-issuance) — C2: per-garden key scoping for human principals
- [Audit Log](./audit-log) — C3: querying the principal → attested-source → fact-id trail
- [OIDC / SSO Integration](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/oidc-sso) — how human principals receive their `entity_uri`
