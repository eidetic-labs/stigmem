---
title: Federation Trust (§19)
sidebar_label: Federation Trust
description: Org manifests, capability tokens, source-trust scoring, quarantine garden, provenance chains, and the recall-time sanitizer — §19 normative in spec v1.1.
audience: Integrator
---

# Federation Trust

**Audience:** node operators deploying cross-org federation; spec contributors.
**Spec reference:** §19 (normative, v1.1); §2.8 fact record extensions; §5.21–5.25 wire format.

---

Federation Trust is the mechanism by which Stigmem nodes establish verifiable identity, delegate cross-org write permissions, score incoming sources, quarantine untrusted facts, and sanitize recall output — without centralised coordination.

§19 is normative in spec v1.1. It builds on the §18 Source Attestation machinery and adds seven interlocking subsystems:

| Subsystem | Section | Summary |
|---|---|---|
| Org manifests | §19.1 | Signed identity document; binds entity URIs to an Ed25519 public key |
| Transparency log | §19.2 | Append-only audit anchor for manifests and revocations |
| Capability tokens | §19.3 | Short-lived signed credentials delegating specific verbs on specific resources |
| Source-trust score | §19.4 | Scalar `t ∈ [0,1]` per source; modulates effective confidence at recall time |
| Quarantine garden | §19.5 | Isolation zone for facts that fail trust thresholds |
| Provenance chain | §19.6 | `derived_from` + `attestation_chain` for verifiable fact lineage |
| Recall-time sanitizer | §19.7 | Strips prompt-injection sentinels from recalled string values |

---

## Org Manifest (§19.1)

An **org manifest** declares the canonical Ed25519 public key for a node or organisation and the entity URIs it is authoritative for. Peers use the manifest key to verify capability tokens and provenance signatures.

### Publish your manifest (§5.21)

```bash
# Generate an Ed25519 keypair (one-time setup)
openssl genpkey -algorithm Ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out signing.pub

# Encode the public key as base64url
PUB_B64=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | base64 | tr '+/' '-_' | tr -d '=')

# Compute the key_id (SHA-256 fingerprint)
KEY_ID=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | sha256sum | awk '{print $1}')

# Publish manifest via the admin API
curl -X PUT https://your-node.example.com/v1/federation/manifest \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"manifest_version\": 1,
    \"entity_uri\":  \"stigmem://your-org.example\",
    \"public_key\":  \"$PUB_B64\",
    \"key_id\":      \"$KEY_ID\",
    \"entities\": [
      \"stigmem://your-org.example/agent/assistant\",
      \"stigmem://your-org.example/adapter/hook\"
    ],
    \"rotation_events\": [],
    \"issued_at\":  \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"expires_at\": \"$(date -u -d '+1 year' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
                     || date -u -v+1y +%Y-%m-%dT%H:%M:%SZ)\",
    \"signature\":  \"<base64url Ed25519 sig over JCS-canonical body>\"
  }"
# → { "manifest_id": "...", "log_entry_url": "..." }
```

The `signature` MUST be computed over the JCS (RFC 8785) canonical encoding of all other manifest fields (§19.1.3).

### Well-known endpoint (§19.1.6)

Nodes MUST publish their manifest at `/.well-known/stigmem-manifest.json`. Peers resolve it with:

```bash
curl https://peer-node.example.com/.well-known/stigmem-manifest.json
```

### Key rotation (§19.1.4)

When rotating your signing key, add a `rotation_events` entry signed by the **old** private key. This preserves a verifiable chain of custody back to the original manifest.

```json
{
  "rotation_events": [
    {
      "rotated_at":   "2026-06-01T00:00:00Z",
      "old_key_id":   "<previous key fingerprint>",
      "new_key_id":   "<current key fingerprint>",
      "rotation_sig": "<base64url Ed25519 sig by OLD key>"
    }
  ]
}
```

Submit the updated manifest to the transparency log after every rotation (§19.1.6).

### Manifest resolution (§5.22)

```bash
ENTITY_URI_ENCODED=$(python3 -c "import urllib.parse, sys; \
  print(urllib.parse.quote(sys.argv[1], safe=''))" \
  "stigmem://peer-org.example")

curl https://your-node.example.com/v1/federation/manifest/$ENTITY_URI_ENCODED
# → 200 { ...manifest object... }
# → 404 if no manifest found for entity_uri
```

---

## Transparency Log (§19.2)

The transparency log is an append-only, tamper-evident audit anchor. Implementations SHOULD integrate with [Rekor](https://docs.sigstore.dev/rekor/overview/) (Sigstore) or an equivalent log that provides Merkle-tree inclusion proofs.

After submitting a manifest, store the `LogEntry` at `/.well-known/stigmem-manifest-proof.json` (§19.2.4) so peers can independently verify inclusion.

```bash
# Submit manifest to Rekor
rekor-cli upload \
  --rekor_server https://rekor.sigstore.dev \
  --artifact stigmem-manifest.json \
  --type intoto

# Verify inclusion proof
rekor-cli verify \
  --rekor_server https://rekor.sigstore.dev \
  --entry <log-index>
```

In `trust_mode: strict`, peers MUST verify log inclusion proofs before trusting a manifest (§19.2.3). Capability token revocations MUST also be submitted as separate log entries (§19.2.5).

---

## Capability Tokens (§19.3)

A **capability token** grants a specific subject a specific verb on a specific resource. Tokens replace ad-hoc per-peer trust agreements with a verifiable, revocable delegation primitive.

### Token shape (§19.3.2)

```
CapabilityToken:
  token_version:  1               // MUST be 1 for this spec version
  token_id:       UUID            // used for revocation lookup
  issuer:         URI             // MUST be in issuer's manifest entities list
  subject:        URI             // the token bearer's entity URI
  verb:           "read" | "write" | "admin" | "federate"
  object:         URI             // scope, garden, or "*"
  issued_at:      RFC3339
  expiry:         RFC3339         // MUST be set; MUST NOT exceed 90 days from issued_at
  nonce:          hex             // 32 bytes cryptographically random
  signature:      base64url       // Ed25519 sig over JCS-canonical body, signed by issuer key
```

### Issue a token (§5.23)

```bash
curl -X POST https://your-node.example.com/v1/federation/capability-tokens \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"issuer\":   \"stigmem://your-org.example\",
    \"subject\":  \"stigmem://partner-org.example/agent/assistant\",
    \"verb\":     \"write\",
    \"object\":   \"stigmem://your-org.example/scope/shared\",
    \"expiry\":   \"2026-06-01T00:00:00Z\",
    \"nonce\":    \"$(openssl rand -hex 32)\"
  }"
# → 201 { "token": "...", "token_id": "..." }
```

### Verify a token (§19.3.3)

Receivers MUST verify a token before honoring it:

1. Resolve the issuer's org manifest.
2. Verify the manifest's self-signature.
3. Verify the token's `signature` under the manifest's `public_key`.
4. Confirm `subject` appears in the issuer's `entities` list or is an explicitly delegated external entity.
5. Check `expiry > now`.
6. Confirm the token is not revoked.

### Revoke a token (§5.24)

```bash
curl -X POST https://your-node.example.com/v1/federation/capability-tokens/$TOKEN_ID/revoke \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -d '{}'
# → 204; revocation is logged to the transparency log (§19.2.5)
```

A revoked token MUST be rejected even if it has not yet expired (§19.3.4). Nodes SHOULD cache revocation events with a TTL of at least 60 seconds.

---

## Source-Trust Score (§19.4)

Every inbound fact source receives a scalar `t ∈ [0,1]`. At recall time, effective confidence is:

```
effective_confidence = fact.confidence × t(fact.source)
```

`t` is recomputed live at recall time using current peer state (§19.4.4). The `source_trust` snapshot stored on the fact is informational only.

### Derivation formula (§19.4.2)

```
t = clamp(
      0.35 × identity_strength(source)
    + 0.30 × peer_history(source)
    + 0.25 × scope_authority(source, scope)
    + 0.10 × attestation_mode_factor(node.attestation_mode),
    0.0, 1.0
  )
```

**`identity_strength`** rewards sources with a verified org manifest and log inclusion proof (max 1.0); penalizes unrecognized or absent sources (min 0.0).

**`peer_history`** rewards sources with a clean attestation track record; new sources default to 0.5.

**`scope_authority`** rewards sources holding a valid `write` capability token for the target scope (1.0) or an admin key (0.9).

**`attestation_mode_factor`** reflects the node's attestation strictness: `enforce` → 1.0, `warn` → 0.6, `off` → 0.2.

If all components are unavailable, `t` defaults to 0.5. Admin-blocklisted sources always receive `t = 0.0` (§19.4.5).

### Trust mode (§19.4.3)

Configure via `STIGMEM_TRUST_MODE`:

| Mode | Behaviour |
|---|---|
| `strict` | Log inclusion proofs required; sources with `t < 0.2` are quarantined |
| `relaxed` (default) | Trust scoring active; low scores logged but not quarantined |
| `off` | No scoring; `source_trust` is `null` on all stored facts |

When using non-default trust weights, declare them at `/.well-known/stigmem` under `federation_trust.trust_weights` (§19.10).

---

## Quarantine Garden (§19.5)

A **quarantine garden** is a Memory Garden (§17) with `quarantine: true` set at creation. It holds facts pending human or automated review before they enter production scope.

In `trust_mode: strict`, the node automatically routes inbound facts to the designated quarantine garden when (§19.5.4):

- The source has `t < 0.2`, **or**
- The source lacks a valid org manifest, **or**
- The fact fails provenance chain verification (§19.6.4).

If no quarantine garden is designated, these facts are rejected with HTTP 403 `trust_below_threshold`.

### Review quarantined facts (§5.25)

```bash
QUARANTINE_ID="<your quarantine garden uuid>"

# Promote a fact to a target garden
curl -X POST https://your-node.example.com/v1/gardens/$QUARANTINE_ID/promote \
  -H "Authorization: Bearer $MODERATOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"fact_id\":          \"<uuid>\",
    \"target_garden_id\": \"<target garden uuid>\",
    \"reason\":           \"Verified provenance.\"
  }"

# Reject a fact (sets confidence=0; retained for audit)
curl -X POST https://your-node.example.com/v1/gardens/$QUARANTINE_ID/reject \
  -H "Authorization: Bearer $MODERATOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"fact_id\": \"<uuid>\",
    \"reason\":  \"Failed source attestation; untrusted origin.\"
  }"
```

Callers need the `quarantine:moderator` or `admin` role on the quarantine garden (§19.5.3). All promote and reject events are written to the attestation audit log (§18.10 + §19.5.6).

A rejected fact is retained in the quarantine garden for audit and MUST NOT appear in normal recall results.

---

## Provenance Chain (§19.6)

Facts may declare their intellectual antecedents and carry cryptographic attestations from intermediate processors. Two new fields extend the v1.1 fact record (§2.8):

| Field | Type | Purpose |
|---|---|---|
| `derived_from` | `[FactHash]` | SHA-256 hashes of antecedent facts; ordered by derivation precedence |
| `attestation_chain` | `[Signature]` | Ed25519 signatures from intermediate processors; paired with `attestation_chain_issuers` |

### Fact hash computation (§19.6.2)

A fact hash is the hex-encoded SHA-256 of the JCS-canonical JSON of:

```json
{
  "entity":     "<entity>",
  "relation":   "<relation>",
  "value":      <FactValue>,
  "scope":      "<scope>",
  "source":     "<source>",
  "confidence": <float>,
  "ts":         "<RFC3339>"
}
```

The following fields are excluded: `id`, `garden_id`, `attested`, `source_trust`, `derived_from`, `attestation_chain`, `attestation_chain_issuers`. Excluding trust annotations keeps the hash stable across metadata updates.

### Example fact with provenance (§2.8)

```json
{
  "entity":     "user:alice",
  "relation":   "memory:prefers",
  "value":      { "type": "string", "v": "dark mode" },
  "source":     "stigmem://your-org.example/agent/assistant",
  "confidence": 0.9,
  "scope":      "company",
  "derived_from": [
    "a3f5b2c1d4e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"
  ],
  "attestation_chain": [
    "<base64url Ed25519 sig by assistant>"
  ],
  "attestation_chain_issuers": [
    "stigmem://your-org.example/agent/assistant"
  ]
}
```

### Verification rules (§19.6.4)

A provenance chain is **valid** if all of the following hold:

1. Every `FactHash` in `derived_from` references a fact that exists and whose stored hash matches the declared value.
2. Every signature in `attestation_chain` verifies under the corresponding issuer's current manifest public key.
3. No issuer appears more than once in `attestation_chain_issuers`.
4. Each issuer's entity URI appears in their manifest's `entities` list.

In `trust_mode: strict`, facts with invalid provenance chains MUST be rejected (§19.6.4). In `relaxed` mode, warnings are logged.

---

## Recall-Time Content Sanitizer (§19.7)

The sanitizer prevents prompt-injection payloads from reaching recall consumers. It is applied immediately before API response serialisation — not at write time — so future policy changes apply retroactively to stored facts (§19.7.1).

The sanitizer runs as the final step in the recall pipeline (§19.7.5):

```
Storage
  → Scope/garden ACL filter (§17.3)
  → Source-trust multiplier → effective_confidence (§19.4.4)
  → Provenance chain verification (§19.6.4, strict only)
  → Content sanitizer   ← HERE
  → API response serialiser
```

### Enforcement modes (§19.7.4)

Configure via `STIGMEM_SANITIZER_MODE`:

| Mode | Behaviour on match |
|---|---|
| `block` (default in `strict`) | Fact excluded; `{ "fact_id": "...", "sanitized": true }` placeholder returned |
| `quarantine` | Fact moved to quarantine garden and excluded from current result |
| `warn` (default in `relaxed`) | Fact returned with `sanitizer_warnings: ["<matched pattern>"]` |
| `off` (implied by `trust_mode: off`) | No sanitization |

Operators MAY configure a stricter mode than the `trust_mode` default; they MUST NOT configure a less restrictive mode in `trust_mode: strict`.

### Default sentinel patterns (§19.7.2)

The following are checked against string- and text-typed `FactValue` fields:

- `ignore [all] previous instructions`
- `disregard [all] previous prompt/instructions`
- `you are now [in a] different/new mode`
- `act as [an] evil/unfiltered/uncensored/dan`
- `system prompt:`
- `<|im_start|>` / `<|im_end|>`
- `[INST]` / `[/INST]`
- `Human:` / `Assistant:` (chat-template leaks)
- `{"__proto__":` / `{"constructor":` (prototype pollution)

Add extra patterns via `STIGMEM_SANITIZER_EXTRA_PATTERNS` (newline-delimited regex file). Operators MUST NOT remove default patterns in `trust_mode: strict`.

### Schema enforcement at recall time (§19.7.3)

The sanitizer also enforces type correctness for structured values. `NaN`/`±Inf` numbers, malformed refs, and invalid JSON blobs are replaced with `null`. Facts where substitution occurs are marked `sanitizer_redacted: true` in the response.

### Audit logging (§19.7.6)

Every sanitizer action is logged to the attestation audit log (§18.10) with `sanitizer_action`, `fact_id`, `matched_pattern`, and `recall_endpoint`.

---

## Well-known advertisement (§19.10)

Nodes MUST extend their `/.well-known/stigmem` response to declare federation trust configuration:

```json
{
  "federation_trust": {
    "trust_mode":         "strict",
    "sanitizer_mode":     "block",
    "manifest_url":       "https://your-node.example.com/.well-known/stigmem-manifest.json",
    "manifest_proof_url": "https://your-node.example.com/.well-known/stigmem-manifest-proof.json",
    "trust_weights": {
      "identity_strength": 0.35,
      "peer_history":      0.30,
      "scope_authority":   0.25,
      "attestation_mode":  0.10
    }
  }
}
```

`trust_weights` is required only when non-default values are configured.

---

## Error reference (§19.9)

| HTTP | Code | Condition |
|---|---|---|
| 400 | `manifest_signature_invalid` | Manifest `signature` does not verify under `public_key` |
| 400 | `manifest_rotation_chain_invalid` | Rotation chain verification fails |
| 400 | `token_nonce_invalid` | Nonce is not 32 bytes or is malformed |
| 400 | `provenance_hash_invalid` | `derived_from` entry is not a 64-char lowercase hex string |
| 403 | `trust_below_threshold` | Source `t < 0.2` in strict mode; no quarantine garden configured |
| 403 | `token_expired` | Capability token expiry has passed |
| 403 | `token_revoked` | Token found in revocation log |
| 403 | `token_replay` | Token nonce already seen within validity window |
| 403 | `insufficient_capability` | Token does not cover the requested verb/object |
| 403 | `entity_not_in_manifest` | Source entity URI not in issuer's manifest `entities` list |
| 409 | `quarantine_has_pending_facts` | Attempted deletion of quarantine garden with pending facts |
| 409 | `fact_not_quarantine_pending` | Promote/reject on a non-pending fact |
| 422 | `attestation_chain_mismatch` | `attestation_chain` and `attestation_chain_issuers` array lengths differ |

---

:::info See also
- [Federation guide](./federation.md) — peer handshake and §6 wire protocol
- [4-node federation topology](./federation-4node.md) — multi-node setup examples
- [Source Attestation §18](../.../spec/index.md) — the §18 foundation §19 builds on
:::
