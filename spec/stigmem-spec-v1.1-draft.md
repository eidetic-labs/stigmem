# Stigmem — Federated Knowledge Fabric + Intent Protocol
## Specification v1.1-draft

**Status:** DRAFT — §19 proposed normative; §20–§22 DRAFT. §1–§18 stable from v1.0.
**License:** Apache-2.0
**Authors:** Eidetic-Labs
**Layer:** Cross-platform federated substrate; sits above company orchestration layers and agent runtimes, below the open internet.
**Changelog:**
- v1.1-draft rev 11 (2026-05-04): §22 Security Hardening — DRAFT normative (Phase 12). Adds §22.1 mTLS federation transport (cipher floor TLS 1.3, cert rotation hook into §19 manifest); §22.2 key rotation (rollover window, 90-day dual-trust period, transparency-log entry shape, SHOULD cadence 90d/365d); §22.3 audit log surface (13 required event types, write-ahead ordering, 90-day retention floor, admin export API); §22.4 per-principal quotas (token-bucket model, 7 default dimensions, 429 backpressure shape); §22.5 replay protection (±5 min clock-skew window, persistent nonce cache, 5 error codes); §22.6 container baseline (distroless, non-root UID 1000, read-only-fs, seccomp normative posture, Cosign image signing); §22.7 transparency log own-instance decision memo (5-criterion gate; reference deployment defers self-hosted Rekor to backlog).
- v1.1-draft rev 10 (2026-05-04): Security re-review amendments. (S1) §21.1.5 rule 1: wake reason MUST be sourced from authenticated control-plane event; runtime MUST NOT accept unverified caller-supplied wake_reason for preload dispatch. (S2) §21.1.5 rule 4: `guarantee_load: true` units MUST cause fatal heartbeat abort if unreachable; non-fatal continues only for `guarantee_load: false` units; preload failures MUST be written to instruction_audit table. (S3) §21.1.5: blast-radius note added — preloaded units exposed to all subsequent task context including adversarial injections. (S4) §21.3.3 rule 3: cap changed from per-deployment to per-agent (max 5/agent); deployment-wide soft cap may emit warning but MUST NOT block individual publishes. (S5) §21.3.3: confidentiality note — guaranteed units accessible to any authorised recall caller including via prompt injection; content MUST NOT rely on retrieval difficulty for confidentiality. (S6) §21.3.3 rule 1: `force_position: "prepend"` MUST require distinct admin approval record; SHOULD be reserved for policy units. (S7) §21.8.3: `skip_coverage_gate: true` on manifests with `guarantee_load: true` entries MUST require dual-admin co-signature; audit event MUST include failing unit names and coverage_pct. (S8) §21.8.3: paraphrase generator data boundary — input MUST be limited to trigger strings; instruction content MUST NOT be sent to external services; external services MUST be in trust manifest. (S9) §21.8.6: peer agent API key querying another agent's coverage MUST return 403 instruction_scope_denied; agent key scoped to own agent_id only. (S10) §21.8.3: 7-day auto-re-certification SHOULD on bypass. (S11) §21.8.6: coverage_status categorical labels SHOULD be restricted to admin-key responses; agent-key responses return raw metrics only.
- v1.1-draft rev 9 (2026-05-04): §21 chronic-miss mitigations. (B) §21.1.5 Task-Type Preloads: `required_by_task_types` manifest field; runtime deterministically injects matching units at heartbeat start before agent context; lint gate on task-type enum; >2 declared task types requires admin sign-off. (A-aug) §21.8.3 augmented manifest certification gate: N=5 paraphrase expansion per intent, top-k coverage check, reject at <80% coverage with `manifest_coverage_failure`; re-certification required on embedding model bump. (C) §21.3.3 guarantee_load: `guarantee_load` boolean on manifest entries; append-by-default; hard budget precedence (guaranteed units never silently dropped); deployment cap of 5 units; `force_position: "prepend"` override for policy units. (D) §21.5.4 expanded: Approach D probe-set + soft-score-lift architecture added as Phase 11 roadmap item; `score += log(1+λ)` lift for coverage-critical units; background audit job; coverage endpoint §21.8.6. New error codes: `manifest_coverage_failure`, `task_type_unknown`, `guarantee_cap_exceeded`.
- v1.1-draft rev 8 (2026-05-04): §21.1.1 defensive guidance — boot stub SHOULD NOT (not MUST NOT) contain operational content; "always-applicable" rules (mandatory escalation thresholds, universal security constraints, hard prohibitions) MAY be embedded directly as the primary mitigation against chronic instruction-scope miss. Deployments SHOULD classify units as "always applicable" vs "task-conditional" at manifest authoring time.
- v1.1-draft rev 7 (2026-05-04): §21.5.3 amendment — endogeneity caveat + §21.5.4 probe-set eval. Adds a non-normative note documenting the `used_chunks` endogeneity limitation (chronic misses invisible to live-audit Recall@k/Hit@k/miss-rate). Adds non-normative §21.5.4 specifying the probe-set complement: curated `(intent, required_units, k)` probes; Probe-coverage@k and Probe-hit@k metrics independent of agent behavior; follow-on spec revision will formalize after live data calibration.
- v1.1-draft rev 6 (2026-05-04): §21 Lazy Instruction Discovery — DRAFT normative (Phase 10). Defines: boot stub (§21.1, ≤500 token preamble with identity + manifest pointer + `recall_instruction` tool schema); instruction manifest (§21.2, ≤1000 token always-loaded index with `load_triggers`); `recall_instruction` tool contract (§21.3, backed by stigmem recall on `instruction:` scope, deterministic + auditable); `instruction:` scope semantics with versioning, provenance requirements, garden isolation, and cross-agent confidentiality (§21.4); discovery audit with replay-based eval shape — Recall@k, Hit@k, miss rate (§21.5); migration semantics and 5-stage deprecation path (§21.6); schema migrations (§21.7); wire format additions (§21.8); error reference (§21.9).
- v1.1-draft rev 5 (2026-05-04): Security review amendments to §§19.3.2, 20.3.3, 20.4.4, 20.5.5, 20.6.2. (S1) §20.5.5 wrong §19.5 cross-ref corrected to §19.3/§19.3.3. (S2) §19.3.2 `subscribe` verb added to capability token verb enum. (S3) §20.5.5 delivery-time validation expanded: token revocation check (§19.3.4) added alongside garden ACL re-evaluation; event content/queue semantics clarified for at-least-once compatibility. (R1) §20.3.3 Stage 2 explicit garden ACL check added; Stage 3 seed garden ACL pre-filter MUST added. (R2) §20.4.4 garden_id ACL check MUST added before card inclusion in recall response. (P1) §20.6.2 auth requirement added: unauthorized root facts MUST return HTTP 403. (P2) §20.6.2 cross-scope oracle fix: unauthorized `derived_from` references MUST be represented as `{"exists": false}` — indistinguishable from absent facts.
- v1.1-draft rev 4 (2026-05-04): Review amendments to §20. (1) §20.2.3 MTEB score corrected to ~53.1. (2) §20.2.4 Matryoshka floor rule added (min 64 dims for nomic-embed-text-v1.5; new error `embed_dimensions_below_floor`). (3) §20.3.2 depth-cap rationale added; default weights marked provisional with eval guidance. (4) §20.3.3 Stage 2 ANN SQL corrected to join `facts` for scope + confidence filtering — normative cross-scope leakage guard. (5) §20.3.4 empty-budget edge-case MUST added.
- v1.1-draft rev 3 (2026-05-04): §20 Recall & Graph — DRAFT normative. Covers graph index (`entity_edges`), embedding storage (`vec_facts`, nomic-embed-text-v1.5 default), recall API (hybrid lexical + vector + graph with MMR packing), memory cards, subscriptions, and causal/derivation links.
- v1.1-draft rev 2 (2026-05-04): Security patch — C1: §19.3.3 step 4 rewritten to remove ambiguous external-entity delegation (Option A); H1: §19.3.3 step 1b added for manifest expiry check with refresh; C2: §19.2.6 "Checkpoint Verification" added with normative Rekor key-discovery and verification procedure, failure-closed behavior, and `sigstore-python` reference; H3: §19.3.4 clarified that revocation TL entries are for auditability only, not inline validation; new error codes `inclusion_proof_invalid` (400) and `transparency_log_unavailable` (503) added to §19.9.
- v1.1-draft (Phase 8): §19 Federation Trust — normative. Replaces the non-normative §19 Security Policy stub from v1.0. Security Policy content moved to Appendix A. §2 extended with `derived_from`, `attestation_chain`, and `source_trust` fields. §19.1–§19.7 cover org manifest, transparency log, capability tokens, source-trust score, quarantine garden, provenance chain, and recall-time sanitizer.
- v1.0 (2026-05-03): Promoted §17 Memory Garden and §18 Source Attestation from draft to normative. All §1–§18 sections stable.
- [Prior changelog in stigmem-spec-v1.0.md]

> **Reading guide:** §1–§18 are unchanged from v1.0. §19 is fully normative in v1.1. §20 is DRAFT normative (Phase 9): graph index, embedding, recall API, memory cards, subscriptions, and causal/derivation links. §21 is DRAFT normative (Phase 10): lazy instruction discovery — boot stub, instruction manifest, `recall_instruction` tool, `instruction:` scope, discovery audit, and migration semantics. §22 is DRAFT normative (Phase 12): security hardening — mTLS transport, key rotation, audit log, quotas, replay protection, container baseline, and transparency log decision memo. §2 and §5 carry v1.1 additions. Appendix A (Security Policy) is unchanged in content from the v1.0 §19 stub.

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
  key_id:            hex              // SHA-256 of the 32-byte raw Ed25519 public key (the base64url-decoded value of `public_key`)
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
  rotation_sig:  base64url // Ed25519 sig over canonical JSON of { entity_uri, old_key_id, new_key_id, rotated_at }
                           // signed by the OLD private key; entity_uri binds the event to its manifest
```

The `rotation_sig` MUST verify under the public key identified by `old_key_id`. This creates an unbroken chain: the previous key vouches for the new key. Nodes MUST build the rotation chain before trusting a manifest: starting from any previously accepted manifest, each rotation step MUST validate before the chain is considered complete.

Peers that do not have the old manifest cached MUST fetch the most recent log entry for the `entity_uri` from the transparency log (§19.2) before accepting or verifying a new manifest.

**Rotation chain invariants:**
1. `rotation_events` MUST be ordered chronologically ascending.
2. Each event's `old_key_id` MUST equal the `key_id` of the preceding entry (or the original manifest's `key_id` for the first rotation).
3. A valid rotation chain MUST terminate with the `new_key_id` matching the current manifest's `key_id`.
4. The `rotation_events` count in a newly published manifest MUST be ≥ the count in the most recently submitted manifest for the same `entity_uri` in the transparency log. Peers MUST reject any manifest where the rotation event count regresses.

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

#### 19.2.6 Checkpoint Verification

The `checkpoint` field in `LogEntry.inclusion_proof` is a signed note in the [transparency-dev/formats](https://github.com/transparency-dev/formats) checkpoint format. Implementations MUST be able to verify it as follows:

1. **Key discovery.** Obtain the log's public key from the log's key discovery endpoint. For Rekor-compatible logs, issue `GET /api/v1/log` against the log instance; the response includes the ECDSA public key (PEM-encoded in the `publicKey.content` field, base64-encoded) used to sign checkpoint notes.

2. **Verification.** For Rekor-compatible logs, implementations MUST verify the checkpoint using the log's published public key as returned by the log's key discovery endpoint. A checkpoint that fails signature verification MUST cause the enclosing inclusion proof to be rejected.

3. **Failure-closed behavior.** If the transparency log is unreachable when an inclusion proof is required (i.e., the node operates in `trust_mode: strict`), the manifest MUST be rejected. Implementations MUST NOT fall back to accepting an unverified manifest in `trust_mode: strict` when the log is unavailable.

4. **Reference implementation.** The `sigstore-python` library (`sigstore.verify`) is the reference implementation for checkpoint and inclusion-proof verification. Implementations in other languages SHOULD follow the same verification flow.

5. **Error codes.** See §19.9 for `inclusion_proof_invalid` (HTTP 400) and `transparency_log_unavailable` (HTTP 503).

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
- `subscribe` — bearer may register a standing event subscription on `object` (scope URI or entity URI).

#### 19.3.3 Signing and Verification

The issuer MUST sign the token using the private key corresponding to the `public_key` in their current org manifest (§19.1). Verifiers MUST:
1. Resolve the issuer's org manifest.
1b. Check `manifest.expires_at > now`; if expired, attempt refresh from the issuer's `/.well-known/stigmem-manifest.json`; reject the token if the manifest is still expired after refresh.
2. Verify the manifest's self-signature.
3. Verify the token's `signature` under the manifest's `public_key`.
4. Check that `subject` appears in the issuer's `entities` list. External-entity subjects are not permitted; cross-org delegation requires the delegatee to obtain their own org manifest and capability tokens.
5. Check `expiry` > now.
5b. Check `expiry` ≤ `issued_at` + 90 days.
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

**Revocation transparency log entries are for auditability, not real-time validation.** Implementations MUST NOT attempt an inline transparency log query as part of per-request token validation; doing so would introduce a synchronous dependency on an external service in the hot path. Real-time revocation checks MUST use the local revocation cache (populated by background sync) and the issuer's revocation API (§5.24). Transparency log entries for revocations exist so that auditors and peers can independently verify that a revocation occurred and when — they are not the authoritative revocation signal for runtime decisions.

#### 19.3.5 Token Nonce and Replay Prevention

The `nonce` field MUST be 32 bytes of cryptographically random data (e.g., from `/dev/urandom`). Receivers MUST maintain a nonce cache in `trust_mode: strict`; receivers SHOULD maintain a nonce cache in `trust_mode: relaxed`. The nonce cache MUST be global (keyed on the nonce value alone, not per-issuer or per-subject) and MUST cover the token's full validity window (from `issued_at` to `expiry`). A nonce that appears in the cache MUST cause the token to be rejected with a `token_replay` error.

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
3. A quarantine garden MUST NOT be deleted while it holds unreviewed facts (status `pending`). Attempting deletion returns HTTP 409 `quarantine_has_pending_facts`.

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
- The `derived_from` reference graph MUST be a DAG. Implementations MUST detect circular references using a visited-set during traversal and MUST reject any fact that would create a cycle with HTTP 400 `provenance_cycle_detected`.
- The referenced facts MUST either exist in the same node or be resolvable via federation. Nodes SHOULD validate that referenced facts exist at write time in `trust_mode: strict`. In `trust_mode: relaxed`, the node MAY log a warning for dangling references.

`attestation_chain: [Signature]`
- Each `Signature` is a base64url-encoded Ed25519 signature over the canonical fact hash (§19.6.2).
- Signatures are ordered from innermost processor to outermost (first processor = index 0).
- `attestation_chain` MUST NOT exceed 16 entries. Nodes MUST reject facts with longer chains with HTTP 400 `attestation_chain_too_long`.
- Each signature is bound to a specific entity URI by convention: the signing entity MUST include their entity URI in a parallel `attestation_chain_issuers: [URI]` field (same indexing). Implementations MUST include both fields together or neither.
- Verifiers MUST verify each signature in the chain using the corresponding issuer's manifest public key.
- A chain with an invalid signature at any position MUST be rejected entirely.

#### 19.6.4 Verification Rules

A provenance chain is **valid** if all of the following hold:

1. Every `FactHash` in `derived_from` references a fact that exists and whose stored hash matches the declared value.
2. Every signature in `attestation_chain` verifies under the corresponding issuer's current manifest public key.
3. No issuer in `attestation_chain_issuers` appears more than once (no circular attestation).
4. The issuers' entity URIs each appear in their respective manifest's `entities` list.
5. If any field included in the fact hash (§19.6.2) is modified after attestation, the node MUST either: (a) clear `attestation_chain` and `attestation_chain_issuers` (treating the updated fact as unattested), or (b) reject the update with HTTP 409 `fact_is_attested`. Nodes MUST NOT retain stale attestation chains after hash-relevant field changes.

Nodes MUST reject facts with invalid provenance chains in `trust_mode: strict`. Nodes SHOULD log warnings for invalid chains in `trust_mode: relaxed`.

---

### 19.7 Recall-Time Content Sanitizer

#### 19.7.1 Purpose

The recall-time content sanitizer prevents prompt-injection payloads and malformed values from reaching the recall layer's consumers. It is a defense-in-depth control applied at recall time, not at write time, so that future policy changes can be retroactively applied to already-stored facts.

The sanitizer is NOT applied at write time (storage is a transparent record layer). It is applied immediately before facts are serialized into the API response for `GET /v1/facts` and `GET /v1/recall` endpoints.

#### 19.7.2 Default-Deny Sentinel Patterns

Before applying sentinel patterns, implementations MUST normalize all string input to Unicode NFKC form. Implementations MUST also strip or reject the following Unicode categories: bidirectional control characters (U+200F, U+200E, U+202A–U+202E, U+2066–U+2069) and invisible formatting characters (U+200B–U+200D, U+FEFF).

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
| 400 | `provenance_cycle_detected` | `derived_from` graph contains a cycle |
| 400 | `attestation_chain_too_long` | `attestation_chain` exceeds 16 entries |
| 403 | `trust_below_threshold` | Fact source `t < 0.2` in `trust_mode: strict` and no quarantine garden configured |
| 403 | `token_expired` | Capability token `expiry` has passed |
| 403 | `token_revoked` | Token found in revocation log |
| 403 | `token_replay` | Token nonce already seen within its validity window |
| 403 | `insufficient_capability` | Bearer's capability token does not cover the requested verb/object |
| 403 | `entity_not_in_manifest` | Source entity_uri not in the issuer's manifest `entities` list |
| 400 | `inclusion_proof_invalid` | Checkpoint signature or Merkle path fails verification; the transparency log inclusion proof is invalid |
| 503 | `transparency_log_unavailable` | The transparency log was unreachable; in `trust_mode: strict`, the manifest MUST be rejected |
| 409 | `quarantine_has_pending_facts` | Attempted deletion of quarantine garden with pending facts |
| 409 | `fact_not_quarantine_pending` | Promote/reject attempted on a fact not in `pending` quarantine state |
| 409 | `fact_is_attested` | Update to a hash-relevant field rejected because `attestation_chain` is present and node is configured to reject rather than clear |
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

## 20. Recall & Graph

**Status:** DRAFT normative (Phase 9). Implementation issues build against this section.  
**Depends on:** §2 (fact shape), §5 (wire format), §17 (memory garden), §18 (source attestation), §19 (federation trust).

§20 defines the graph adjacency index, embedding storage, recall API, memory cards, subscription primitive, and causal/derivation link lifecycle.

---

### 20.1 Graph Index

#### 20.1.1 Purpose

The facts table is a flat relation keyed by entity URI. Entity-to-entity connections exist implicitly: any fact whose `value.type = "ref"` and whose value URI denotes a known entity constitutes a directed edge from the subject entity to the referenced entity. Without a materialized adjacency structure, multi-hop traversal requires O(k × |F|) full table scans per recall query. §20 mandates a materialized `entity_edges` table to enable efficient bounded-depth BFS.

#### 20.1.2 Schema

```sql
CREATE TABLE IF NOT EXISTS entity_edges (
    id              TEXT PRIMARY KEY,      -- edge UUID (= source fact id)
    subject         TEXT NOT NULL,         -- normalized entity URI ("from" node)
    relation        TEXT NOT NULL,         -- predicate / edge label
    object          TEXT NOT NULL,         -- normalized entity URI ("to" node)
    scope           TEXT NOT NULL,
    confidence      REAL NOT NULL,         -- mirrors fact.confidence; updated by decay sweeper
    source_trust    REAL,                  -- cached t(fact.source) per §19.4; nullable
    decay_epoch     INTEGER,               -- Unix ms of last decay sweep touch
    created_at      INTEGER NOT NULL       -- Unix ms
);

CREATE INDEX IF NOT EXISTS idx_edges_subject     ON entity_edges (subject,  scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_object      ON entity_edges (object,   scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel ON entity_edges (subject,  relation, scope);
```

Implementations MUST create this table and all three indexes before accepting `PUT /v1/facts` calls that could produce ref-type values.

#### 20.1.3 Adjacency Invariants

1. **Insert on ref fact.** An `entity_edges` row MUST be inserted whenever a fact is persisted with `value.type = "ref"` and the `v` field passes entity-URI validation. The `id` MUST equal the source fact's `id`. The `object` MUST be the normalized form of the ref target URI.
2. **Decay sweep propagation.** When the decay sweeper updates a fact's `confidence`, it MUST update the corresponding `entity_edges` row's `confidence` and `decay_epoch` in the same transaction.
3. **Retraction soft-delete.** When a fact is retracted (`confidence = 0.0`), the edge row MUST be soft-deleted by setting `confidence = 0.0`, not hard-deleted. Hard deletion is a maintenance-window operation only.
4. **Garden scope.** `entity_edges` rows inherit the fact's `scope`. Cross-garden traversal is governed by the caller's garden ACL checked at the application layer before returning traversal results (§17.3).
5. **Consistency.** An `entity_edges` row MUST NOT outlive the deletion of its source fact from the facts table. Implementations SHOULD use a foreign-key cascade or equivalent constraint to enforce this.

#### 20.1.4 Edge Metadata Fields

| Field | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key; equals the source fact's `id`. |
| `subject` | TEXT (URI) | Normalized "from" entity URI. |
| `relation` | TEXT | Predicate label from the source fact. |
| `object` | TEXT (URI) | Normalized "to" entity URI (the ref target). |
| `scope` | TEXT | Garden or global scope identifier. |
| `confidence` | REAL [0,1] | Current confidence; mirrors and tracks `facts.confidence`. |
| `source_trust` | REAL [0,1] | Cached `t(fact.source)` from §19.4.4. MAY be null for pre-Phase-9 data. |
| `decay_epoch` | INTEGER | Unix ms of last decay sweep update. |
| `created_at` | INTEGER | Unix ms of row creation (= fact insertion time). |

#### 20.1.5 `neighbors()` Query Semantics

The `neighbors()` traversal is the primitive used by the recall pipeline's graph expansion stage and is also exposed directly via `GET /v1/graph/neighbors`.

**Request:**

```
GET /v1/graph/neighbors
  ?entity={entity_uri}
  &depth={k}            // integer 1–3; default 1; MUST reject > 3
  &relation_filter={rel_pattern}  // optional; comma-separated relation labels or glob patterns
  &scope={scope}        // required; MUST NOT traverse across scope boundaries
  &min_confidence={c}   // optional; default 0.1
  &min_trust={t}        // optional; default 0.0
  &cursor={opaque}      // pagination cursor (see §20.1.6)
  &page_size={n}        // default 20; max 200
```

**Response:**

```json
{
  "entity": "https://example.com/entity/alice",
  "depth": 2,
  "neighbors": [
    {
      "entity": "https://example.com/entity/beta-corp",
      "relation": "memory:employer",
      "hops": 1,
      "confidence": 0.92,
      "source_trust": 0.85,
      "path": ["https://example.com/entity/alice"]
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIwfQ",
  "total_hint": 47
}
```

**Normative rules:**

- Implementations MUST cap depth at 3. Requests with `depth > 3` MUST return HTTP 400 with error code `graph_depth_exceeded`.
- Implementations SHOULD prune edges with `confidence < min_confidence` or `source_trust < min_trust` before beginning BFS, not after, to reduce traversal fanout.
- `relation_filter` MAY use `*` as a wildcard suffix (e.g., `memory:*` matches all `memory:` relations). Implementations MUST NOT evaluate `relation_filter` as a full regex; only prefix-glob is supported.
- Duplicate paths to the same neighbor entity MUST be de-duplicated; the shortest path (fewest hops) is reported.

#### 20.1.6 Pagination and Cursor Stability

The `neighbors()` endpoint uses cursor-based pagination. Cursors MUST be:

- Opaque (base64url-encoded) to callers.
- Stable for the lifetime of the underlying fact data: a cursor that was valid before a new fact was inserted MUST continue to work and MUST NOT skip or re-return neighbors that were present at the time the cursor was issued.
- Invalidated (gracefully) after `STIGMEM_CURSOR_TTL_S` seconds (default 300). A request with an expired cursor MUST return HTTP 400 with error code `cursor_expired`.

The server MUST include a `next_cursor` field in the response only when more pages exist. An absent `next_cursor` indicates the final page.

#### 20.1.7 Federation Integrity

The `entity_edges` table is **local-node state**. When facts are received from a federated peer (§19.3), the receiving node MUST apply the same insert / retract / decay invariants (§20.1.3) to its local `entity_edges` table. Edges derived from federated facts MUST record the peer's `source_trust` in the `source_trust` field (as computed per §19.4.4) so that cross-node traversal paths carry trust provenance.

Nodes MUST NOT return federated-source edges in `neighbors()` results when the caller's capability token lacks cross-federation read scope (§19.5.2).

---

### 20.2 Embedding Storage

#### 20.2.1 Vector Table

Implementations MUST use `sqlite-vec` for vector storage. The virtual table schema is:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
    id       TEXT PRIMARY KEY,
    embedding FLOAT[768]         -- default dimensionality; see §20.2.4
);
```

The `id` column is the source fact's `id` for per-fact embeddings, or the string `"card:{entity_uri}:{scope}"` for memory card embeddings (§20.4.2).

#### 20.2.2 Embedding Unit

Each live fact (confidence > `STIGMEM_EMBED_MIN_CONFIDENCE`, default 0.1) MUST be embedded as the composed string:

```
"{entity_display} {relation} {value_text}"
```

where:
- `entity_display` is the last path segment of the entity URI (e.g., `alice` from `https://example.com/entity/alice`).
- `relation` is the fact's relation label.
- `value_text` is: for `value.type = "text"`, the raw `v` string; for `value.type = "ref"`, the last path segment of the ref URI; for `value.type = "number"`, the decimal string; for `value.type = "bool"`, `"true"` or `"false"`.

This 1-to-1 mapping (one embedding per fact row) ensures that vector ANN retrieval returns individual, attributable facts rather than entity-level blobs. Memory card embeddings (§20.4.2) form a secondary, entity-level index.

All embeddings MUST be L2-normalized to unit length on insertion so that cosine similarity reduces to a dot product, enabling sqlite-vec's native dot-product acceleration. Implementations MUST document that raw stored vectors are unit-norm.

#### 20.2.3 Default Model

The default embedding model is `nomic-embed-text-v1.5` (768 dimensions, Apache-2.0, runnable offline via Ollama: `ollama pull nomic-embed-text`). This model is chosen because it is open-weight, runs without network access, and achieves MTEB retrieval avg ~53.1 on the standard benchmark set (MTEB leaderboard, 2025-05-04), which is representative of the fact-recall workload.

Alternative models are supported via environment configuration:

| `STIGMEM_EMBED_PROVIDER` | `STIGMEM_EMBED_MODEL` | Dimensions | Notes |
|---|---|---|---|
| `ollama` (default) | `nomic-embed-text` (default) | 768 | Offline; Matryoshka-capable |
| `ollama` | `mxbai-embed-large` | 1024 | Higher recall; larger memory footprint |
| `openai` | `text-embedding-3-small` | 1536 | Cloud opt-in; requires `OPENAI_API_KEY` |
| `voyage` | `voyage-3-lite` | 512 | Cloud opt-in; requires `VOYAGE_API_KEY` |

#### 20.2.4 Dimensionality Declaration

Each node MUST record its configured embedding dimensionality in the `/.well-known/stigmem` response:

```json
{
  "embedding": {
    "model": "nomic-embed-text-v1.5",
    "provider": "ollama",
    "dimensions": 768,
    "truncated_dimensions": null
  }
}
```

`truncated_dimensions` MAY be set to a smaller integer (e.g., 256) when using Matryoshka-capable models and the operator has configured dimension truncation for resource-constrained deployments. Implementations MUST use only the first `truncated_dimensions` components from the model's output. Implementations MUST document the minimum effective `truncated_dimensions` for each supported model; for `nomic-embed-text-v1.5` this floor is **64 dimensions** — setting `truncated_dimensions` below this value MUST be rejected with error `embed_dimensions_below_floor`.

**Incompatibility rule:** Implementations MUST refuse to mix embeddings of different dimensionalities in the same `vec_facts` table. If `STIGMEM_EMBED_DIMENSIONS` is changed after facts have been indexed, the node MUST refuse to start and emit the error:

```
FATAL: vec_facts dimensionality mismatch: stored=768 configured=1536. Re-index required.
```

Re-indexing is performed by draining and re-inserting all rows into `vec_facts` with the new model. Nodes MUST NOT silently drop or truncate existing embeddings when dimensions change.

#### 20.2.5 Embedding Lifecycle

| Event | Action |
|---|---|
| Fact inserted with confidence > threshold | Embed and insert into `vec_facts` |
| Fact updated (value change) | Re-embed and update `vec_facts` row |
| Fact confidence drops below `embed_tombstone_threshold` (default 0.1) | Delete from `vec_facts` |
| Fact confidence restored above threshold | Re-embed and re-insert into `vec_facts` |
| Fact hard-deleted | Delete from `vec_facts` (MUST be in same transaction) |

Stale low-confidence vectors MUST be deleted; they pollute ANN results with semantically present but epistemically discredited facts.

#### 20.2.6 Contradiction Interaction

Both contradicting facts retain their embeddings. The contradiction penalty is applied at ranking time (§20.3.3), not by modifying stored vectors. Implementations MUST NOT delete or modify the embedding of a contradicted fact; they MUST apply the scoring penalty using the `contradicted` flag from the facts table.

---

### 20.3 Recall API

#### 20.3.1 Route

```
GET  /v1/recall
POST /v1/recall   (preferred when query text is long)
```

The POST form accepts a JSON body identical to the query parameters below. Both forms are equivalent; POST is preferred when `query` exceeds 1000 characters to avoid URI length limits.

The MCP tool `recall` wraps the same endpoint with identical semantics.

#### 20.3.2 Request Shape

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | — | Natural-language or structured query string |
| `token_budget` | integer | Yes | — | Max tokens in the response payload (exclusive of field labels) |
| `depth` | integer | No | 1 | Graph expansion depth for the traversal stage; max 2 (capped lower than `neighbors()` max-3 to bound recall latency at the P95 target) |
| `weights` | object | No | `{lexical:0.30, vector:0.50, graph:0.20}` | Stage weights; MUST sum to 1.0 within ±0.001. **These defaults are provisional** — operators SHOULD re-tune `α`, `β`, `γ` against a held-out probe set (recall@10, MRR) before production use. |
| `include_low_trust` | boolean | No | `false` | If `false`, facts with effective confidence < 0.2 are excluded |
| `entity` | string | No | — | Entity URI; enables entity-centric recall (card-first) |
| `relation` | string | No | — | Relation label filter; skips memory card lookup |
| `scope` | string | No | global | Garden or global scope |
| `include_contradicted` | boolean | No | `false` | Include contradicted facts in results |
| `force_refresh` | boolean | No | `false` | Block on synchronous memory card refresh before responding |
| `lambda_mmr` | float | No | 0.7 | MMR diversity-relevance tradeoff; 1.0 = pure relevance (greedy) |
| `min_confidence` | float | No | 0.1 | Minimum effective confidence for candidate inclusion |

**Validation:**
- Implementations MUST reject `token_budget < 1` with HTTP 400, error code `invalid_token_budget`.
- Implementations MUST reject `depth > 2` with HTTP 400, error code `recall_depth_exceeded`.
- Implementations MUST reject `weights` that do not sum to 1.0 ± 0.001 with HTTP 400, error code `invalid_weights`.

#### 20.3.3 Ranking Pipeline

The recall pipeline runs three stages then fuses their candidate sets.

**Stage 1 — Lexical (FTS5 / BM25):**

```sql
SELECT f.id, bm25(facts_fts) AS bm25_score
FROM facts_fts
WHERE facts_fts MATCH tokenize(query)
  AND scope = :scope
  AND confidence >= :min_confidence
ORDER BY bm25_score
LIMIT 200
```

**Stage 2 — Dense (ANN):**

```sql
SELECT vf.id, vf.distance
FROM vec_facts vf
JOIN facts f ON f.id = vf.id
WHERE vf.embedding MATCH embed(query)
  AND vf.k = 200
  AND f.scope = :scope
  AND f.confidence >= :min_confidence
```

`vec_facts` carries no `scope` column; scope enforcement MUST be applied via the join to `facts` as shown above. Implementations MUST NOT pass ANN results to the fusion stage before this join filter; doing so risks cross-scope leakage. Implementations MUST ALSO verify the caller's garden ACL for each Stage 2 candidate before passing it to fusion — scope filtering alone is insufficient if the caller's garden access does not cover the candidate's `garden_id`.

Cosine similarity `= 1 - distance` for unit-norm vectors.

**Stage 3 — Graph expansion (BFS on `entity_edges`):**

Seed entities are the distinct `entity` values from the union of stage 1 and stage 2 results. Seed entities MUST have their garden ACL verified before BFS expansion begins; entities in unauthorized gardens MUST be dropped as seeds. Expand to depth ≤ `depth` (max 2). For each reached entity, include the top-20 facts by effective confidence. Edge score:

```
graph_score(f at entity e via edge x) =
  (1 / (1 + hops)) × edge.confidence / log(1 + out_degree(x.subject))
```

The `log(1 + out_degree)` denominator is the **hub-bias guard**: it penalizes hub entities (e.g., a root namespace entity with thousands of outbound edges) whose facts would otherwise dominate graph expansion results regardless of query relevance.

**Fusion formula:**

For each candidate fact `f` across all three candidate sets:

```
raw_score(f) = α · norm(bm25(f)) + β · norm(cosine_sim(f)) + γ · norm(graph_score(f))

salience(f)  = recency(f)
             × confidence_weight(f)
             × access_freq_weight(f)
             × contradiction_weight(f)
             × garden_tier(f)

score(f)     = raw_score(f) × salience(f) × source_trust_multiplier(f.source_trust)
```

where `norm(·)` is min-max normalization within the candidate set independently for each stage (missing stage values normalize to 0.0), and:

| Salience signal | Formula | Range |
|---|---|---|
| `recency(f)` | `exp(-0.01 × age_days)` | (0, 1] |
| `confidence_weight(f)` | `f.confidence` | [0, 1] |
| `access_freq_weight(f)` | `log(1 + access_count) / log(1 + max_access_count)` within candidate set | [0, 1] |
| `contradiction_weight(f)` | 1.0 if no unresolved contradiction; 0.7 otherwise | {0.7, 1.0} |
| `garden_tier(f)` | Configurable per garden; default 1.0; quarantine garden default 0.2 | [0, 1] |
| `source_trust_multiplier(t)` | `0.5 + 0.5 × t` (maps [0,1] → [0.5,1.0]); 1.0 when `trust_mode = off` | [0.5, 1] |

The `access_count` field on fact rows MUST be incremented each time a fact appears in a recall response. Implementations SHOULD batch these increments (flush interval ≤ 30s) to avoid write contention.

#### 20.3.4 Token-Budget Packing (MMR)

The scored candidate set is packed into the response using **Maximal Marginal Relevance (MMR)**:

```
next = argmax_{f ∈ R \ selected} [
    λ_mmr · score(f)
  - (1 − λ_mmr) · max_{f_j ∈ selected} cosine_sim(embed(f), embed(f_j))
]
```

The loop runs until the remaining token budget cannot accommodate the next candidate. Implementations MUST estimate token cost as:

```
token_cost(f) = 40 + ceil(len(value_text_utf8) / 4)
```

The constant 40 accounts for field labels, punctuation, and newline overhead per result row. Implementations MUST stay under `token_budget`; they MUST NOT return a partial result row to fit exactly.

**Empty-budget edge case:** When no candidate's `token_cost` fits within the remaining budget — including when `token_budget` is too small to hold even the smallest candidate — implementations MUST return an empty `results` array with `truncated: true` and `tokens_used: 0`. They MUST NOT return HTTP 400; the caller controls budget.

**Exception:** When `entity` is specified (entity-centric recall), MMR MUST be disabled. All facts for that entity in scope are returned sorted by `score` descending, up to the token budget.

#### 20.3.5 Response Shape

```json
{
  "query": "what is Alice's current role?",
  "token_budget": 512,
  "tokens_used": 340,
  "results": [
    {
      "id":          "3f7a…",
      "entity":      "https://example.com/entity/alice",
      "relation":    "memory:role",
      "value":       { "type": "text", "v": "CEO" },
      "confidence":  0.97,
      "source_trust": 0.90,
      "score":       0.843,
      "hops":        0,
      "contradicted": false,
      "card_stale":  false
    }
  ],
  "memory_card": null,
  "truncated": false,
  "scores_debug": null
}
```

- `memory_card` is populated for entity-centric queries (§20.4.4).
- `truncated: true` indicates the result set was cut to fit `token_budget`.
- `scores_debug` MAY be populated (with stage-level scores) when the request includes `debug=true`; MUST be null in production responses.

#### 20.3.6 `include_low_trust` Behavior

When `include_low_trust = false` (default), facts with `effective_confidence = fact.confidence × source_trust < 0.2` MUST be excluded from all three stages before fusion. When `include_low_trust = true`, they are included but the `source_trust_multiplier` still applies, so they rank lower.

---

### 20.4 Memory Cards

#### 20.4.1 Card Definition

A **memory card** is a per-entity synthesized text summary stored as a fact with:

```
entity:   {entity-uri}
relation: stigmem:memory:card
value:    { "type": "text", "v": {card_markdown} }
source:   "system:stigmem:card-generator"
scope:    {same scope as constituent facts}
confidence: 1.0
```

The `confidence = 1.0` field expresses confidence in the card's _existence_, not its content accuracy. Cards are NOT subject to the fact decay sweeper (§20.4.3).

#### 20.4.2 Card Schema

The `value.v` field is structured Markdown:

```markdown
## {entity_display_name}

**Type:** {entity_type}  **URI:** {entity_uri}  **Last refreshed:** {iso8601}

### Current facts ({n} live, {m} contradicted)

| Relation | Value | Confidence | Source | Since |
|----------|-------|------------|--------|-------|
| memory:role | CEO | 1.00 | agent/assistant | 2026-04-01 |
...

### Contradictions ({m} unresolved)

- **memory:role**: `CEO` (conf 1.00) ⟷ `CTO` (conf 0.80) — *unresolved*

### Sources

{n_sources} distinct sources; trust range [{min_t:.2f}, {max_t:.2f}]
```

**Content rules:**
- MUST include all live facts with effective confidence ≥ 0.3 (fact.confidence × source_trust per §19.4.4).
- MUST sort rows by `(relation ASC, hlc DESC)` so the most recent assertion per relation appears first.
- MUST surface contradictions explicitly with both values and their confidences. Cards MUST NOT silently resolve contradictions.
- MUST cap content at 4000 tokens. When an entity's facts exceed this limit, include the highest-confidence facts and append `… {n_omitted} lower-confidence facts omitted`.
- MUST be scoped to a single `(entity, scope, garden_id)` triple where `garden_id` may be null. The card generator MUST NOT mix garden-scoped facts into a cross-garden card.

The card is also embedded as a unit for entity-level semantic search; its `vec_facts` key is `"card:{entity_uri}:{scope}"` (§20.2.1).

#### 20.4.3 Refresh Policy

Cards MUST NOT be subject to confidence decay. They are invalidated and queued for async refresh on these triggers:

| Trigger | Action |
|---|---|
| New fact asserted for entity | Invalidate card; enqueue background refresh |
| Decay sweep touches a constituent fact (confidence changes) | Invalidate card; enqueue background refresh |
| Card age exceeds `STIGMEM_CARD_MAX_AGE_S` (default: 86400 s) | Background job invalidates and refreshes |
| Contradiction resolved via `POST /v1/conflicts/:id/resolve` | Invalidate card; enqueue refresh |

During refresh, the **stale card remains readable** and is served with `card_stale: true`. When `force_refresh = true`, card regeneration is synchronous and MUST complete within 500 ms. If the deadline is exceeded, the stale card (or raw facts if no card exists) MUST be returned with `card_stale: true` and `force_refresh_timeout: true`.

#### 20.4.4 Recall Integration

In `GET /v1/recall`, memory cards are used as follows:

| Condition | Behavior |
|---|---|
| `entity` param specified, no `relation` filter, card exists | Return card as `memory_card`; top-N raw facts as `results` |
| `relation` filter specified | Skip card; return raw facts for that relation |
| Card stale and `force_refresh = false` | Return stale card with `card_stale: true` + top-10 raw facts |
| Card has contradictions and `include_contradicted = true` | Return card + raw fact pairs for each contradiction |
| No card exists | Return raw facts; trigger async card generation |
| Card generation in flight | Return raw facts immediately; do not block |
| Query is not entity-centric (no `entity` param) | Skip card lookup; run full hybrid pipeline on raw facts |

Implementations MUST verify the caller's garden ACL against the card's `garden_id` before including the card in a recall response. Cards in unauthorized gardens MUST be excluded; when a card is excluded, the fallback is raw facts from authorized gardens only (following the rows above as if no card exists).

#### 20.4.5 Divergence Policy

When raw facts contradict the card's synthesized summary (i.e., a fact's current value differs from what was captured in a cached card), the card MUST be invalidated immediately and the divergent fact MUST be included in the `results` array of the recall response with `card_stale: true`. Implementations MUST NOT serve a card whose content is known to be inconsistent with live facts.

---

### 20.5 Subscriptions

#### 20.5.1 Route

```
POST   /v1/subscriptions
GET    /v1/subscriptions
GET    /v1/subscriptions/:id
DELETE /v1/subscriptions/:id
```

#### 20.5.2 Request Shape

```json
{
  "target":           "scope:global" | "entity:{entity_uri}",
  "on_change":        "webhook" | "wake",
  "webhook_url":      "https://example.com/hook",   // required if on_change = "webhook"
  "wake_agent_id":    "{uuid}",                      // required if on_change = "wake"
  "event_filter":     ["fact_assert", "fact_retract", "contradiction_detected", "card_refreshed"],
  "idempotency_key":  "{opaque string}",             // optional; max 128 chars
  "scope":            "{scope_id}"
}
```

- `target` MUST be either a `scope:` prefixed scope identifier or an `entity:` prefixed entity URI.
- `on_change = "webhook"` delivers events to `webhook_url` via HTTP POST. `webhook_url` MUST use HTTPS.
- `on_change = "wake"` wakes the specified agent by triggering a Paperclip wake event on its assigned issue (requires the node to be running inside a Paperclip execution context). For standalone deployments, `wake` MUST return HTTP 422 with error code `wake_not_supported`.
- Subscriptions MUST be scoped to the caller's authorized garden or to the global scope if the caller has global read access (§17.4).
- Duplicate subscriptions (same `target` + `on_change` + `webhook_url`/`wake_agent_id`) MUST be deduplicated using `idempotency_key` if provided, or matched by structural equality if not. A duplicate POST MUST return 200 with the existing subscription.

#### 20.5.3 Event Shape

Events are delivered as JSON payloads with the following structure:

```json
{
  "subscription_id": "{uuid}",
  "event_id":        "{uuid}",
  "event_type":      "fact_assert" | "fact_retract" | "contradiction_detected" | "card_refreshed",
  "entity":          "{entity_uri}",
  "scope":           "{scope_id}",
  "fact_id":         "{uuid}",          // null for card_refreshed events
  "hlc":             "{hlc}",
  "payload":         { ... },            // event-specific; see below
  "idempotency_key": "{event_id}"        // subscribers MUST use this for dedup
}
```

The `idempotency_key` in the delivery envelope MUST equal `event_id`. Subscribers MUST treat deliveries with the same `idempotency_key` as duplicates and discard them after first processing.

#### 20.5.4 Delivery Guarantees

- Implementations MUST deliver each event **at least once**.
- Implementations MUST retry failed webhook deliveries with exponential backoff (initial delay 1s, max 10 attempts, cap 300s).
- A webhook endpoint that returns 5xx or times out (>10s) triggers a retry. A 410 response permanently removes the subscription.
- Implementations MUST maintain a **replay window** of `STIGMEM_SUBSCRIPTION_REPLAY_S` (default 3600s). Subscribers MAY request replay from a given `event_id` using `GET /v1/subscriptions/:id/events?after={event_id}` within this window.
- Events outside the replay window are not recoverable. Implementations SHOULD expose this limit in the subscription response as `replay_window_s`.

#### 20.5.5 Auth and Scoping

Subscription creation MUST require the caller to hold a capability token (§19.3) with verb `subscribe` on the target scope or entity URI. Tokens MUST be validated per §19.3.3 before any subscription is persisted.

The security boundary is critical: a subscription's event stream MUST NOT leak facts from garden-scoped entities to callers without garden read access. At each event delivery, implementations MUST perform the following checks in order:

1. **Token revocation check** — verify the subscriber's capability token is not revoked (§19.3.4). A revoked token MUST be treated the same as access revocation below.
2. **Garden ACL check** — re-evaluate the caller's garden ACL against the event's target entity/scope, not just at subscription creation time.

If either check fails, event content MUST NOT be populated or delivered. The event record MAY be queued internally before these checks to honour at-least-once delivery semantics, but event content MUST be withheld from the subscriber until both checks pass at delivery time. If the caller's access or token has been revoked since subscription creation, delivery MUST be silently dropped (not an error) and the subscription MUST be automatically cancelled with event type `subscription_cancelled_access_revoked`.

This is the primary security concern for the subscription primitive: **cross-garden leakage via event streams**.

---

### 20.6 Causal / Derivation Links

#### 20.6.1 `derived_from` Lifecycle

The `derived_from` field on a fact (§2 v1.1 additions) is a JSON array of FactHash references identifying the source facts from which this fact was inferred or synthesized:

```json
{
  "entity": "https://example.com/entity/alice",
  "relation": "derived:tenure_days",
  "value": { "type": "number", "v": 730 },
  "derived_from": [
    "a3f9c2d1e8b74f6a…",    // 64-char lowercase hex SHA-256 of the start-date fact
    "b7e4d5f2a1c36e9b…"     // 64-char lowercase hex SHA-256 of the current-date fact
  ]
}
```

**Invariants:**

1. Each entry in `derived_from` MUST be a 64-character lowercase hex string (SHA-256 of the referenced fact's canonical wire representation per §5.3).
2. `derived_from` arrays MUST NOT contain cycles. The `PUT /v1/facts` handler MUST verify acyclicity before persisting. Cycles MUST be rejected with HTTP 400, error code `provenance_cycle_detected`.
3. `derived_from` references MAY point to facts that no longer exist (the source fact was retracted). Dangling references are valid — they preserve audit lineage.
4. Implementations MUST NOT alter `derived_from` after the fact is created. `PATCH /v1/facts/:id` MUST reject `derived_from` modifications with HTTP 422, error code `derived_from_immutable`.

#### 20.6.2 Provenance Walk

The provenance walk retrieves the full derivation graph for a given fact, following `derived_from` references recursively.

```
GET /v1/facts/:id/provenance
  ?depth={k}      // max 5; default 3
  &scope={scope}
```

Implementations MUST verify that the caller has read access to the root fact's scope and `garden_id` before executing the walk. Unauthorized root facts MUST return HTTP 403 with error code `access_denied`. No node or edge data MUST be returned for an unauthorized root fact.

**Response:**

```json
{
  "root_fact_id":   "{uuid}",
  "depth_limit":    3,
  "nodes": [
    { "id": "…", "entity": "…", "relation": "…", "value": {…}, "confidence": 0.9, "exists": true },
    { "hash": "a3f9c2d1e8b7…", "exists": false }   // retracted or unauthorized fact
  ],
  "edges": [
    { "derived_fact_id": "…", "source_hash": "a3f9c2d1e8b7…" }
  ],
  "truncated": false
}
```

Nodes with `"exists": false` represent either retracted source facts or facts in unauthorized scopes/gardens. When resolving `derived_from` references during the walk, implementations MUST check the caller's garden ACL for each referenced fact's scope and `garden_id`. Facts in unauthorized scopes or gardens MUST be represented as `{ "hash": "…", "exists": false }` — identical in shape to genuinely absent facts. Implementations MUST NOT confirm or deny the existence of facts in unauthorized scopes or gardens via the provenance walk; the response MUST be indistinguishable from a missing fact to prevent cross-scope inference attacks.

#### 20.6.3 Recall Integration

When `GET /v1/recall` returns a derived fact, its `derived_from` hashes MUST be included in the result object:

```json
{
  "id": "…",
  "entity": "…",
  "relation": "derived:tenure_days",
  "value": { "type": "number", "v": 730 },
  "derived_from": ["a3f9c2d1e8b7…", "b7e4d5f2a1c3…"],
  "confidence": 0.85,
  "score": 0.72
}
```

Implementations SHOULD include the immediate parent facts (depth=1) in the `results` array when their token cost fits within `token_budget`, annotated with `"provenance_of": "{derived_fact_id}"`. This allows consumers to verify derived facts without a separate API call. If the budget is tight, parent facts MUST be omitted (not truncated); the `derived_from` hashes allow a follow-up provenance walk.

Derivation depth contributes to the `graph_score` discount: each additional derivation hop applies a multiplier of 0.9 to the fact's `confidence_weight` salience signal, mirroring the intuition that derived facts carry less epistemic weight than directly observed facts.

#### 20.6.4 Derivation Link and Federation

When a derived fact is replicated to a peer via federation (§19.3), the `derived_from` hashes MUST be transmitted in the wire format. The receiving node MUST store them as-is; it MUST NOT attempt to resolve hashes that it does not have locally. Dangling hashes on the receiving node are valid and MUST NOT prevent the fact from being persisted.

---

### 20.7 Schema Migrations

The following migrations MUST be applied when upgrading to Phase 9 (v1.1 spec compliance):

```sql
-- Graph index
CREATE TABLE IF NOT EXISTS entity_edges ( ... );  -- see §20.1.2
CREATE INDEX IF NOT EXISTS idx_edges_subject     ON entity_edges (subject, scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_object      ON entity_edges (object,  scope, confidence);
CREATE INDEX IF NOT EXISTS idx_edges_subject_rel ON entity_edges (subject, relation, scope);

-- Vector table (sqlite-vec required)
CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
    id        TEXT PRIMARY KEY,
    embedding FLOAT[768]
);

-- Access frequency tracking
ALTER TABLE facts ADD COLUMN IF NOT EXISTS access_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS last_accessed_at INTEGER;  -- Unix ms

-- Subscription table
CREATE TABLE IF NOT EXISTS subscriptions (
    id               TEXT PRIMARY KEY,
    target           TEXT NOT NULL,
    on_change        TEXT NOT NULL CHECK (on_change IN ('webhook', 'wake')),
    webhook_url      TEXT,
    wake_agent_id    TEXT,
    event_filter     TEXT NOT NULL DEFAULT '["fact_assert","fact_retract"]',  -- JSON array
    scope            TEXT NOT NULL,
    idempotency_key  TEXT,
    created_at       INTEGER NOT NULL,
    last_event_at    INTEGER,
    cancelled_at     INTEGER,
    replay_window_s  INTEGER NOT NULL DEFAULT 3600
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_target ON subscriptions (target, scope);

-- Subscription event log (replay buffer)
CREATE TABLE IF NOT EXISTS subscription_events (
    id               TEXT PRIMARY KEY,  -- event UUID
    subscription_id  TEXT NOT NULL REFERENCES subscriptions(id),
    event_type       TEXT NOT NULL,
    entity           TEXT,
    fact_id          TEXT,
    hlc              TEXT,
    payload          TEXT,              -- JSON
    delivered_at     INTEGER,
    created_at       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sub_events_sub_id ON subscription_events (subscription_id, created_at DESC);
```

#### 20.8 Error Reference

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `graph_depth_exceeded` | `neighbors()` or `recall` depth > max allowed |
| 400 | `cursor_expired` | Pagination cursor TTL exceeded |
| 400 | `invalid_token_budget` | `token_budget < 1` |
| 400 | `recall_depth_exceeded` | `depth > 2` on recall request |
| 400 | `invalid_weights` | `weights` values do not sum to 1.0 ± 0.001 |
| 400 | `provenance_cycle_detected` | `derived_from` graph contains a cycle |
| 400 | `invalid_relation_filter` | `relation_filter` uses unsupported regex beyond prefix-glob |
| 422 | `derived_from_immutable` | Attempt to modify `derived_from` on an existing fact |
| 422 | `wake_not_supported` | `on_change = "wake"` on a non-Paperclip deployment |
| 422 | `embed_dimensionality_mismatch` | `vec_facts` configured dimensions differ from stored |
| 404 | `subscription_not_found` | No subscription with given id exists |
| 404 | `fact_not_found` | Provenance walk root fact not found |

---

## 21. Lazy Instruction Discovery

**Status: DRAFT normative (Phase 10)**

This section specifies how agents discover and load their instructions on demand rather than preloading every instruction document at startup. The mechanism has three runtime components — a **boot stub**, an **instruction manifest**, and the **`recall_instruction` tool** — and one off-path component, the **discovery audit**, used for continuous retrieval-quality evaluation.

---

### 21.1 Boot Stub

The boot stub is the minimal agent preamble loaded unconditionally at the start of every heartbeat or session. Its purpose is to give the agent enough context to function and to provide handles for lazy-loading the rest of its instructions.

#### 21.1.1 Required Content

A compliant boot stub MUST contain all of the following fields:

| Field | Description |
|---|---|
| `agent_id` | Stable UUID that uniquely identifies this agent within the deployment |
| `agent_role` | Human-readable role label (e.g. `"CTO"`, `"ResearchScientist"`) |
| `heartbeat_contract` | URI or `instruction:` fact URI pointing to the heartbeat procedure document |
| `manifest_uri` | `instruction:` scope URI for the instruction manifest (§21.2) |
| `recall_tool_schema` | Inline JSON Schema for the `recall_instruction` tool (§21.3); MUST be present so the agent can invoke it without a separate fetch |

The boot stub SHOULD NOT contain operational instruction content — instructions SHOULD be loaded lazily via `recall_instruction`. **Exception:** rules that apply unconditionally on every heartbeat regardless of task type (e.g. mandatory escalation thresholds, universal security constraints, hard "never-do" prohibitions) MAY be embedded directly in the boot stub body. This is the primary mitigation against chronic instruction-scope misses (§21.5.3 limitation note): a rule that is always in context cannot be silently missed by a retrieval failure. Deployments SHOULD classify each instruction unit as either "always applicable" (candidate for boot stub embedding) or "task-conditional" (lazy-load via manifest) during the manifest authoring phase.

#### 21.1.2 Wire Format

The boot stub MUST be serialized as a markdown document with YAML frontmatter:

```markdown
---
agent_id: "8e0ed057-bcd8-4f8f-92ee-c046c55b64e9"
agent_role: "CTO"
heartbeat_contract: "instruction:acme/heartbeat-contract/v1"
manifest_uri: "instruction:acme/agent/cto/manifest/v1"
stub_version: 1
generated_at: "2026-05-04T00:00:00Z"
adapter_profile: "paperclip-claude-code"
migration_mode: "stigmem"
---

# Agent Boot Stub

You are **CTO** (id: `8e0ed057-bcd8-4f8f-92ee-c046c55b64e9`).

Your heartbeat procedure is at `instruction:acme/heartbeat-contract/v1`.
Your instruction manifest is at `instruction:acme/agent/cto/manifest/v1`.

Call `recall_instruction(intent)` to load relevant instruction sections before
performing any non-trivial task. The manifest lists available sections and their
triggers to help you decide when to load.
```

The body section (after the frontmatter) MUST be no longer than **500 tokens** as measured by a cl100k-compatible tokenizer. Implementations SHOULD target ≤ 450 tokens to leave headroom for adapter injection.

#### 21.1.3 Adapter Profiles

The `adapter_profile` frontmatter field allows runtimes to inject adapter-specific content (tool declarations, permission banners, etc.) after boot stub delivery. Supported built-in profiles:

| Profile | Description |
|---|---|
| `paperclip-claude-code` | Injects Paperclip tool definitions and heartbeat harness context |
| `openai-assistants` | Injects OpenAI Assistants tool-call shim |
| `generic` | No runtime injection; stub is delivered as-is |

Implementations MAY define additional profiles. Unknown profiles MUST be treated as `generic`.

#### 21.1.4 Boot Stub Delivery

The boot stub for an agent MUST be retrievable via:

```
GET /v1/agents/{agent_id}/boot-stub[?profile={adapter_profile}]
```

See §21.8.1 for the full wire contract. The boot stub MUST be regenerated whenever the agent's `manifest_uri` changes or the stub schema version increments; stale delivery is a correctness defect, not a warning.

#### 21.1.5 Task-Type Preloads

Immediately after boot stub delivery and before the agent receives any task context, the runtime MUST deliver the content of all manifest units whose `required_by_task_types` array contains the current heartbeat's wake reason. This is called **task-type preloading**. No retrieval scoring is applied; units are fetched deterministically.

Rules:

1. The runtime MUST compare the current wake reason against each manifest entry's `required_by_task_types` array. String comparison is exact and case-sensitive. **The wake reason MUST be sourced from the authenticated heartbeat trigger event (e.g. the control-plane JWT or signed adapter payload). The runtime MUST NOT accept an unverified `wake_reason` claim originating from the agent's task context or any caller-supplied payload when dispatching preloads.** (S1)
2. All matching units MUST be fetched and injected into the agent's context before any task context is provided.
3. Preloaded units MUST be included in the heartbeat's audit record under `loaded_chunks`, tagged with `"source": "task_type_preload"`.
4. If a preloaded unit's `fact_uri` is unreachable, the runtime MUST fall back to `path` if present (with `"source": "fallback_path"`) or MUST surface a `preload_unit_unavailable` warning and continue — a missing preload MUST NOT abort the heartbeat. **Exception: if the unavailable unit also has `guarantee_load: true` in the manifest, the runtime MUST treat unavailability as fatal and MUST abort the heartbeat with a `preload_unit_unavailable` error.** Non-fatal fallback applies only to units with `guarantee_load: false`. In all cases the warning or error MUST be written to the `instruction_audit` table (not only local log) to support replay-based audit (§21.5.3). (S2)
5. Token budget: the combined token cost of boot stub + task-type preloads SHOULD remain under 2000 tokens. Implementations SHOULD emit a `preload_budget_warning` event when this threshold is exceeded but MUST NOT silently drop preloaded units.

Governance:

- Any manifest entry declaring more than **2** `required_by_task_types` values MUST require explicit administrator approval before the manifest can be published (enforced at §21.8.3 as `task_types_approval_required`).
- Build pipelines MUST validate all strings in `required_by_task_types` against the deployment's registered wake-reason enum. Unknown values MUST cause a `task_type_unknown` error at manifest publish time (§21.9).
- The intent of task-type preloads is for structurally-predictable critical units. Authors MUST NOT use `required_by_task_types` as a shortcut to load content that should be retrieved semantically; excessive preload declarations rot into a distributed boot stub.
- **Blast-radius note:** Units declared in `required_by_task_types` are exposed unconditionally to all subsequent task context, including adversarial prompt injections that arrive later in the same heartbeat. Authors SHOULD NOT declare units containing content that must remain confidential from adversarial task payloads. (S3)

---

### 21.2 Instruction Manifest

The instruction manifest is a compact, always-loaded index of every instruction unit available to an agent. It fits in the agent's context without incurring meaningful token cost.

#### 21.2.1 Token Budget

The instruction manifest MUST fit within **1000 tokens** (cl100k). Implementations MUST enforce this at write time and MUST reject a manifest update that would exceed it with error `manifest_too_large` (§21.9). Instruction units SHOULD be described at granular enough detail that `recall_instruction` can select them precisely but coarse enough to stay within budget.

#### 21.2.2 Manifest Entry Shape

Each instruction unit in the manifest MUST be described by the following fields:

```json
{
  "name":                   "security-posture",
  "description":            "Security constraints, escalation thresholds, and hard prohibitions.",
  "required_by_task_types": ["issue_assigned", "issue_commented"],
  "guarantee_load":         false,
  "load_triggers": {
    "intents":    ["security rule", "what am I not allowed to do", "escalation threshold"],
    "keywords":   ["security", "escalate", "prohibited", "never"],
    "task_types": ["issue_assigned", "issue_commented", "routine_fired"]
  },
  "fact_uri":       "instruction:acme/agent/cto/security-posture/v2",
  "path":           null,
  "token_estimate": 320
}
```

| Field | Required | Description |
|---|---|---|
| `name` | MUST | Stable identifier for this instruction unit; MUST be unique within the manifest |
| `description` | MUST | One-line (≤ 120 characters) description of what this unit covers |
| `required_by_task_types` | SHOULD for critical units | Wake-reason strings that cause this unit to be deterministically preloaded at heartbeat start (§21.1.5); entries MUST be registered wake-reason enum values |
| `guarantee_load` | MAY | If `true`, unit is always appended to `recall_instruction` responses regardless of relevance score (§21.3.3); max 5 per agent; requires explicit admin approval; content MUST be safe for any authorised recall caller to observe |
| `load_triggers.intents` | SHOULD | Natural-language intent phrases that SHOULD cause this unit to be loaded |
| `load_triggers.keywords` | SHOULD | Exact or prefix-match keywords; implementations MAY use BM25 matching |
| `load_triggers.task_types` | MAY | Event type strings (e.g. `issue_assigned`) that SHOULD trigger a `recall_instruction` call; distinct from `required_by_task_types` (semantic hint, not deterministic preload) |
| `fact_uri` | MUST if `path` absent | `instruction:`-scope stigmem fact URI for this unit (§21.4) |
| `path` | MUST if `fact_uri` absent | File path relative to the agent's instructions root |
| `token_estimate` | SHOULD | Estimated token count of the full unit content; used for budget planning |

Exactly one of `fact_uri` or `path` MUST be present per entry; an entry with neither or both MUST be rejected with `manifest_entry_invalid`.

> **`required_by_task_types` vs `load_triggers.task_types`:** These are complementary. `required_by_task_types` is a deterministic preload commitment — the runtime unconditionally injects this unit at heartbeat start for the named wake reasons. `load_triggers.task_types` is a semantic hint — it tells the manifest how to describe when a `recall_instruction` call should include this unit, but does not guarantee loading.

#### 21.2.3 Manifest Wire Contract

The manifest is stored as a stigmem fact under the `instruction:` scope (§21.4) and is also surfaced as a structured API resource. See §21.8.2 and §21.8.3.

---

### 21.3 `recall_instruction` Tool Contract

`recall_instruction` is the agent-facing callable that retrieves instruction content on demand. It MUST be available to the agent as a declared tool in all compliant runtimes.

#### 21.3.1 Request Shape

```json
{
  "intent":        "I need to check out an issue and start work",
  "max_chunks":    3,
  "token_budget":  1200,
  "manifest_hint": ["heartbeat-procedure", "checkout-procedure"]
}
```

| Field | Required | Description |
|---|---|---|
| `intent` | MUST | Free-text description of what the agent is about to do or needs help with |
| `max_chunks` | SHOULD | Maximum number of instruction units to return; MUST default to `3` if absent |
| `token_budget` | SHOULD | Soft token budget for the combined response content; MUST default to `2000` if absent |
| `manifest_hint` | MAY | Explicit unit names from the manifest; these are loaded first before ranked retrieval |

#### 21.3.2 Response Shape

```json
{
  "chunks": [
    {
      "name":        "heartbeat-procedure",
      "fact_uri":    "instruction:acme/agent/cto/heartbeat-procedure/v3",
      "content":     "## Heartbeat Procedure\n\n...",
      "tokens":      420,
      "valid_until": "2027-05-04T00:00:00Z",
      "version":     "v3",
      "score":       0.91,
      "source":      "stigmem"
    }
  ],
  "total_tokens":  420,
  "truncated":     false,
  "missed_hints":  [],
  "audit_token":   "audi_01J..."
}
```

| Field | Description |
|---|---|
| `chunks` | Ordered list of instruction units; most relevant first |
| `chunks[].name` | Unit name from the manifest |
| `chunks[].fact_uri` | Stigmem `instruction:` fact URI |
| `chunks[].content` | Full rendered markdown content of the instruction unit |
| `chunks[].tokens` | Actual token count of `.content` |
| `chunks[].valid_until` | Expiry from the backing stigmem fact; agent SHOULD re-call before expiry if session is long |
| `chunks[].version` | Version string of the instruction unit; used in audit logs |
| `chunks[].score` | Relevance score in [0.0, 1.0] used for ordering |
| `chunks[].source` | Either `"stigmem"` or `"fallback_path"` (§21.6.1 co-existence fallback) |
| `total_tokens` | Sum of tokens across all returned chunks |
| `truncated` | `true` if one or more units were dropped to stay within `token_budget` |
| `missed_hints` | Unit names from `manifest_hint` that were not found or not accessible |
| `audit_token` | Opaque token for the discovery audit; MUST be passed to the audit submission endpoint (§21.5.2) |

#### 21.3.3 Backing Implementation

`recall_instruction` MUST be implemented as a stigmem `recall` call (§20.3) restricted to the `instruction:` scope (§21.4.1):

```json
POST /v1/recall
{
  "scope":              "instruction:{deployment}/{agent_id}",
  "intent":             "{agent-provided intent string}",
  "max_facts":          "{max_chunks}",
  "token_budget":       "{token_budget}",
  "weights":            { "lexical": 0.35, "semantic": 0.50, "graph": 0.15 },
  "require_garden_ids": ["{agent_instruction_garden_id}"]
}
```

The `require_garden_ids` constraint MUST be applied so that `recall_instruction` cannot return facts from gardens the agent is not authorized to read (§17, §19.3). Implementations MUST apply the garden ACL check at recall time using the caller's capability token.

If `manifest_hint` is provided, the named units MUST be included in the result (subject to `token_budget`) before the ranked retrieval results. If a hinted unit does not exist or is not accessible, it MUST be silently omitted (not an error) and its name MUST appear in `missed_hints`.

**Guaranteed units (`guarantee_load: true`):** After ranked and hinted results are assembled, the implementation MUST append all manifest units with `guarantee_load: true` that were not already included. The following rules govern their inclusion:

1. **Position:** guaranteed units MUST be appended after ranked results by default, so that ranked results (higher expected relevance) receive attention primacy. A unit with `force_position: "prepend"` in its manifest entry MUST be prepended instead. **A unit with `force_position: "prepend"` MUST undergo explicit content review at manifest publish time, recorded in provenance metadata, and MUST require a distinct admin approval record separate from the general `guarantee_load` approval.** The `force_position: "prepend"` override SHOULD be reserved for universal policy units where omission risk outweighs priming risk. (S6)
2. **Budget precedence:** guaranteed units MUST NOT be silently dropped by `token_budget` exhaustion. If budget is exhausted after ranked results, the implementation MUST still append guaranteed units and MUST set `truncated: true`. Ranked results are truncated first to make room; guaranteed units are truncated last but never to zero.
3. **Agent cap:** at most **5** manifest units **per agent** may have `guarantee_load: true`. Manifest publish MUST be rejected with `guarantee_cap_exceeded` if this per-agent limit would be exceeded (§21.9). A deployment-wide soft cap MAY be configured; exceeding it SHOULD emit a warning event but MUST NOT block individual agent manifest publishes. (S4)
4. **Relevance threshold:** implementations SHOULD warn (non-fatal) if a guaranteed unit has an empirical `P(relevant | recall_invoked) < 0.6` based on the discovery audit; this is a signal to remove the `guarantee_load` flag from that unit.
5. **Governance:** setting `guarantee_load: true` on any manifest entry requires explicit administrator approval. The approval MUST be recorded in the manifest's provenance metadata.
6. **Confidentiality note:** guaranteed units are appended to every `recall_instruction` response and are therefore accessible to any principal authorised to invoke `recall_instruction` for this agent, including via prompt injection. Content in guaranteed units MUST NOT rely on retrieval difficulty for confidentiality. Guaranteed units MUST only contain content that is acceptable for any authorised recall caller to observe. (S5)

#### 21.3.4 Determinism and Auditability

The same `(intent, manifest_hint, max_chunks, token_budget)` tuple MUST produce the same ordered result given the same set of instruction facts at the same `valid_until` boundaries. This determinism property enables replay-based audit (§21.5.3).

Implementations MUST record every `recall_instruction` invocation in the discovery audit table (§21.5.1) before returning the response. If audit write fails, the response MUST still be returned (audit is best-effort); the failure MUST be logged as `audit_write_failed`.

---

### 21.4 `instruction:` Scope Semantics

The `instruction:` URI scheme is a reserved stigmem scope for agent instruction artifacts. It extends §17 (Memory Garden) and §19 (Federation Trust) with instruction-specific semantics.

#### 21.4.1 Scope Namespace

`instruction:` URIs follow the pattern:

```
instruction:{deployment}/{agent_id}/{unit_name}/{version}
```

Where:
- `{deployment}` is the deployment identifier (e.g. `acme`); MUST match the `entity_uri` root in the org manifest (§19.1).
- `{agent_id}` is the stable agent UUID or a well-known shortname (e.g. `cto`).
- `{unit_name}` is the instruction unit name from the manifest.
- `{version}` is a version string (e.g. `v1`, `v3`); MUST be monotonically incrementing; MUST NOT be a floating alias (e.g. `latest`).

The special URI `instruction:{deployment}/{agent_id}/manifest/{version}` addresses the agent's instruction manifest itself.

#### 21.4.2 Versioning

Instruction facts are **mutable** in the sense that a new version supersedes the old, but individual versioned facts are **immutable** once written. The following rules apply:

1. A new version MUST be written as a new fact (new `id`, new `version` string) rather than mutating an existing fact.
2. The previous version's `valid_until` MUST be set to the new version's `created_at` within the same transaction, or within a 30-second grace window.
3. `recall_instruction` MUST return only the latest version (highest version string by semantic version ordering, or by `created_at` if versions are non-comparable strings).
4. Agents MAY cache instruction chunks for the duration of a heartbeat/session. Agents MUST NOT cache across heartbeats unless the `valid_until` extends past the next expected heartbeat time.

#### 21.4.3 Provenance

Every instruction fact MUST carry:

| Field | Requirement |
|---|---|
| `source_trust` | MUST be populated at write time (§19.4); instruction facts authored by verified human administrators SHOULD have `source_trust >= 0.9` |
| `attestation_chain` | MUST include at least one signature from an org manifest key (§19.2); unsigned instruction facts MUST be quarantined (§19.5) |
| `derived_from` | SHOULD reference the instruction unit's prior version hash when updating; `null` is valid for the first version |
| Metadata `authored_by` | MUST be the `entity_uri` of the human or system that created this version |
| Metadata `authored_at` | MUST be an ISO 8601 timestamp |

#### 21.4.4 Garden Membership

All instruction facts MUST be placed in a dedicated instruction garden, separate from operational fact gardens. The naming convention is:

```
garden_id: "instruction:{deployment}:{agent_id}"
```

Access MUST be restricted to:
- The agent itself: read-only via capability token with verb `read`
- Deployment administrators: read + write via admin API key
- Peer agents: MUST NOT have read access to another agent's instruction garden unless explicitly granted; cross-agent instruction access is a confidentiality boundary (§21.4.5)

#### 21.4.5 Cross-Agent Confidentiality

An agent's instruction facts MAY contain sensitive operational details including security postures, escalation paths, and negotiation limits. The following rules enforce confidentiality:

1. A capability token granting `read` on `instruction:{deployment}/{agent_A}/*` MUST NOT be derived from a token held by `agent_B` unless `agent_B`'s role is a declared supervisor of `agent_A` in the org manifest.
2. Federation (§19.3) MUST NOT replicate instruction-scope facts to peer nodes unless the receiving node is in the same deployment trust domain.
3. The `recall_instruction` API endpoint MUST validate that the calling agent's token scope matches the instruction garden of the agent whose manifest is being queried; cross-agent recall MUST return `403 instruction_scope_denied`.
4. Audit logs for instruction recall MUST be accessible to administrators but MUST NOT be surfaced to peer agents.

---

### 21.5 Discovery Audit

The discovery audit provides a per-heartbeat signal for tuning manifest descriptions and `load_triggers`. It enables evaluation of retrieval quality by comparing what was loaded against what was actually used.

#### 21.5.1 Audit Record Shape

```json
{
  "id":            "audevent_01J...",
  "agent_id":      "8e0ed057-bcd8-4f8f-92ee-c046c55b64e9",
  "heartbeat_id":  "run_ad74de74...",
  "session_start": "2026-05-04T12:00:00Z",
  "intent":        "I need to check out an issue and start work",
  "loaded_chunks": ["heartbeat-procedure", "checkout-procedure"],
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": [],
  "audit_token":   "audi_01J...",
  "audit_closed":  "2026-05-04T12:01:05Z",
  "created_at":    "2026-05-04T12:00:02Z"
}
```

| Field | Description |
|---|---|
| `id` | Globally unique audit event ID with `audevent_` prefix |
| `agent_id` | Agent that performed the recall |
| `heartbeat_id` | Run/heartbeat ID in which the recall occurred |
| `session_start` | ISO 8601 timestamp of the heartbeat start |
| `intent` | The `intent` string passed to `recall_instruction` |
| `loaded_chunks` | Unit names returned by `recall_instruction` in this invocation |
| `used_chunks` | Unit names the agent demonstrably applied (runtime-tracked or self-reported) |
| `missed_chunks` | Unit names the agent referenced but that were not in `loaded_chunks` (self-reported or post-hoc replay) |
| `audit_token` | Must match the `audit_token` returned in the `recall_instruction` response |
| `audit_closed` | Timestamp when the audit submission was received; `null` until POST /audit |
| `created_at` | Write timestamp of the initial record |

`used_chunks` and `missed_chunks` MAY be populated by the runtime (if it tracks tool-call traces) or by the agent via self-report at heartbeat end. Agents SHOULD self-report usage when runtime tracking is unavailable.

#### 21.5.2 Audit Submission API

```
POST /v1/instruction/audit
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "audit_token":   "audi_01J...",
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": []
}
→ 204 No Content on success
→ 400 audit_token_invalid  if token not recognized or already fully closed
→ 400 audit_token_expired  if token is older than 24 hours
```

The audit endpoint MUST be idempotent: a second submission with the same `audit_token` MUST return `204` without modifying the record.

#### 21.5.3 Replay-Based Evaluation

The audit table is append-only and replay-able. The evaluation metrics are:

**Recall@k**: fraction of `used_chunks` that appear in `loaded_chunks` within rank k.  
**Hit@k**: fraction of heartbeats where at least one `used_chunk` was in `loaded_chunks`.  
**Miss rate**: `|missed_chunks| / (|used_chunks| + |missed_chunks|)`.

These metrics SHOULD be computed over a rolling 7-day window. Deployments SHOULD alert when `miss_rate > 0.15` over 100+ events, as this indicates manifest descriptions or triggers need improvement.

Replay procedure: given an audit record with `intent` and the stigmem state at `session_start`, re-execute `recall_instruction(intent)` and compare results to `loaded_chunks`. Determinism (§21.3.4) guarantees the replay is reproducible.

The `recall@k` and `hit@k` metrics SHOULD be computed against the post-hoc replay set (ground truth: all instruction units the agent actually needed, reconstructed from the full heartbeat trace) to measure manifest coverage independently of what the agent happened to load.

> **Known limitation — endogeneity of `used_chunks` (non-normative):** Recall@k, Hit@k, and miss rate are all computed relative to `used_chunks`, which is itself derived from agent behavior during the heartbeat being measured. An agent that chronically fails to load a required instruction unit will never reference it, so the unit will never appear in `used_chunks`. The chronic miss is therefore invisible to all three live-audit metrics. This is an accepted limitation for Phase 10: the live audit is a useful signal for units the agent *does* interact with, but it cannot independently surface units the agent has never successfully retrieved.
>
> #### 21.5.4 Probe-Set Eval (follow-on, non-normative)
>
> To complement the endogenous live-audit metrics with an exogenous coverage signal, implementations SHOULD maintain a **probe set**: a curated list of `(intent, required_units)` pairs administered independently of the live agent. After every manifest update and on a periodic schedule (e.g. daily), run `recall_instruction(intent)` against each probe and compute:
>
> **Probe-coverage@k**: fraction of `required_units` in each probe that appear in the top-k recall result.  
> **Probe-hit@k**: fraction of probes where ≥ 1 `required_unit` appears in the top-k result.
>
> Unlike live-audit Recall@k, these metrics are independent of agent behavior — a chronically un-loaded unit will fail the probe that covers it even if no live heartbeat ever referenced it.
>
> The probe set SHOULD be curated by deployment administrators. Each probe entry MUST specify:
>
> ```json
> {
>   "probe_id":       "probe_heartbeat_start",
>   "intent":         "I am starting a new heartbeat and need to know what to do",
>   "required_units": ["heartbeat-procedure", "checkout-procedure"],
>   "k":              3
> }
> ```
>
> A follow-on spec revision (Phase 11) will formalize the probe-set storage format, the evaluation runner contract, alert thresholds, and the soft-lift mechanism described below.
>
> #### 21.5.5 Probe-Set Coverage Sampling with Soft Score Lift (Phase 11 roadmap, non-normative)
>
> Approaches B and augmented A (§21.1.5, §21.8.3) address structurally-predictable and trigger-quality misses at authoring time. The residual problem — semantic-drift misses and embedding-model staleness causing gradual coverage degradation without any live-audit signal — requires an exogenous coverage signal independent of both the retrieval path and agent behavior.
>
> **Architecture (non-normative):**
>
> 1. **Probe-set construction:** At manifest publish time, generate M=15–20 synthetic queries per unit by combining the unit's `description` with each `load_triggers.intents` string, paraphrased via a diverse augmentation pass (lexical + syntactic variation, not just dense neighbours). Store per unit as `{unit_id → [q_1 … q_M]}` in the manifest DB. Re-generated on unit update.
>
> 2. **Background coverage audit:** A scheduled job (runs daily and on every embedding-model version bump) runs all probes through the live retrieval index. Computes per-unit `hit@10` across the M probes. Units with `hit@10 < 0.4` are flagged as *coverage-critical*.
>
> 3. **Soft score lift for coverage-critical units:** Flagged units receive a log-additive ranking boost applied within the recall engine: `score += log(1 + λ)` where λ ≈ 0.15. This lifts chronically under-retrieved units without forcing them into context unconditionally — they only appear if they are in the semantic neighbourhood of the actual query. No irrelevant units are injected; the noise properties of Approach C are avoided entirely.
>
> 4. **Coverage endpoint:** `GET /v1/agents/{agent_id}/instruction-manifest/coverage` (§21.8.6) returns per-unit `hit@10` and `coverage_status` so authors can diagnose units before production misses occur.
>
> 5. **Probe-set calibration:** The probe set SHOULD be seeded with real heartbeat intent strings (10% sample, PII-stripped) on a weekly cadence to keep the distribution calibrated to actual agent query patterns.
>
> This approach addresses the root cause of endogeneity by making the miss-rate signal exogenous, and makes embedding-model drift visible as a measurable per-unit delta across versions.

---

### 21.6 Migration Semantics

This section defines the co-existence and deprecation path for agents transitioning from file-based instructions to `instruction:`-scope stigmem facts.

#### 21.6.1 Co-existence Period

During migration, an agent MAY have both:
- A static markdown instruction file (e.g. `AGENTS.md`) at a file path, and
- A manifest with `fact_uri` entries pointing at stigmem.

The following resolution rules apply:

1. If a manifest entry has both `fact_uri` and `path`, `fact_uri` MUST take precedence.
2. If `fact_uri` lookup fails (fact not found or scope unreachable), the runtime MUST fall back to `path` if present and MUST append `"source": "fallback_path"` to the returned chunk.
3. File-path entries are read-only; they MUST NOT be written via `recall_instruction` or the instruction API.
4. The boot stub MUST indicate migration state via the `migration_mode` frontmatter field:
   - `"file"` — no manifest; static file only
   - `"coexistence"` — both static file and manifest entries present
   - `"stigmem"` — manifest only; no file fallback

#### 21.6.2 Deprecation Path

The deprecation sequence for an instruction unit is:

| Stage | Action |
|---|---|
| 1. Seed | Write instruction content to stigmem as `instruction:` facts; verify recall quality over ≥ 5 heartbeats |
| 2. Coexist | Add `fact_uri` to the manifest entry alongside existing `path`; set `migration_mode: "coexistence"` |
| 3. Verify | Monitor audit metrics (§21.5.3) for 7 days; confirm `miss_rate < 0.10` |
| 4. Promote | Remove `path` from the manifest entry; set `migration_mode: "stigmem"` |
| 5. Archive | Move the source markdown file to `docs/legacy-instructions/` with a redirect comment pointing to the `fact_uri` |

Deployments MUST NOT skip Stage 3 (Verify) for agents that handle sensitive operational decisions. The risk of an undetected miss in a security-relevant instruction unit is higher than the cost of a 7-day observation window.

#### 21.6.3 Bulk Migration Tooling

Implementations SHOULD provide a `stigmem migrate-instructions` CLI command that:

1. Reads all entries from an existing markdown instruction file.
2. Splits at H2/H3 section boundaries (or at a configurable split regex).
3. Writes each section as an `instruction:` fact with attestation from the local admin key.
4. Emits a manifest `entries` array for copy-paste into the manifest file.
5. Does NOT automatically update the manifest or boot stub; the operator MUST review and commit the change manually.

This is a SHOULD (not MUST) because manual migration is always acceptable.

---

### 21.7 Schema Migrations

The following DDL MUST be applied when upgrading to Phase 10 (§21 compliance):

```sql
-- Instruction manifest registry
CREATE TABLE IF NOT EXISTS instruction_manifests (
    id               TEXT PRIMARY KEY,           -- UUID
    agent_id         TEXT NOT NULL,
    version          TEXT NOT NULL,
    fact_uri         TEXT NOT NULL,              -- instruction: scope URI
    token_count      INTEGER NOT NULL,
    body             TEXT NOT NULL,              -- JSON: array of manifest entries
    created_at       INTEGER NOT NULL,           -- Unix ms
    superseded_at    INTEGER,                    -- NULL if current version
    UNIQUE(agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_manifests_agent ON instruction_manifests (agent_id, superseded_at NULLS FIRST);

-- Discovery audit log (append-only)
CREATE TABLE IF NOT EXISTS instruction_audit (
    id               TEXT PRIMARY KEY,           -- audevent_ prefixed UUID
    agent_id         TEXT NOT NULL,
    heartbeat_id     TEXT NOT NULL,
    session_start    INTEGER NOT NULL,           -- Unix ms
    intent           TEXT NOT NULL,
    loaded_chunks    TEXT NOT NULL,              -- JSON array of unit names
    used_chunks      TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    missed_chunks    TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    audit_token      TEXT NOT NULL UNIQUE,
    audit_closed     INTEGER,                    -- Unix ms; NULL until POST /audit received
    created_at       INTEGER NOT NULL            -- Unix ms
);
CREATE INDEX IF NOT EXISTS idx_audit_agent_session ON instruction_audit (agent_id, session_start DESC);
CREATE INDEX IF NOT EXISTS idx_audit_token         ON instruction_audit (audit_token);

-- Boot stub cache (invalidated on manifest update)
CREATE TABLE IF NOT EXISTS boot_stubs (
    agent_id          TEXT NOT NULL,
    adapter_profile   TEXT NOT NULL DEFAULT 'generic',
    stub_version      INTEGER NOT NULL DEFAULT 1,
    body              TEXT NOT NULL,              -- full markdown stub
    token_count       INTEGER NOT NULL,
    generated_at      INTEGER NOT NULL,           -- Unix ms
    manifest_version  TEXT NOT NULL,              -- version string of backing manifest
    PRIMARY KEY (agent_id, adapter_profile)
);
```

---

### 21.8 Wire Format Additions

The following routes supplement §5. Implementations MUST provide all MUST-labelled routes to claim §21 compliance.

#### 21.8.1 Get Boot Stub (MUST)

```
GET /v1/agents/{agent_id}/boot-stub[?profile={adapter_profile}]
Authorization: Bearer <agent api-key or admin api-key>

→ 200 Content-Type: text/markdown
      X-Stub-Version: 1
      X-Manifest-Version: v3
      X-Token-Count: 420
      [stub body]

→ 403 if caller is not the agent itself or an admin
→ 404 if agent not found or no stub generated yet
```

If `profile` is absent, MUST default to `generic`. Unknown profiles MUST be treated as `generic` (no error).

#### 21.8.2 Get Instruction Manifest (MUST)

```
GET /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <agent api-key or admin api-key>

→ 200 {
    "manifest_version": "v3",
    "fact_uri": "instruction:acme/agent/cto/manifest/v3",
    "token_count": 840,
    "entries": [ ...entry objects per §21.2.2... ],
    "last_updated_at": "2026-05-04T00:00:00Z"
  }
→ 403 if caller is not the agent itself or an admin
→ 404 if no manifest configured for agent
```

#### 21.8.3 Publish / Replace Instruction Manifest (MUST)

```
PUT /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "version": "v4",
  "entries": [ ...entry objects per §21.2.2... ],
  "skip_coverage_gate": false
}

→ 200 {
    "fact_uri":       "instruction:acme/agent/cto/manifest/v4",
    "token_count":    910,
    "coverage_report": [
      { "unit": "security-posture", "coverage_pct": 0.95, "passed": true },
      { "unit": "escalation-path",  "coverage_pct": 0.60, "passed": false }
    ]
  }
→ 400 manifest_too_large              if token_count > 1000
→ 400 manifest_entry_invalid          if any entry has neither or both of fact_uri/path
→ 400 manifest_coverage_failure       if any unit fails the paraphrase coverage gate (see below)
→ 400 task_type_unknown               if any required_by_task_types value is not a registered wake-reason string
→ 400 guarantee_cap_exceeded          if more than 5 entries have guarantee_load: true
→ 400 task_types_approval_required    if any entry declares > 2 required_by_task_types values without recorded admin approval
→ 409 manifest_version_conflict       if version already exists (versions are immutable)
```

**Augmented manifest coverage gate (Approach A):** This route MUST run a paraphrase-expansion coverage check before accepting a manifest. For each unit in the incoming manifest:

1. For every string in `load_triggers.intents`, generate N=5 paraphrases using lexically and syntactically diverse augmentation (MUST NOT use the retrieval encoder's own nearest-neighbour space as the sole paraphrase source).
2. Run `recall_instruction(paraphrase)` for each generated paraphrase and check whether this unit appears in the top-k results (default k=3).
3. Compute `coverage_pct = (paraphrases where unit in top-k) / (total paraphrases)`.
4. If `coverage_pct < 0.80` for any unit, the entire publish MUST be rejected with `manifest_coverage_failure`, identifying the failing unit(s).

`skip_coverage_gate: true` MAY be used by administrators to bypass the coverage check (e.g. for bootstrap or emergency update); the bypass MUST be recorded in the manifest's provenance metadata and MUST emit an audit event that includes the names and `coverage_pct` values of all units that would have failed the gate. **When `skip_coverage_gate: true` is used on a manifest containing any `guarantee_load: true` entry, the bypass provenance record MUST include co-signatures from at least two distinct administrators (two distinct `authored_by` entity URIs). Single-admin bypass is permitted only for manifests with no `guarantee_load: true` entries.** (S7) Implementations SHOULD automatically schedule re-certification within 7 days when `skip_coverage_gate: true` is used. (S10)

**Paraphrase generator data boundary:** Paraphrase generation input MUST be limited to `load_triggers.intents` strings only. Instruction fact content (the body of instruction units) MUST NOT be sent to any external paraphrase generation service. If an external service is used for paraphrase generation, it MUST be listed in the deployment's trust manifest (§19.1) and covered by an appropriate data processing agreement. Implementations SHOULD prefer local, deterministic paraphrase methods for deployments handling confidential instruction content. (S8)

**Re-certification requirement:** When the deployment's embedding model version changes, all existing manifests MUST be re-certified through this gate before the new model version is activated for production recall. Implementations MUST expose the current embedding model version in the `GET /v1/agents/{agent_id}/instruction-manifest` response.

This route MUST atomically: (1) run coverage gate, (2) write the manifest fact to stigmem under `instruction:` scope, (3) update `instruction_manifests` table, (4) invalidate the boot stub cache for this agent.

#### 21.8.4 Recall Instructions (MUST)

```
POST /v1/agents/{agent_id}/recall-instruction
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "intent":        "I need to check out an issue and start work",
  "max_chunks":    3,
  "token_budget":  1200,
  "manifest_hint": ["heartbeat-procedure"]
}

→ 200 { ...response shape per §21.3.2... }
→ 400 intent_required          if intent is absent or empty
→ 403 instruction_scope_denied if agent token scope does not match agent_id
→ 404 if agent not found
→ 503 recall_backend_unavailable if stigmem recall backend is unreachable (retryable)
```

#### 21.8.5 Submit Discovery Audit (SHOULD)

```
POST /v1/instruction/audit
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "audit_token":   "audi_01J...",
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": []
}

→ 204 on success (idempotent)
→ 400 audit_token_invalid  if token not recognized or already fully closed
→ 400 audit_token_expired  if token is older than 24 hours
```

#### 21.8.6 Get Manifest Coverage Report (SHOULD)

```
GET /v1/agents/{agent_id}/instruction-manifest/coverage
Authorization: Bearer <agent api-key or admin api-key>

Agent-key response:
→ 200 {
    "manifest_version": "v4",
    "embedding_model_version": "nomic-embed-text-v1.5",
    "evaluated_at": "2026-05-04T06:00:00Z",
    "units": [
      {
        "name":             "security-posture",
        "coverage_pct":     0.95,
        "hit_at_10":        0.92,
        "probe_count":      20,
        "last_evaluated_at": "2026-05-04T06:00:00Z"
      }
    ]
  }

Admin-key response: same as above, plus "coverage_status" field per unit.

→ 403 instruction_scope_denied  if agent API key's scope does not match {agent_id}
→ 403 if peer agent's API key is used to query another agent's coverage
→ 404 if no manifest or no coverage report generated yet
```

**Scope validation (S9):** The `agent_id` path parameter MUST be validated against the caller's API key scope. An agent API key MUST only grant access to the coverage report for the agent whose scope matches the token. A peer agent's API key querying a different agent's coverage report MUST return `403 instruction_scope_denied`. Only an admin API key may access any agent's coverage report.

**Categorical label restriction (S11):** The `coverage_status` categorical label (`"ok"`, `"coverage_critical"`, `"not_evaluated"`) SHOULD be returned only in admin-key responses. Agent-key responses SHOULD return only raw `coverage_pct` and `hit_at_10` values, omitting the categorical label. This limits the retrieval-quality oracle surface for non-admin callers.

`coverage_status` values (admin-only): `"ok"` (hit@10 ≥ 0.4), `"coverage_critical"` (hit@10 < 0.4, soft-lift eligible in Phase 11), `"not_evaluated"` (probe run not yet completed). This endpoint is the primary operator signal for diagnosing instruction units before they produce production misses.

---

### 21.9 Error Reference

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `intent_required` | `intent` field absent or empty in `recall_instruction` request |
| 400 | `manifest_too_large` | Manifest exceeds 1000-token budget |
| 400 | `manifest_entry_invalid` | Entry has neither `fact_uri` nor `path`, or has both |
| 400 | `manifest_coverage_failure` | One or more units failed the paraphrase coverage gate at publish time (§21.8.3); response body identifies failing units and their `coverage_pct` |
| 400 | `task_type_unknown` | A `required_by_task_types` value is not a registered wake-reason string in this deployment |
| 400 | `guarantee_cap_exceeded` | More than 5 manifest entries have `guarantee_load: true`; deployment cap exceeded |
| 400 | `task_types_approval_required` | A manifest entry declares > 2 `required_by_task_types` values and no admin approval is recorded |
| 400 | `audit_token_invalid` | `audit_token` not recognized or already fully closed |
| 400 | `audit_token_expired` | `audit_token` is older than 24 hours |
| 403 | `instruction_scope_denied` | Caller's token scope does not match the requested agent's instruction garden |
| 404 | `manifest_not_found` | No instruction manifest configured for the agent |
| 404 | `boot_stub_not_found` | No boot stub generated for the agent yet |
| 409 | `manifest_version_conflict` | Version string already exists; manifest versions are immutable |
| 503 | `recall_backend_unavailable` | Stigmem recall backend unreachable; retryable |

---

## 22. Security Hardening

**Status:** DRAFT normative (Phase 12). §22.1–§22.7 carry MUST/SHOULD/MAY normative language.

### 22.1 mTLS Federation Transport

#### 22.1.1 Scope

This section specifies mutual TLS requirements for all transport connections between federated Stigmem nodes. The spec otherwise treats the federation wire protocol as transport-agnostic (§6); §22.1 narrows that flexibility for deployments connecting more than one node.

#### 22.1.2 Normative Requirements

1. All federation transport connections between distinct Stigmem nodes MUST use mutual TLS (mTLS): both the dialing node and the accepting node MUST present a valid X.509 certificate and MUST verify the peer's certificate before data exchange begins.
2. The TLS version floor is **TLS 1.3**. Nodes MUST NOT negotiate TLS 1.2 or earlier on federation ports. Implementations MUST configure their TLS stack to refuse downgrade to TLS < 1.3.
3. The cipher suite floor for TLS 1.3 connections MUST include at a minimum:
   - `TLS_AES_128_GCM_SHA256`
   - `TLS_AES_256_GCM_SHA384`
   - `TLS_CHACHA20_POLY1305_SHA256`

   Operators MAY restrict to a subset of the above for compliance purposes, but MUST NOT add cipher suites outside this list without board-level security approval documented in their node's ops runbook.
4. Node certificate Subject Alternative Names (SANs) MUST include the node's canonical `entity_uri` (as a URI SAN). Verifying nodes MUST check that the peer's SAN matches the `entity_uri` declared in the peer's org manifest (§19.1.2) before accepting the connection as authenticated.
5. Nodes MUST reject any federation connection from a peer whose certificate chain cannot be verified against a locally configured trust root or whose SAN does not match the expected `entity_uri`.

#### 22.1.3 Cert Rotation Hook into §19 Manifest

When a node rotates its mTLS node certificate:

1. The node MUST generate a new X.509 certificate for the new key pair.
2. The new certificate's public key fingerprint MUST be recorded in the node's org manifest (§19.1) as a new `RotationEvent` (§19.1.4) alongside the Ed25519 key rotation, or in a dedicated `tls_cert_fingerprint` field on the manifest if the TLS key is distinct from the Ed25519 signing key. Implementations MUST NOT rotate the mTLS certificate silently — every rotation MUST produce a manifest update.
3. The updated manifest MUST be re-signed and re-published to `/.well-known/stigmem-manifest.json` (§19.1.6) before the new certificate is put into service.
4. The updated manifest MUST be submitted to the transparency log (§19.2) as part of the rotation event. Nodes MUST NOT activate the new certificate until the transparency log submission has been acknowledged (i.e., until a `LogEntry` is received). Nodes SHOULD retry the transparency log submission for up to 24 hours before proceeding with rotation. If rotation proceeds without a log acknowledgement (e.g., due to a Rekor maintenance window), the node MUST record a `pending_log_submission: true` flag in the manifest and MUST complete the submission as soon as the log is reachable.
5. During the transition window (see §22.2.2 for dual-trust period), nodes MUST accept both the old and new TLS certificates from the rotating peer. The transition window MUST NOT exceed the dual-trust period defined in §22.2.

#### 22.1.4 Client Certificate Provisioning

Nodes SHOULD use short-lived mTLS client certificates (≤ 24 hours) issued by a local certificate authority dedicated to federation transport. Operators MAY use longer-lived certificates (≤ 90 days) provided they implement automated rotation (e.g., via cert-manager or equivalent). Long-lived certificates MUST be listed in the node's org manifest as described in §22.1.3.

---

### 22.2 Key Rotation

#### 22.2.1 Scope

This section applies to two key types:
- **Ed25519 node signing keys** — used to sign org manifests and capability tokens (§19.1, §19.3).
- **Capability issuer keys** — the subset of node signing keys used as issuers in live capability tokens.

#### 22.2.2 Rollover Window and Dual-Trust Period

1. The **rollover window** begins when a new key pair is generated and ends when all previously issued capability tokens signed by the old key have expired or been explicitly revoked.
2. During the rollover window, nodes MUST maintain a **dual-trust period**: both the old and new public keys are simultaneously trusted for signature verification. The dual-trust period MUST cover at least the maximum outstanding capability token lifetime from the time rotation is initiated. Since capability tokens MUST NOT exceed 90 days (§19.3.2), the dual-trust period MUST be at least 90 days unless all outstanding tokens are explicitly revoked before rotation completes.
3. Nodes MUST reject tokens signed by a key older than the dual-trust period (i.e., keys for which the dual-trust period has elapsed and which are no longer in the org manifest's rotation chain).
4. The rollover window MUST be recorded in the org manifest via a `RotationEvent` (§19.1.4). The transparency log MUST receive a separate log entry for the rotation event with `event_type: "key_rotation"` and a `dual_trust_expires_at` field indicating when the old key's trust period ends.
5. During the dual-trust period, verifiers SHOULD consult the org manifest rotation chain (§19.1.4) to identify which historic key signed a given token, rather than assuming the current manifest key.

#### 22.2.3 Transparency Log Entry on Rotation

Every key rotation MUST produce a transparency log entry. The log entry payload:

```
KeyRotationLogEntry:
  event_type:           "key_rotation"
  entity_uri:           URI         // the rotating node/org
  old_key_id:           hex         // key_id of the retiring key
  new_key_id:           hex         // key_id of the new key
  rotated_at:           RFC3339
  dual_trust_expires_at: RFC3339    // old key trusted until this time
  manifest_log_index:   integer     // log index of the updated manifest submission
  rotation_sig:         base64url   // Ed25519 sig over RFC 8785 JCS encoding of other fields, signed by OLD key
```

The `rotation_sig` MUST verify under the `old_key_id` public key. This anchors the log entry to the prior identity. The byte sequence signed MUST be the RFC 8785 JSON Canonicalization Scheme (JCS) serialisation of the other fields: keys lexicographically sorted, no whitespace, UTF-8 encoding, no trailing newline.

The manifest submission (§22.1.3.4) MUST be acknowledged by the transparency log before the `KeyRotationLogEntry` is submitted; the returned log index MUST be recorded as `manifest_log_index`.

#### 22.2.4 Rotation Cadence

Nodes SHOULD rotate Ed25519 node signing keys on a cadence no longer than **365 days**. For capability issuer keys specifically, the SHOULD cadence is **90 days** (matching the maximum token lifetime). Operators MAY define shorter cadences. Cadence MUST be documented in the node's operational runbook and MAY be declared in the node's `/.well-known/stigmem` advertisement.

---

### 22.3 Audit Log Surface

#### 22.3.1 Required Event Types

Every Stigmem node MUST emit structured audit log events for the following operations. Each event MUST be written to the audit log before the operation's response is returned to the caller (write-ahead semantics).

| Event type | Trigger | Minimum fields |
|---|---|---|
| `fact_write` | Any fact assertion (assert, retract) | `event_type`, `timestamp`, `hlc`, `actor_entity`, `fact_id`, `scope`, `verb` (`assert`\|`retract`) |
| `fact_read` | Any recall or query returning ≥ 1 fact | `event_type`, `timestamp`, `actor_entity`, `scope_filter`, `fact_ids_returned[]`, `query_strategy` |
| `capability_token_issue` | Token issued | `event_type`, `timestamp`, `token_id`, `issuer`, `subject`, `verb`, `object`, `expiry` |
| `capability_token_revoke` | Token revoked | `event_type`, `timestamp`, `token_id`, `issuer`, `revoked_at`, `reason` |
| `manifest_publish` | Org manifest published or updated | `event_type`, `timestamp`, `entity_uri`, `key_id`, `manifest_hash` |
| `key_rotation` | Ed25519 or mTLS key rotated | `event_type`, `timestamp`, `entity_uri`, `old_key_id`, `new_key_id`, `dual_trust_expires_at` |
| `federation_connect` | Peer connection accepted or rejected | `event_type`, `timestamp`, `peer_entity_uri`, `peer_cert_fingerprint`, `outcome` (`accepted`\|`rejected`), `reject_reason?` |
| `quarantine_admit` | Fact admitted to quarantine garden | `event_type`, `timestamp`, `fact_id`, `source`, `admit_reason` |
| `quarantine_release` | Fact released from quarantine | `event_type`, `timestamp`, `fact_id`, `actor_entity`, `decision` (`accept`\|`reject`) |
| `quota_breach` | Per-principal quota ceiling hit | `event_type`, `timestamp`, `principal`, `quota_dimension`, `ceiling`, `actual` |
| `admin_action` | Any admin API call | `event_type`, `timestamp`, `actor_entity`, `action`, `resource`, `outcome` |
| `replay_rejected` | Capability token rejected due to replay | `event_type`, `timestamp`, `token_id`, `nonce`, `reject_reason` |
| `instruction_audit` | Lazy instruction preload or recall (MUST emit if the instruction recall layer is active; nodes not implementing the lazy instruction layer are exempt) | `event_type`, `timestamp`, `agent_id`, `chunk_id`, `load_trigger`, `outcome` |

Implementations MUST NOT omit required fields. Optional fields (marked `?`) SHOULD be included when available.

#### 22.3.2 Ordering Guarantee

Audit log events MUST be totally ordered by a monotonically increasing sequence number within a single node. Events SHOULD include the node's HLC tick (§2.4) alongside the wall-clock timestamp to allow cross-node ordering reconstruction. The sequence MUST NOT reset across node restarts.

#### 22.3.3 Retention Contract

- Audit logs MUST be retained for a minimum of **90 days**.
- Operators SHOULD retain logs for **1 year** for forensic purposes.
- Logs MUST be stored in a medium that is append-only with respect to normal operational access (i.e., ordinary application processes MUST NOT be able to overwrite or delete log entries).
- Logs MUST NOT be stored exclusively in the same database that serves the production fact store unless that database provides an independent, append-only audit trail mechanism (e.g., PostgreSQL audit extension with restricted DDL access).

#### 22.3.4 Admin Export Shape

Admins MUST be able to export audit logs via the following HTTP route:

```
GET /v1/admin/audit-log
Authorization: Bearer <admin-token>
Query parameters:
  after:      RFC3339   // events after this timestamp (exclusive); omit for all
  before:     RFC3339   // events before this timestamp (exclusive); omit for open end
  event_type: string    // filter to one event type; repeatable for multiple types
  limit:      integer   // max events per page; default 500; max 5000
  cursor:     string    // opaque pagination cursor from prior response
```

Response:

```json
{
  "events": [
    {
      "seq":        12345,
      "event_type": "fact_write",
      "timestamp":  "2026-05-04T12:00:00Z",
      "hlc":        "1746360000000-0001-a1b2",
      ...
    }
  ],
  "next_cursor": "opaque-cursor-string",
  "has_more":   true
}
```

- The export route MUST require an admin-scoped token.
- Events MUST be returned in ascending `seq` order.
- The route MUST support streaming for large time ranges (chunked transfer encoding or cursor pagination with `has_more`).
- Operators SHOULD provide a CLI wrapper for this endpoint that writes NDJSON to stdout.

---

### 22.4 Per-Principal Quotas

#### 22.4.1 Model

Stigmem implements per-principal rate limiting using a **token-bucket** model. Each `(principal, dimension)` pair maintains an independent token bucket. The principal is the `actor_entity` URI derived from the authenticated caller's capability token or API key.

```
TokenBucket:
  principal:   URI      // entity URI of the caller
  dimension:   string   // quota dimension (see §22.4.2)
  capacity:    integer  // bucket size (max burst)
  rate:        float    // refill rate in tokens/second
  current:     float    // current token count (updated on each request)
  last_refill: RFC3339  // timestamp of last refill computation
```

The bucket refills continuously at `rate` tokens/second up to `capacity`. Each qualifying request consumes 1 token unless otherwise specified per dimension.

#### 22.4.2 Quota Dimensions and Default Ceilings

| Dimension | Unit | Default capacity | Default rate | Description |
|---|---|---|---|---|
| `fact_write` | facts/sec | 100 | 10 | Fact assertions and retractions |
| `fact_read` | queries/sec | 500 | 50 | Recall and query operations |
| `token_issue` | tokens/min | 20 | 0.33 | Capability token issuance |
| `federation_pull` | requests/min | 30 | 0.5 | Outbound federation pull calls |
| `admin_action` | actions/min | 10 | 0.17 | Admin API calls |
| `subscription_event` | deliveries/sec | 200 | 20 | Outbound subscription event deliveries |
| `audit_export` | rows/min | 10000 | 167 | Rows returned from audit export endpoint |

Default ceilings MUST be applied unless overridden by an admin-configured `QuotaPolicy` document for the principal. Overrides MUST be stored persistently and survive node restarts.

#### 22.4.3 Backpressure Response Shape

When a principal's token bucket is exhausted:

1. The node MUST return **HTTP 429 Too Many Requests** with a JSON body:

```json
{
  "error":        "quota_exceeded",
  "dimension":    "fact_write",
  "principal":    "stigmem://org/my-agent",
  "retry_after":  3.2
}
```

- `retry_after` is a float number of seconds until the bucket refills sufficiently to accept one more request at the current rate. Implementations MUST compute this as `(1 - current) / rate` (seconds to earn 1 token).

2. The node MUST include a `Retry-After` HTTP header with the integer ceiling of `retry_after`.
3. The node MUST emit a `quota_breach` audit log event (§22.3.1) for every request that hits the ceiling.
4. Nodes SHOULD propagate quota pressure upstream to federated callers via the `X-Stigmem-Replication-Lag` header (§6.7) when `federation_pull` quota is exhausted.
5. Callers MUST honour `Retry-After` and MUST implement exponential backoff with jitter after two consecutive 429 responses from the same node.

---

### 22.5 Replay Protection

#### 22.5.1 Scope

This section extends §19.3.5 (capability token nonce) with normative clock-skew bounds and a unified replay protection model applicable to both capability tokens and federation handshake messages.

#### 22.5.2 Nonce and Timestamp Window

1. Every capability token MUST include a `nonce` of 32 cryptographically random bytes (§19.3.5). Every federation handshake message MUST include an independent `nonce` of 32 cryptographically random bytes.
2. The **timestamp acceptance window** is ± **5 minutes** from the verifier's local clock. Tokens or messages with an `issued_at` timestamp outside this window MUST be rejected with a `timestamp_out_of_window` error, even if the nonce is fresh.
3. The **nonce cache** MUST retain seen nonces for at least the **duration of the acceptance window plus the maximum token lifetime** (5 minutes + 90 days for capability tokens; 5 minutes + session duration for handshake messages). Implementations MUST NOT prune nonces from the cache before this window elapses.
4. Nonces MUST be stored in a persistent cache (survives node restarts within the retention window). An in-memory-only nonce cache MUST NOT be used in production; a brief restart MUST NOT create a replay window.

#### 22.5.3 Clock-Skew Bounds

| Scenario | Bound | Behaviour on violation |
|---|---|---|
| `issued_at` > verifier clock + 5 min | Future-dated | Reject: `timestamp_future_dated` |
| `issued_at` < verifier clock − 5 min | Stale | Reject: `timestamp_stale` |
| `expiry` < verifier clock | Expired | Reject: `token_expired` |
| `expiry` > `issued_at` + 90 days | Excessive lifetime | Reject: `token_lifetime_exceeded` |

Nodes MUST synchronise their system clocks via NTP (or equivalent). Operators SHOULD configure alerts if clock drift exceeds 30 seconds.

#### 22.5.4 Error Codes

| HTTP | Error code | Condition |
|---|---|---|
| 401 | `timestamp_future_dated` | `issued_at` more than 5 minutes in the future |
| 401 | `timestamp_stale` | `issued_at` more than 5 minutes in the past |
| 401 | `token_expired` | Token `expiry` has passed |
| 401 | `token_lifetime_exceeded` | Token `expiry` − `issued_at` > 90 days |
| 401 | `token_replay` | Nonce already seen within the retention window |

---

### 22.6 Container Baseline

#### 22.6.1 Scope

This section specifies the normative security posture for reference operator container images published by Eidetic-Labs. Third-party operators running Stigmem from source SHOULD adopt the same baseline.

#### 22.6.2 Distroless Image

1. Reference operator images MUST be built FROM a [distroless base](https://github.com/GoogleContainerTools/distroless) (e.g., `gcr.io/distroless/cc-debian12` or equivalent). Images MUST NOT include a shell (`sh`, `bash`) in the production layer.
2. Multi-stage builds MUST be used: build dependencies and tools MUST be confined to a builder stage and MUST NOT appear in the final image layer.
3. The image MUST contain only the Stigmem node binary and its minimal runtime dependencies (shared libraries, CA bundle, tzdata).

#### 22.6.3 Non-Root User

1. The container MUST run as a non-root user. The `Dockerfile` MUST include a `USER` directive setting a non-zero UID (SHOULD use UID 1000) in the final stage.
2. The container MUST NOT be run with `--privileged` or with `CAP_SYS_ADMIN`. Operators MUST NOT grant any Linux capabilities beyond the minimum required for the Stigmem node to bind its listen port (if < 1024, use `CAP_NET_BIND_SERVICE`; SHOULD use a port ≥ 1024 to avoid requiring any capability grant).
3. Kubernetes / container runtime manifests for reference deployments MUST include:
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     allowPrivilegeEscalation: false
   ```

#### 22.6.4 Read-Only Root Filesystem

1. The container's root filesystem MUST be mounted read-only (`readOnlyRootFilesystem: true` in Kubernetes). All writable state (database files, log buffers, temporary files) MUST be mounted as explicit volumes or `emptyDir` mounts.
2. Reference Helm charts MUST configure `readOnlyRootFilesystem: true` by default and MUST document which volumes require write access.

#### 22.6.5 Seccomp Profile

1. Reference images MUST ship a [seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html) profile that allows only the syscalls required by the Stigmem node binary. The profile MUST deny `ptrace`, `process_vm_readv`, `process_vm_writev`, `kexec_load`, and `perf_event_open` at a minimum.
2. Kubernetes deployments MUST apply the profile via:
   ```yaml
   securityContext:
     seccompProfile:
       type: Localhost
       localhostProfile: profiles/stigmem-node.json
   ```
   or `type: RuntimeDefault` where a restrictive runtime default is confirmed equivalent. `Unconfined` MUST NOT be used in production.
3. The seccomp profile MUST be published alongside each release in `deploy/seccomp/stigmem-node.json` and versioned with the binary.

#### 22.6.6 Image Signing

Reference images MUST be signed using [Sigstore Cosign](https://github.com/sigstore/cosign) and the signature MUST be pushed to the same registry. Operators SHOULD verify the image signature before deployment using `cosign verify`. Image digests (not mutable tags) MUST be used in all reference Kubernetes manifests and Helm chart `values.yaml` defaults.

---

### 22.7 Transparency Log Own-Instance Decision Memo

#### 22.7.1 Purpose

§19.2.2 permits but does not require operating a self-hosted Rekor instance. This section provides normative decision criteria so that operators can determine whether self-hosting is appropriate, and records the Eidetic-Labs reference deployment position.

#### 22.7.2 Decision Criteria

An operator SHOULD self-host a Rekor instance if and only if ALL of the following criteria are met:

| Criterion | Rationale |
|---|---|
| The deployment operates in a private network without external internet egress | Public Rekor requires egress to `rekor.sigstore.dev` |
| Federation peers are all internal (no public or third-party peers) | Public log provides independent verifiability for external peers; private log acceptable for closed meshes |
| The operator can commit to operating the log with ≥ 99.9% uptime | Federation peers depend on the log for manifest verification in `trust_mode: strict` |
| The operator can provide independent accessibility of the log to all federation peers | §19.2.2 SHOULD: log SHOULD be independently accessible to all peers |
| A dedicated ops team or automation pipeline manages log key ceremonies | Rekor key rotation is operationally complex and MUST NOT be performed ad-hoc |

If any criterion is not met, the operator SHOULD use the public Rekor instance at `https://rekor.sigstore.dev` (or a hosted equivalent). Operators MUST NOT self-host without documented answers to each criterion in their ops runbook.

#### 22.7.3 Reference Deployment Position (Eidetic-Labs)

The Eidetic-Labs reference deployment uses the **public Rekor instance** (`https://rekor.sigstore.dev`). Criteria evaluation:

| Criterion | Status |
|---|---|
| Private network without egress | Not met — reference node targets public deployments |
| Internal-only federation | Not met — external federation is a core use-case |
| Ops commitment ≥ 99.9% uptime | Not evaluated — would require dedicated SRE investment |
| Independent peer accessibility | Not evaluated — moot given above |
| Dedicated key ceremony team | Not evaluated — moot given above |

**Decision: defer self-hosted Rekor to backlog.** A self-hosted Rekor instance for the Eidetic-Labs reference deployment does not meet the minimum decision criteria at this phase. A backlog issue SHOULD be filed when the following change conditions are met: (a) a private-network deployment tier is productised, or (b) a dedicated SRE function is established. Implementation of a self-hosted instance is explicitly out of scope for Phase 12.

#### 22.7.4 Configuration

When using the public Rekor instance (default):

```
STIGMEM_TRANSPARENCY_LOG_URL=https://rekor.sigstore.dev
STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY=<base64-encoded ECDSA key from GET /api/v1/log>
```

When using a self-hosted instance, replace the above with the self-hosted instance URL and its corresponding public key. The `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST be pinned explicitly; key discovery via the URL alone MUST NOT be the sole trust anchor in production.

#### 22.7.5 Transparency Log Public-Key Rotation

The Sigstore/Rekor root signing key is subject to rotation (a root key rotation occurred in 2022). Operators pinning `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST have a documented procedure for updating the pin.

1. Operators SHOULD subscribe to Sigstore transparency log key rotation announcements (the [sigstore-announce mailing list](https://groups.google.com/g/sigstore-announce) and the CT log transparency dashboard) and SHOULD update `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` within **30 days** of a published rotation.
2. A node MUST NOT treat a persistent transparency log key verification failure as a permanent misconfiguration without first checking whether a Rekor root key rotation has occurred. On repeated verification failures, the node SHOULD emit a `transparency_log_key_mismatch` audit log event and surface an operator alert before entering a degraded-verification state.

---

## Appendix A. Security Policy

*Content unchanged from v1.0 §19 (non-normative).*

The active security policy — supported versions, vulnerability reporting instructions, scope definitions, and the coordinated disclosure timeline — is maintained in [`SECURITY.md`](../SECURITY.md) at the root of the repository.

**Reporting:** Do not open a public GitHub issue for security vulnerabilities. Report via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories). We acknowledge within 48 hours and target a patch within 14 days for critical vulnerabilities.

**Disclosure timeline:** 90 days from the report date before public disclosure, except for vulnerabilities already being actively exploited in the wild.

For the current security posture and Dependabot alert triage covering v1.0-rc, see the [Security Posture section of SECURITY.md](../SECURITY.md#security-posture--v10-rc-2026-05-03).

---
