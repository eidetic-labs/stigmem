# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v1.1-draft

**Status:** DRAFT — §19 proposed normative. §1–§18 stable from v1.0.
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v1.1-draft (Phase 8): §19 Federation Trust — normative. Replaces the non-normative §19 Security Policy stub from v1.0. Security Policy content moved to Appendix A. §2 extended with `derived_from`, `attestation_chain`, and `source_trust` fields. §19.1–§19.7 cover org manifest, transparency log, capability tokens, source-trust score, quarantine garden, provenance chain, and recall-time sanitizer.
- v1.0 (2026-05-03): Promoted §17 Memory Garden and §18 Source Attestation from draft to normative. All §1–§18 sections stable.
- [Prior changelog in stigmem-spec-v1.0.md]

> **Reading guide:** §1–§18 are unchanged from v1.0. §19 is fully normative in v1.1. §2 and §5 carry v1.1 additions. Appendix A (Security Policy) is unchanged in content from the v1.0 §19 stub.

---

## 2. Atomic Fact Shape — v1.1 additions

*Stable sections §2.1–§2.7 unchanged from v1.0. The following fields are added to the fact record.*

### 2.8 Federation Trust Fields

Three optional fields extend the fact record to carry provenance, attestation evidence, and source-trust information:

```
FactRecord (v1.1 extension):
  ...all v1.0 fields...
  derived_from:      [FactHash]  | null  // provenance: hashes of facts this derives from (§19.6)
  attestation_chain: [Signature] | null  // ordered attestation signatures (§19.6)
  source_trust:      float | null        // cached source-trust score at write time (§19.4); null = not computed
```

Where:
- `FactHash` is a hex-encoded SHA-256 hash of a normalized fact record (see §19.6.2).
- `Signature` is a base64url-encoded Ed25519 signature from an org manifest key (§19.1).
- `source_trust` is a float in [0.0, 1.0]. Nodes SHOULD populate this at write time when source-trust computation is enabled (§19.4). Nodes MUST NOT reject facts with a low `source_trust` at write time; the value is informational.

**Invariants:**
1. `derived_from` is ordered by logical derivation; the first entry is the most direct antecedent.
2. `attestation_chain` is ordered from innermost to outermost signer; an empty array is semantically equivalent to `null`.
3. `source_trust` is recomputed at recall time and MUST NOT be relied upon as final from the stored record; the stored value is a snapshot useful for audit.

---

## 5. Wire Format — v1.1 additions

*§5.1–§5.20 unchanged from v1.0. The following routes are added.*

### 5.21 Publish an org manifest

```
PUT /v1/federation/manifest
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "manifest_version": 1,
  "entity_uri":       "stigmem://company.example",      // root entity URI for this node/org
  "public_key":       "<base64url Ed25519 public key>", // active signing key
  "key_id":           "<sha256 fingerprint of public key>",
  "entities":         [                                 // entity URIs this manifest is authoritative for
    "stigmem://company.example/agent/assistant",
    "stigmem://company.example/adapter/hook"
  ],
  "rotation_events":  [],   // see §19.1.4; empty on first publish
  "issued_at":        "2026-05-04T00:00:00Z",
  "expires_at":       "2027-05-04T00:00:00Z",
  "signature":        "<base64url Ed25519 sig over canonical JSON>"
}
→ 200 { "manifest_id": "...", "log_entry_url": "..." }
→ 400 if signature verification fails or required fields missing
→ 403 if caller not admin
```

### 5.22 Resolve an org manifest

```
GET /v1/federation/manifest/:entity_uri_encoded
→ 200 { ...manifest object... }
→ 404 if no manifest found for entity_uri
```

### 5.23 Issue a capability token

```
POST /v1/federation/capability-tokens
Authorization: Bearer <admin api-key>

{
  "issuer":   "stigmem://company.example",
  "subject":  "stigmem://company.example/agent/assistant",
  "verb":     "write",
  "object":   "stigmem://partner.example/scope/shared",
  "expiry":   "2026-06-01T00:00:00Z",
  "nonce":    "<32-byte hex random>"
}
→ 201 { "token": "<base64url-encoded signed JWT-like structure>", "token_id": "..." }
→ 403 if caller not admin
```

### 5.24 Revoke a capability token

```
POST /v1/federation/capability-tokens/:token_id/revoke
Authorization: Bearer <admin api-key>

{} // empty body; revocation event is logged to transparency log
→ 204
→ 404 if token_id not found
```

### 5.25 Quarantine garden operations

```
// Promote a fact from quarantine to a target garden
POST /v1/gardens/:quarantine_garden_id/promote
Authorization: Bearer <api-key> (must hold quarantine:moderator role)

{
  "fact_id":           "<uuid>",
  "target_garden_id":  "<uuid or null for no-garden>",
  "reason":            "Verified provenance."
}
→ 200 { "fact_id": "...", "promoted_at": "...", "promoted_by": "..." }
→ 403 if caller lacks quarantine:moderator
→ 404 if fact_id not found in quarantine garden
→ 409 if fact already promoted or rejected

// Reject a quarantined fact
POST /v1/gardens/:quarantine_garden_id/reject
Authorization: Bearer <api-key> (must hold quarantine:moderator role)

{
  "fact_id": "<uuid>",
  "reason":  "Failed source attestation; untrusted origin."
}
→ 200 { "fact_id": "...", "rejected_at": "...", "rejected_by": "..." }
→ 403 if caller lacks quarantine:moderator
→ 404 if fact_id not found in quarantine garden
→ 409 if fact already promoted or rejected
```

---

## 19. Federation Trust

### 19.1 Org Manifest

#### 19.1.1 Purpose

An **org manifest** is a signed document that declares the canonical public key for a Stigmem node or organisation and the set of entity URIs that the manifest is authoritative for. Peers MUST use the manifest public key to verify capability tokens (§19.3), provenance signatures (§19.6), and recall-time sanitizer trust decisions (§19.7).

#### 19.1.2 Manifest Fields

```
OrgManifest:
  manifest_version:  integer          // MUST be 1 for this spec version
  entity_uri:        URI              // root entity URI; MUST be a stigmem:// URI
  public_key:        base64url        // Ed25519 public key (32 bytes, encoded)
  key_id:            hex              // SHA-256 fingerprint of the raw public key bytes
  entities:          [URI]            // entity URIs this manifest is authoritative for; MUST include entity_uri
  rotation_events:   [RotationEvent]  // ordered history of key rotations (§19.1.4); empty on first publish
  issued_at:         RFC3339          // issuance timestamp
  expires_at:        RFC3339          // expiry; MUST be at least 24h after issued_at
  signature:         base64url        // Ed25519 sig over the canonical JSON encoding of all other fields
```

A manifest MUST be self-consistent: the `signature` MUST verify under the `public_key` declared in the same manifest.

#### 19.1.3 Canonical Encoding

Manifest signing and verification MUST use RFC 8785 (JSON Canonicalization Scheme, JCS) for deterministic byte ordering. Implementations MUST serialize the manifest body (all fields except `signature`) using JCS before signing. Implementations MUST reject manifests where JCS canonicalization of the non-`signature` fields does not reproduce the same bytes that were signed.

#### 19.1.4 Key Rotation

Key rotation events allow a node to cycle its signing key while preserving a verifiable chain of custody back to its original published key.

```
RotationEvent:
  rotated_at:    RFC3339   // timestamp of rotation
  old_key_id:    hex       // key_id of the previous key
  new_key_id:    hex       // key_id of the new key (= current manifest's key_id)
  rotation_sig:  base64url // Ed25519 sig over canonical JSON of { old_key_id, new_key_id, rotated_at }
                           // signed by the OLD private key
```

The `rotation_sig` MUST verify under the public key identified by `old_key_id`. This creates an unbroken chain: the previous key vouches for the new key. Nodes MUST build the rotation chain before trusting a manifest: starting from any previously accepted manifest, each rotation step MUST validate before the chain is considered complete.

Peers that do not have the old manifest cached SHOULD fetch it from the transparency log (§19.2) before verifying the rotation chain.

**Rotation chain invariants:**
1. `rotation_events` MUST be ordered chronologically ascending.
2. Each event's `old_key_id` MUST equal the `key_id` of the preceding entry (or the original manifest's `key_id` for the first rotation).
3. A valid rotation chain MUST terminate with the `new_key_id` matching the current manifest's `key_id`.

#### 19.1.5 Entity URI List

The `entities` array declares which entity URIs this manifest speaks for. An entity URI MUST appear in at most one valid (non-expired) manifest per transparency log epoch. Nodes MUST reject capability tokens and provenance signatures claiming to be from an entity URI that does not appear in the signer's manifest.

#### 19.1.6 Manifest Publication

Nodes MUST publish their manifest at `/.well-known/stigmem-manifest.json`. Nodes SHOULD also submit each new or rotated manifest to the transparency log (§19.2) for independent auditability. A manifest MUST be re-submitted on key rotation.

---

### 19.2 Transparency Log Integration

#### 19.2.1 Purpose

A transparency log provides tamper-evident, append-only evidence that a manifest was published at a given time and has not been backdated or silently revoked. It is the audit anchor for the federation trust model.

#### 19.2.2 Recommended Integration

Implementations SHOULD integrate with [Rekor](https://docs.sigstore.dev/rekor/overview/) (Sigstore's transparency log) or an equivalent OSS log offering:
- Append-only, tamper-evident storage backed by a Merkle tree.
- Public inclusion proofs using signed tree heads (STH).
- An HTTP API for entry submission and proof retrieval.

Implementations MAY operate a self-hosted Rekor instance. A self-hosted log is acceptable for private deployments, but SHOULD be independently accessible to all federation peers.

#### 19.2.3 What We Depend On vs. Require

| Capability | Requirement |
|---|---|
| Inclusion proof for submitted manifests | MUST be supported by the chosen log |
| Consistency proof between log checkpoints | SHOULD be supported |
| Log entry search by key fingerprint | SHOULD be supported |
| Public verifiability (log accessible without auth) | SHOULD hold for public federation deployments |
| Specific log implementation (Rekor) | MAY; alternative logs acceptable if they satisfy the above |

Nodes MUST NOT trust a peer's manifest without a valid inclusion proof when operating in `trust_mode: strict` (see §19.4.3). Nodes operating in `trust_mode: relaxed` MAY accept peer manifests without log verification, but SHOULD log a warning.

#### 19.2.4 Inclusion Proof Format

When submitting a manifest to the log, the node receives a `LogEntry`:

```
LogEntry:
  log_id:            hex          // transparency log's identity
  log_index:         integer      // position in the log
  integrated_time:   RFC3339      // when the entry was appended
  entry_hash:        hex          // SHA-256 of the log entry body
  signed_entry_ts:   base64url    // signed timestamp from the log (Rekor: SignedEntryTimestamp)
  inclusion_proof:   {
    log_index:       integer,
    root_hash:       hex,         // Merkle root of the log at time of proof
    tree_size:       integer,
    hashes:          [hex],       // sibling hashes for Merkle path
    checkpoint:      string       // signed tree head
  }
```

Nodes SHOULD store the `LogEntry` alongside the manifest and serve it at `/.well-known/stigmem-manifest-proof.json`. Peers MUST be able to verify the inclusion proof independently using only the log's public key and the proof data.

#### 19.2.5 Revocation Events

Capability token revocations (§19.3.4) MUST be submitted to the transparency log as a distinct log entry type. This makes revocations independently auditable: a peer can verify a token is revoked by checking the log without trusting the issuing node's runtime state.

---

### 19.3 Capability Tokens

#### 19.3.1 Purpose

A capability token is a signed, short-lived credential that grants a specific named permission to a specific subject from a specific issuer. Tokens replace ad-hoc per-peer trust agreements with a verifiable, revocable, auditable delegation primitive.

#### 19.3.2 Token Shape

```
CapabilityToken:
  token_version: integer    // MUST be 1 for this spec version
  token_id:      UUID       // unique identifier; used for revocation lookup
  issuer:        URI        // entity URI of the issuing node/org (MUST be in issuer's manifest)
  subject:       URI        // entity URI of the token bearer
  verb:          string     // one of: "read" | "write" | "admin" | "federate"
  object:        URI        // resource the verb applies to (scope URI, garden URI, or "*" for any)
  issued_at:     RFC3339
  expiry:        RFC3339    // MUST be set; MUST NOT exceed 90 days from issued_at
  nonce:         hex        // 32 bytes cryptographically random; prevents replay
  signature:     base64url  // Ed25519 sig over canonical JSON of all other fields, signed by issuer key
```

The `verb` values are:
- `read` — bearer may read facts from `object`.
- `write` — bearer may assert facts to `object`.
- `admin` — bearer may manage keys and settings on `object`.
- `federate` — bearer may replicate facts bidirectionally via the federation protocol (§6).

#### 19.3.3 Signing and Verification

The issuer MUST sign the token using the private key corresponding to the `public_key` in their current org manifest (§19.1). Verifiers MUST:
1. Resolve the issuer's org manifest.
2. Verify the manifest's self-signature.
3. Verify the token's `signature` under the manifest's `public_key`.
4. Check that `subject` appears in the issuer's `entities` list or is an external entity the issuer is permitted to delegate to.
5. Check `expiry` > now.
6. Check the token is not revoked (§19.3.4).

A token that fails any of steps 1–6 MUST be rejected.

#### 19.3.4 Revocation

Issuers MAY revoke a token before its expiry by submitting a revocation event to the transparency log (§19.2.5) and calling the local revocation API (§5.24). The revocation event payload:

```
RevocationEvent:
  event_type:    "token_revocation"
  token_id:      UUID       // the token being revoked
  issuer:        URI
  revoked_at:    RFC3339
  reason:        string     // human-readable; SHOULD be informative
  signature:     base64url  // Ed25519 sig over canonical JSON of other fields
```

Nodes that receive a token MUST check for a revocation event before honoring it. Nodes SHOULD cache revocation events with a TTL of no less than 60 seconds.

A revoked token MUST be rejected even if it has not yet expired.

#### 19.3.5 Token Nonce and Replay Prevention

The `nonce` field MUST be 32 bytes of cryptographically random data (e.g., from `/dev/urandom`). Receivers SHOULD maintain a nonce cache for the token's lifetime (from `issued_at` to `expiry`) to detect replays. A nonce that appears in the cache MUST cause the token to be rejected with a `token_replay` error.

---

### 19.4 Source-Trust Score

#### 19.4.1 Purpose

The source-trust score `t` is a scalar in [0.0, 1.0] that expresses how much confidence a node should place in facts asserted by a given source URI. It modulates the effective confidence of recalled facts: `effective_confidence = fact.confidence × t`. This makes the recall layer trust-aware without altering stored fact confidence values.

#### 19.4.2 Derivation Formula

```
t = clamp(
      w_i × identity_strength(source)
    + w_p × peer_history(source)
    + w_s × scope_authority(source, fact.scope)
    + w_a × attestation_mode_factor(node.attestation_mode),
    0.0, 1.0
  )
```

Default weights: `w_i = 0.35, w_p = 0.30, w_s = 0.25, w_a = 0.10`. These MUST be documented in the node's `/.well-known/stigmem` response as `trust_weights` if non-default values are used.

**Component definitions:**

`identity_strength(source)` — a float in [0.0, 1.0] measuring how strongly the source is identified:

| Condition | Value |
|---|---|
| Source has a valid org manifest with current log proof | 1.0 |
| Source has a valid org manifest but no log proof | 0.7 |
| Source has a valid capability token from a trusted issuer | 0.5 |
| Source is a known `entity_uri` registered on a local API key | 0.4 |
| Source is unrecognized but syntactically valid | 0.1 |
| Source is absent or syntactically invalid | 0.0 |

`peer_history(source)` — a float in [0.0, 1.0] derived from the node's interaction history with this source:

| Condition | Value |
|---|---|
| Source has contributed ≥ 100 facts with 0 attestation failures in the past 30 days | 1.0 |
| Source has contributed ≥ 10 facts with < 5% attestation failures | 0.7 |
| Source is new (< 10 facts or no history) | 0.5 |
| Source has a recent attestation failure rate ≥ 5% | 0.3 |
| Source has been explicitly blocklisted by an admin | 0.0 |

Nodes with no peer history MUST default `peer_history` to 0.5.

`scope_authority(source, scope)` — whether the source has the right to assert at this scope level:

| Condition | Value |
|---|---|
| Source holds a valid capability token for this scope with `verb: write` | 1.0 |
| Source is an admin API key holder for this node | 0.9 |
| Source's entity_uri prefix matches the node's authority | 0.7 |
| Source is an external entity with a `federate` token | 0.5 |
| Source has no explicit scope authority | 0.2 |

`attestation_mode_factor(mode)` — contribution of the node's attestation mode:

| Mode | Value |
|---|---|
| `enforce` | 1.0 |
| `warn`    | 0.6 |
| `off`     | 0.2 |

#### 19.4.3 Trust Mode Configuration

Nodes expose a `trust_mode` setting:
- `strict` — nodes MUST verify log inclusion proofs for all peer manifests; `source_trust` is computed for all inbound facts; facts from sources with `t < 0.2` are quarantined (§19.5).
- `relaxed` (default) — nodes SHOULD compute `source_trust` but MUST NOT quarantine facts based solely on a low score; attestation failures are logged.
- `off` — `source_trust` is not computed; `source_trust` field is `null` on all stored facts.

This is configured via `STIGMEM_TRUST_MODE=strict|relaxed|off`.

#### 19.4.4 Recall-Time Multiplier

At recall time, the `effective_confidence` of a fact is computed as:

```
effective_confidence = fact.confidence × t(fact.source)
```

Where `t(fact.source)` is recomputed live at recall time using current peer state (not the stored `source_trust` snapshot). Implementations SHOULD cache per-source trust scores with a TTL of no less than 60 seconds.

Recall results SHOULD include `effective_confidence` alongside `confidence` when `trust_mode` is `strict` or `relaxed`. Callers MUST NOT rely on `effective_confidence` being identical to `confidence`.

#### 19.4.5 Bounds and Defaults

- `t` is always clamped to [0.0, 1.0].
- A source with no computable score (all components unavailable) MUST default to `t = 0.5`.
- Admin blocklisted sources MUST return `t = 0.0` regardless of other components.

---

### 19.5 Quarantine Garden

#### 19.5.1 Purpose

A quarantine garden is a special-purpose Memory Garden (§17) that holds facts pending human or automated review before they are integrated into production scope. It is the first-class mechanism for isolating untrusted, low-trust, or policy-violating facts.

#### 19.5.2 Relationship to §17 Garden Machinery

A quarantine garden is a `Garden` record (§17) with an additional `quarantine: true` flag set at creation time. It inherits all §17 mechanics: it is scope-bound, ACL-controlled, facts within it are isolated from federation, and standard garden CRUD applies.

Differences from a standard garden:
1. A quarantine garden adds a `quarantine:moderator` role (§19.5.3) not present in standard gardens.
2. Facts in a quarantine garden MAY NOT be asserted directly — they are only populated by the node's automatic quarantine policy (§19.5.4) or by explicit operator action.
3. A quarantine garden MUST NOT be deleted while it holds unreviewd facts (status `pending`). Attempting deletion returns HTTP 409 `quarantine_has_pending_facts`.

#### 19.5.3 Roles

Quarantine gardens use the following role model, extending §17's admin/writer/reader:

| Role | Permissions |
|---|---|
| `admin` | All §17 admin permissions; can promote/reject; can add/remove moderators |
| `quarantine:moderator` | Can promote (§5.25) and reject (§5.25) pending facts; read-only otherwise |
| `writer` | Same as §17; cannot promote/reject quarantined facts |
| `reader` | Read-only; can see quarantined facts and review metadata |

The node MUST automatically add the garden's creating principal as `admin`. A quarantine garden MUST have at least one `admin` or `quarantine:moderator` at all times; the API MUST reject the last removal of these roles with HTTP 409.

#### 19.5.4 Automatic Quarantine Policy

When `trust_mode: strict` is set (§19.4.3), the node MUST route inbound federated facts to the node's designated quarantine garden when:
1. The fact's source has `source_trust t < 0.2`, OR
2. The fact's source lacks a valid org manifest, OR
3. The fact fails provenance chain verification (§19.6.3).

When no quarantine garden has been designated, the node MUST reject these facts with HTTP 403 `trust_below_threshold` rather than silently dropping them.

The node MAY also quarantine facts that trigger the recall-time sanitizer (§19.7) in `quarantine` enforcement mode.

#### 19.5.5 Promote and Reject Mechanics

**Promote:** A `quarantine:moderator` or `admin` calls `POST /v1/gardens/:id/promote` (§5.25) with a `target_garden_id`. The node:
1. Moves the fact's `garden_id` to the `target_garden_id` (or clears it for no-garden).
2. Removes the `quarantine:pending` status marker from the fact.
3. Logs a `quarantine_promote` event to the attestation audit log.

**Reject:** A `quarantine:moderator` or `admin` calls `POST /v1/gardens/:id/reject` (§5.25). The node:
1. Sets `confidence = 0.0` on the fact (logical retraction).
2. Sets a `quarantine:rejected` marker.
3. Logs a `quarantine_reject` event to the attestation audit log.

A rejected fact is retained in the quarantine garden for audit purposes. It MUST NOT be served in normal recall results. It MUST be visible to garden admins and moderators via the garden-filtered fact query.

#### 19.5.6 Auditability

All promote and reject events MUST be written to the attestation audit log (§18.10) with the additional fields:

```
quarantine_action: "promote" | "reject"
quarantine_garden_id: <garden_id>
target_garden_id:  <garden_id> | null   // promote only
reason:            string
acted_by:          <entity_uri>
acted_at:          RFC3339
```

The audit log MUST be queryable by `quarantine_garden_id` and `quarantine_action`.

---

### 19.6 Provenance Chain

#### 19.6.1 Purpose

The provenance chain allows a fact to declare its intellectual antecedents (`derived_from`) and carry cryptographic attestations from intermediate processors (`attestation_chain`). Together they create a verifiable lineage from source to recall, enabling detection of data tampering or unexplained derivation gaps.

#### 19.6.2 Fact Hash Computation

A fact hash is the hex-encoded SHA-256 digest of the fact's canonical JSON representation. The canonical form MUST be JCS (RFC 8785) of:

```json
{
  "entity":    "<entity>",
  "relation":  "<relation>",
  "value":     <FactValue>,
  "scope":     "<scope>",
  "source":    "<source>",
  "confidence": <float>,
  "ts":        "<RFC3339>"
}
```

The following fields MUST be excluded from the hash input: `id`, `garden_id`, `attested`, `source_trust`, `derived_from`, `attestation_chain`. This ensures the hash is stable regardless of storage metadata or trust annotations.

#### 19.6.3 Provenance Field Shapes

`derived_from: [FactHash]`
- Each `FactHash` MUST be a 64-character lowercase hex string.
- The array is ordered by logical derivation precedence (first = most direct antecedent).
- An empty array is equivalent to `null` (no declared provenance).
- The referenced facts MUST either exist in the same node or be resolvable via federation. Nodes SHOULD validate that referenced facts exist at write time in `trust_mode: strict`. In `trust_mode: relaxed`, the node MAY log a warning for dangling references.

`attestation_chain: [Signature]`
- Each `Signature` is a base64url-encoded Ed25519 signature over the canonical fact hash (§19.6.2).
- Signatures are ordered from innermost processor to outermost (first processor = index 0).
- Each signature is bound to a specific entity URI by convention: the signing entity MUST include their entity URI in a parallel `attestation_chain_issuers: [URI]` field (same indexing). Implementations MUST include both fields together or neither.
- Verifiers MUST verify each signature in the chain using the corresponding issuer's manifest public key.
- A chain with an invalid signature at any position MUST be rejected entirely.

#### 19.6.4 Verification Rules

A provenance chain is **valid** if all of the following hold:

1. Every `FactHash` in `derived_from` references a fact that exists and whose stored hash matches the declared value.
2. Every signature in `attestation_chain` verifies under the corresponding issuer's current manifest public key.
3. No issuer in `attestation_chain_issuers` appears more than once (no circular attestation).
4. The issuers' entity URIs each appear in their respective manifest's `entities` list.

Nodes MUST reject facts with invalid provenance chains in `trust_mode: strict`. Nodes SHOULD log warnings for invalid chains in `trust_mode: relaxed`.

---

### 19.7 Recall-Time Content Sanitizer

#### 19.7.1 Purpose

The recall-time content sanitizer prevents prompt-injection payloads and malformed values from reaching the recall layer's consumers. It is a defense-in-depth control applied at recall time, not at write time, so that future policy changes can be retroactively applied to already-stored facts.

The sanitizer is NOT applied at write time (storage is a transparent record layer). It is applied immediately before facts are serialized into the API response for `GET /v1/facts` and `GET /v1/recall` endpoints.

#### 19.7.2 Default-Deny Sentinel Patterns

The following patterns are checked against all string-typed `FactValue` fields (`type: "string"`, `type: "text"`) in the recall result. Matches trigger the configured enforcement action (§19.7.4):

```
// Instruction-injection sentinels
\bignore\s+(all\s+)?previous\s+instructions?\b          (case-insensitive)
\bdisregard\s+(all\s+)?previous\s+(prompt|instructions?)\b
\byou\s+are\s+now\s+(?:in\s+)?(?:a\s+)?(?:different|new)\s+mode\b
\bact\s+as\s+(?:an?\s+)?(?:evil|unfiltered|uncensored|dan\b)
\bsystem\s+prompt\s*:\s*
\<\|im_start\|\>
\<\|im_end\|\>
\[INST\]
\[\/INST\]
\bHuman:\s*                         // common chat-template leak
\bAssistant:\s*                     // ditto

// Schema evasion sentinels
\{\s*"__proto__"\s*:                // prototype pollution attempt
\{\s*"constructor"\s*:
```

This list is the default. Operators MAY add patterns via node configuration (`STIGMEM_SANITIZER_EXTRA_PATTERNS` as a newline-delimited regex file). Operators MUST NOT remove default patterns in `trust_mode: strict`.

#### 19.7.3 Schema Enforcement for Typed FactValues

The sanitizer also enforces type correctness for structured `FactValue` types at recall time:

| FactValue type | Enforcement |
|---|---|
| `string` | MUST be a valid UTF-8 string. Control characters (U+0000–U+001F except U+0009, U+000A, U+000D) MUST be removed before return. |
| `number` | MUST be a finite IEEE 754 double. `NaN`, `+Inf`, `-Inf` MUST be replaced with `null` in the response. |
| `bool` | MUST be `true` or `false`. Coercion from `0`/`1` is NOT performed; unexpected values MUST be returned as `null`. |
| `ref` | `v` field MUST be a syntactically valid URI. Malformed refs MUST be replaced with `null`. |
| `json` | MUST be valid JSON. Malformed values MUST be replaced with `null`. |
| `text` | Same as `string`, plus sentinel pattern matching. |

Facts where type enforcement produces a `null` substitution MUST include a `sanitizer_redacted: true` marker in the API response alongside the `null` value.

#### 19.7.4 Enforcement Modes

The sanitizer operates in one of three modes, configured via `STIGMEM_SANITIZER_MODE`:

| Mode | Behavior on match |
|---|---|
| `block` (default in `trust_mode: strict`) | Entire fact is excluded from the recall result. A placeholder `{ "fact_id": "...", "sanitized": true }` is returned in its position. |
| `quarantine` | Fact is moved to the node's quarantine garden (§19.5) and excluded from the current recall result. |
| `warn` (default in `trust_mode: relaxed`) | Fact is returned with `sanitizer_warnings: ["<matched pattern>"]` in the response; content is unmodified. |
| `off` | No sanitizer check; `trust_mode: off` implies this mode. |

Operators MAY configure a more restrictive mode than the `trust_mode` default. Operators MUST NOT configure a less restrictive mode in `trust_mode: strict`.

#### 19.7.5 Placement and Ordering

The sanitizer is the final processing step before serialization in the recall pipeline:

```
Storage layer
  → Scope/garden ACL filter (§17.3)
  → Source-trust multiplier applied to effective_confidence (§19.4.4)
  → Provenance chain verification (§19.6.4, strict mode only)
  → Content sanitizer  ← HERE
  → API response serializer
```

The sanitizer MUST run after trust scoring and provenance verification so that trust metadata is available to the enforcement decision (e.g., facts with `effective_confidence < 0.1` in `quarantine` mode go directly to quarantine without sentinel checking).

#### 19.7.6 Audit Logging

Every sanitizer action (block, quarantine, warn) MUST be logged to the attestation audit log (§18.10) with the following additional fields:

```
sanitizer_action:  "block" | "quarantine" | "warn"
fact_id:           <uuid>
matched_pattern:   string   // the regex that triggered; "schema_enforcement" for type failures
recall_endpoint:   string   // "/v1/facts" or "/v1/recall"
ts:                RFC3339
```

---

### 19.8 Schema Migration (Migration 006)

```sql
-- Org manifest storage
CREATE TABLE IF NOT EXISTS federation_manifests (
  id              TEXT PRIMARY KEY,
  entity_uri      TEXT NOT NULL UNIQUE,
  manifest_json   TEXT NOT NULL,          -- JCS-canonical manifest body
  signature       TEXT NOT NULL,          -- base64url Ed25519 sig
  key_id          TEXT NOT NULL,
  issued_at       TEXT NOT NULL,
  expires_at      TEXT NOT NULL,
  log_entry_json  TEXT,                   -- NULL if not yet submitted to transparency log
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_federation_manifests_entity_uri ON federation_manifests(entity_uri);
CREATE INDEX IF NOT EXISTS idx_federation_manifests_key_id     ON federation_manifests(key_id);

-- Capability token storage
CREATE TABLE IF NOT EXISTS capability_tokens (
  id           TEXT PRIMARY KEY,          -- token_id UUID
  token_json   TEXT NOT NULL,             -- full signed token body (JCS-canonical)
  issuer       TEXT NOT NULL,
  subject      TEXT NOT NULL,
  verb         TEXT NOT NULL,
  object       TEXT NOT NULL,
  issued_at    TEXT NOT NULL,
  expiry       TEXT NOT NULL,
  nonce        TEXT NOT NULL UNIQUE,
  revoked_at   TEXT,                      -- NULL if active
  revoke_log   TEXT,                      -- JSON of RevocationEvent if revoked
  created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capability_tokens_subject  ON capability_tokens(subject);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_issuer   ON capability_tokens(issuer);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_nonce    ON capability_tokens(nonce);
CREATE INDEX IF NOT EXISTS idx_capability_tokens_expiry   ON capability_tokens(expiry);

-- Quarantine metadata extension on facts table
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_status TEXT;
  -- NULL = not quarantined; "pending" = awaiting review; "promoted" = approved; "rejected" = rejected
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_garden_id TEXT REFERENCES gardens(id);
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_acted_by  TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_acted_at  TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS quarantine_reason    TEXT;

-- Provenance chain fields on facts table
ALTER TABLE facts ADD COLUMN IF NOT EXISTS derived_from         TEXT;  -- JSON array of FactHash
ALTER TABLE facts ADD COLUMN IF NOT EXISTS attestation_chain    TEXT;  -- JSON array of base64url sigs
ALTER TABLE facts ADD COLUMN IF NOT EXISTS attestation_chain_issuers TEXT; -- JSON array of URI

-- Source trust snapshot
ALTER TABLE facts ADD COLUMN IF NOT EXISTS source_trust REAL;

CREATE INDEX IF NOT EXISTS idx_facts_quarantine_status ON facts(quarantine_status) WHERE quarantine_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facts_quarantine_garden ON facts(quarantine_garden_id) WHERE quarantine_garden_id IS NOT NULL;
```

---

### 19.9 Error Reference

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `manifest_signature_invalid` | Manifest `signature` does not verify under `public_key` |
| 400 | `manifest_rotation_chain_invalid` | Rotation chain verification fails |
| 400 | `token_nonce_invalid` | Nonce is not 32 bytes or is malformed |
| 400 | `provenance_hash_invalid` | `derived_from` entry is not a 64-char lowercase hex string |
| 403 | `trust_below_threshold` | Fact source `t < 0.2` in `trust_mode: strict` and no quarantine garden configured |
| 403 | `token_expired` | Capability token `expiry` has passed |
| 403 | `token_revoked` | Token found in revocation log |
| 403 | `token_replay` | Token nonce already seen within its validity window |
| 403 | `insufficient_capability` | Bearer's capability token does not cover the requested verb/object |
| 403 | `entity_not_in_manifest` | Source entity_uri not in the issuer's manifest `entities` list |
| 409 | `quarantine_has_pending_facts` | Attempted deletion of quarantine garden with pending facts |
| 409 | `fact_not_quarantine_pending` | Promote/reject attempted on a fact not in `pending` quarantine state |
| 422 | `attestation_chain_mismatch` | `attestation_chain` and `attestation_chain_issuers` array lengths differ |

---

### 19.10 Well-Known Advertisement

Nodes MUST extend their `/.well-known/stigmem` response to include federation trust configuration:

```json
{
  ...existing fields...,
  "federation_trust": {
    "trust_mode":        "strict" | "relaxed" | "off",
    "sanitizer_mode":    "block" | "quarantine" | "warn" | "off",
    "manifest_url":      "https://node.example.com/.well-known/stigmem-manifest.json",
    "manifest_proof_url": "https://node.example.com/.well-known/stigmem-manifest-proof.json",
    "trust_weights": {
      "identity_strength": 0.35,
      "peer_history":      0.30,
      "scope_authority":   0.25,
      "attestation_mode":  0.10
    }
  }
}
```

`trust_weights` MUST be included when non-default values are configured.

---

## Appendix A. Security Policy

*Content unchanged from v1.0 §19 (non-normative).*

The active security policy — supported versions, vulnerability reporting instructions, scope definitions, and the coordinated disclosure timeline — is maintained in [`SECURITY.md`](../SECURITY.md) at the root of the repository.

**Reporting:** Do not open a public GitHub issue for security vulnerabilities. Report via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories). We acknowledge within 48 hours and target a patch within 14 days for critical vulnerabilities.

**Disclosure timeline:** 90 days from the report date before public disclosure, except for vulnerabilities already being actively exploited in the wild.

For the current security posture and Dependabot alert triage covering v1.0-rc, see the [Security Posture section of SECURITY.md](../SECURITY.md#security-posture--v10-rc-2026-05-03).

---
