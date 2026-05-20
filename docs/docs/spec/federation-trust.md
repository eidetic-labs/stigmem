---
title: Federation Trust Components
sidebar_label: Federation Trust
audience: Spec
description: "Rendered entry point for federation trust component specs: manifests, capability tokens, federation trust, and quarantine."
---

# Federation Trust Components \{#section-19\}

<p className="stigmem-meta"><span>12 min read</span><span>Spec contributor · Node operator</span><span>Spec-04 + Spec-05 + Spec-06 + Spec-08</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for the four federation trust
component specs:
[Spec-04-Manifests](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/04-manifests.md),
[Spec-05-Federation-Trust](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/05-federation-trust.md),
[Spec-06-Capability-Tokens](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/06-capability-tokens.md),
and
[Spec-08-Quarantine-Garden](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/08-quarantine-garden.md).
Org manifests, capability tokens, source-trust score, quarantine
garden, recall-time sanitizer.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source.
:::

*This section is non-normative.*

The active security policy — supported versions, vulnerability
reporting instructions, scope definitions, and the coordinated
disclosure timeline — is maintained in
[`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md)
at the root of the repository.

<div className="stigmem-keypoint">

**Reporting.**

Do not open a public GitHub issue for security vulnerabilities.
Report via the
[GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories).
We acknowledge within 48 hours and target a patch within 14 days
for critical vulnerabilities.

</div>

**Disclosure timeline:** 90 days from the report date before public
disclosure, except for vulnerabilities already being actively
exploited in the wild.

For the current security posture and Dependabot alert triage
covering the pre-reset v1.0-rc snapshot, see the
[Security Posture section of SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md#security-posture--v10-rc-2026-05-03).

*v1.0 — Stable. All sections normative. Apache-2.0.*

### §19.1 Org manifest \{#section-19-1\}

#### §19.1.1 Purpose \{#section-19-1-1\}

An **org manifest** is a signed document that declares the canonical
public key for a Stigmem node or organisation and the set of entity
URIs that the manifest is authoritative for. Peers MUST use the
manifest public key to verify capability tokens (§19.3), provenance
signatures (§19.6), and recall-time sanitizer trust decisions
(§19.7).

#### §19.1.2 Manifest fields \{#section-19-1-2\}

The `OrgManifest` struct carries everything a verifier needs to
validate tokens and provenance from a given node.

```
OrgManifest:
  manifest_version:  integer          // MUST be 1 for this spec version
  entity_uri:        URI              // root entity URI; MUST be a stigmem:// URI
  public_key:        base64url        // Ed25519 public key (32 bytes, encoded)
  key_id:            hex              // SHA-256 of the 32-byte raw Ed25519 public key
  entities:          [URI]            // entity URIs this manifest is authoritative for; MUST include entity_uri
  rotation_events:   [RotationEvent]  // ordered history of key rotations (§19.1.4); empty on first publish
  issued_at:         RFC3339          // issuance timestamp
  expires_at:        RFC3339          // expiry; MUST be at least 24h after issued_at
  signature:         base64url        // Ed25519 sig over the canonical JSON encoding of all other fields
```

<div className="stigmem-keypoint">

**A manifest MUST be self-consistent.**

The <code>signature</code> MUST verify under the
<code>public_key</code> declared in the same manifest. The
<code>expires_at</code> ceiling forces regular re-publication,
limiting the window during which a compromised key remains trusted.

</div>

#### §19.1.3 Canonical encoding \{#section-19-1-3\}

Manifest signing and verification MUST use RFC 8785 (JSON
Canonicalization Scheme, JCS) for deterministic byte ordering.
Implementations MUST serialize the manifest body (all fields except
`signature`) using JCS before signing. Implementations MUST reject
manifests where JCS canonicalization of the non-`signature` fields
does not reproduce the same bytes that were signed.

#### §19.1.4 Key rotation \{#section-19-1-4\}

Key rotation events allow a node to cycle its signing key while
preserving a verifiable chain of custody back to its original
published key.

```
RotationEvent:
  rotated_at:    RFC3339   // timestamp of rotation
  old_key_id:    hex       // key_id of the previous key
  new_key_id:    hex       // key_id of the new key (= current manifest's key_id)
  rotation_sig:  base64url // Ed25519 sig over canonical JSON of { entity_uri, old_key_id, new_key_id, rotated_at }
                           // signed by the OLD private key; entity_uri binds the event to its manifest
```

The `rotation_sig` MUST verify under the public key identified by
`old_key_id`. This creates an unbroken chain: the previous key
vouches for the new key.

**Rotation chain invariants:**

<ol className="stigmem-steps">
<li><code>rotation_events</code> MUST be ordered chronologically ascending.</li>
<li>Each event's <code>old_key_id</code> MUST equal the <code>key_id</code> of the preceding entry (or the original manifest's <code>key_id</code> for the first rotation).</li>
<li>A valid rotation chain MUST terminate with the <code>new_key_id</code> matching the current manifest's <code>key_id</code>.</li>
<li>The <code>rotation_events</code> count in a newly published manifest MUST be ≥ the count in the most recently submitted manifest for the same <code>entity_uri</code>. Peers MUST reject any manifest where the rotation event count regresses.</li>
</ol>

#### §19.1.5 Entity URI list \{#section-19-1-5\}

The `entities` array declares which entity URIs this manifest speaks
for. An entity URI MUST appear in at most one valid (non-expired)
manifest per transparency log epoch. Nodes MUST reject capability
tokens and provenance signatures claiming to be from an entity URI
that does not appear in the signer's manifest.

#### §19.1.6 Manifest publication \{#section-19-1-6\}

Nodes MUST publish their manifest at
`/.well-known/stigmem-manifest.json`. Nodes SHOULD also submit each
new or rotated manifest to the transparency log (§19.2) for
independent auditability. A manifest MUST be re-submitted on key
rotation.

### §19.2 Transparency log integration \{#section-19-2\}

#### §19.2.1 Purpose \{#section-19-2-1\}

A transparency log provides tamper-evident, append-only evidence
that a manifest was published at a given time and has not been
backdated or silently revoked. It is the audit anchor for the
federation trust model.

#### §19.2.2 Recommended integration \{#section-19-2-2\}

Implementations SHOULD integrate with
[Rekor](https://docs.sigstore.dev/rekor/overview/) (Sigstore's
transparency log) or an equivalent OSS log offering:

<div className="stigmem-grid">

<div><h4>Append-only, tamper-evident</h4><p>Backed by a Merkle tree.</p></div>
<div><h4>Public inclusion proofs</h4><p>Using signed tree heads (STH).</p></div>
<div><h4>HTTP API</h4><p>For entry submission and proof retrieval.</p></div>

</div>

Implementations MAY operate a self-hosted Rekor instance. A
self-hosted log is acceptable for private deployments but SHOULD be
independently accessible to all federation peers.

#### §19.2.3 What we depend on vs. require \{#section-19-2-3\}

<div className="stigmem-fields">

<div>
<dt>Capability</dt>
<dt><span className="stigmem-fields__type">Requirement</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Inclusion proof for submitted manifests</dt>
<dt><span className="stigmem-fields__type">MUST</span></dt>
<dd>Be supported by the chosen log.</dd>
</div>

<div>
<dt>Consistency proof between log checkpoints</dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Be supported.</dd>
</div>

<div>
<dt>Log entry search by key fingerprint</dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Be supported.</dd>
</div>

<div>
<dt>Public verifiability (no auth)</dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Hold for public federation deployments.</dd>
</div>

<div>
<dt>Specific log implementation (Rekor)</dt>
<dt><span className="stigmem-fields__type">MAY</span></dt>
<dd>Alternative logs acceptable if they satisfy the above.</dd>
</div>

</div>

Nodes MUST NOT trust a peer's manifest without a valid inclusion
proof when operating in `trust_mode: strict` (see §19.4.3). Nodes
operating in `trust_mode: relaxed` MAY accept peer manifests without
log verification, but SHOULD log a warning.

#### §19.2.4 Inclusion proof format \{#section-19-2-4\}

When submitting a manifest to the log, the node receives a
`LogEntry`:

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

Nodes SHOULD store the `LogEntry` alongside the manifest and serve
it at `/.well-known/stigmem-manifest-proof.json`. Peers MUST be able
to verify the inclusion proof independently using only the log's
public key and the proof data.

#### §19.2.5 Revocation events \{#section-19-2-5\}

Capability token revocations (§19.3.4) MUST be submitted to the
transparency log as a distinct log entry type. This makes
revocations independently auditable: a peer can verify a token is
revoked by checking the log without trusting the issuing node's
runtime state.

#### §19.2.6 Checkpoint verification \{#section-19-2-6\}

The `checkpoint` field in `LogEntry.inclusion_proof` is a signed
note in the
[transparency-dev/formats](https://github.com/transparency-dev/formats)
checkpoint format.

<ol className="stigmem-steps">
<li><strong>Key discovery.</strong> Obtain the log's public key from the log's key discovery endpoint. For Rekor-compatible logs, issue <code>GET /api/v1/log</code> against the log instance; the response includes the ECDSA public key (PEM-encoded in the <code>publicKey.content</code> field, base64-encoded).</li>
<li><strong>Verification.</strong> For Rekor-compatible logs, implementations MUST verify the checkpoint using the log's published public key. A checkpoint that fails signature verification MUST cause the enclosing inclusion proof to be rejected.</li>
<li><strong>Failure-closed behavior.</strong> If the transparency log is unreachable when an inclusion proof is required (i.e., the node operates in <code>trust_mode: strict</code>), the manifest MUST be rejected. Implementations MUST NOT fall back to accepting an unverified manifest.</li>
<li><strong>Reference implementation.</strong> The <code>sigstore-python</code> library (<code>sigstore.verify</code>) is the reference for checkpoint and inclusion-proof verification.</li>
<li><strong>Error codes.</strong> See §19.9 for <code>inclusion_proof_invalid</code> (HTTP 400) and <code>transparency_log_unavailable</code> (HTTP 503).</li>
</ol>

### §19.3 Capability tokens \{#section-19-3\}

#### §19.3.1 Purpose \{#section-19-3-1\}

A capability token is a signed, short-lived credential that grants
a specific named permission to a specific subject from a specific
issuer. Tokens replace ad-hoc per-peer trust agreements with a
verifiable, revocable, auditable delegation primitive.

#### §19.3.2 Token shape \{#section-19-3-2\}

```
CapabilityToken:
  token_version: integer    // MUST be 1 for this spec version
  token_id:      UUID       // unique identifier; used for revocation lookup
  issuer:        URI        // entity URI of the issuing node/org (MUST be in issuer's manifest)
  subject:       URI        // entity URI of the token bearer
  verb:          string     // one of: "read" | "write" | "admin" | "federate" | "subscribe" | "tombstone:read"
  object:        URI        // resource the verb applies to (scope URI, garden URI, or "*" for any)
  issued_at:     RFC3339
  expiry:        RFC3339    // MUST be set; MUST NOT exceed 90 days from issued_at
  nonce:         hex        // 32 bytes cryptographically random; prevents replay
  signature:     base64url  // Ed25519 sig over canonical JSON of all other fields, signed by issuer key
```

The `verb` values are:

<div className="stigmem-fields">

<div>
<dt>Verb</dt>
<dt><span className="stigmem-fields__type">Bearer may</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>read</code></dt>
<dt><span className="stigmem-fields__type">read facts from <code>object</code></span></dt>
<dd></dd>
</div>

<div>
<dt><code>write</code></dt>
<dt><span className="stigmem-fields__type">assert facts to <code>object</code></span></dt>
<dd></dd>
</div>

<div>
<dt><code>admin</code></dt>
<dt><span className="stigmem-fields__type">manage keys and settings on <code>object</code></span></dt>
<dd></dd>
</div>

<div>
<dt><code>federate</code></dt>
<dt><span className="stigmem-fields__type">replicate facts bidirectionally</span></dt>
<dd>Via the federation protocol (§6).</dd>
</div>

<div>
<dt><code>subscribe</code></dt>
<dt><span className="stigmem-fields__type">register a standing event subscription</span></dt>
<dd>On <code>object</code> (scope URI or entity URI).</dd>
</div>

<div>
<dt><code>tombstone:read</code></dt>
<dt><span className="stigmem-fields__type">poll the tombstone federation route</span></dt>
<dd>Compound verb namespaces may be introduced by extension sections. Token validation implementations MUST accept any verb that appears in this enumeration.</dd>
</div>

</div>

#### §19.3.3 Signing and verification \{#section-19-3-3\}

The issuer MUST sign the token using the private key corresponding
to the `public_key` in their current org manifest (§19.1).

Verifiers MUST:

<ol className="stigmem-steps">
<li>Resolve the issuer's org manifest.</li>
<li>Check <code>manifest.expires_at &gt; now</code>; if expired, attempt refresh from the issuer's <code>/.well-known/stigmem-manifest.json</code>; reject the token if the manifest is still expired after refresh.</li>
<li>Verify the manifest's self-signature.</li>
<li>Verify the token's <code>signature</code> under the manifest's <code>public_key</code>.</li>
<li>Check that <code>subject</code> appears in the issuer's <code>entities</code> list. External-entity subjects are not permitted; cross-org delegation requires the delegatee to obtain their own org manifest and capability tokens.</li>
<li>Check <code>expiry &gt; now</code>.</li>
<li>Check <code>expiry ≤ issued_at + 90 days</code>.</li>
<li>Check the token is not revoked (§19.3.4).</li>
</ol>

A token that fails any of these steps MUST be rejected.

#### §19.3.4 Revocation \{#section-19-3-4\}

Issuers MAY revoke a token before its expiry by submitting a
revocation event to the transparency log (§19.2.5) and calling the
local revocation API (§5.24).

```
RevocationEvent:
  event_type:    "token_revocation"
  token_id:      UUID       // the token being revoked
  issuer:        URI
  revoked_at:    RFC3339
  reason:        string     // human-readable; SHOULD be informative
  signature:     base64url  // Ed25519 sig over canonical JSON of other fields
```

Nodes that receive a token MUST check for a revocation event before
honoring it. Nodes SHOULD cache revocation events with a TTL of no
less than 60 seconds. A revoked token MUST be rejected even if it
has not yet expired.

<div className="stigmem-keypoint">

**Revocation transparency log entries are for auditability, not real-time validation.**

Implementations MUST NOT attempt an inline transparency log query
as part of per-request token validation; doing so would introduce a
synchronous dependency on an external service in the hot path.
Real-time revocation checks MUST use the local revocation cache
(populated by background sync) and the issuer's revocation API
(§5.24).

</div>

#### §19.3.5 Token nonce and replay prevention \{#section-19-3-5\}

The `nonce` field MUST be 32 bytes of cryptographically random data
(e.g., from `/dev/urandom`). Receivers MUST maintain a nonce cache
in `trust_mode: strict`; receivers SHOULD maintain a nonce cache in
`trust_mode: relaxed`. The nonce cache MUST be global (keyed on the
nonce value alone, not per-issuer or per-subject) and MUST cover the
token's full validity window (from `issued_at` to `expiry`). A
nonce that appears in the cache MUST cause the token to be rejected
with a `token_replay` error.

### §19.4 Source-trust score \{#section-19-4\}

#### §19.4.1 Purpose \{#section-19-4-1\}

The source-trust score `t` is a scalar in [0.0, 1.0] that expresses
how much confidence a node should place in facts asserted by a
given source URI. It modulates the effective confidence of recalled
facts: `effective_confidence = fact.confidence × t`.

#### §19.4.2 Derivation formula \{#section-19-4-2\}

```
t = clamp(
      w_i × identity_strength(source)
    + w_p × peer_history(source)
    + w_s × scope_authority(source, fact.scope)
    + w_a × attestation_mode_factor(node.attestation_mode),
    0.0, 1.0
  )
```

Default weights: `w_i = 0.35, w_p = 0.30, w_s = 0.25, w_a = 0.10`.
These MUST be documented in the node's `/.well-known/stigmem`
response as `trust_weights` if non-default values are used.

**Component definitions:**

`identity_strength(source)` — a float in [0.0, 1.0] measuring how
strongly the source is identified:

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Value</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Valid manifest + log proof</dt>
<dt><span className="stigmem-fields__type">1.0</span></dt>
<dd></dd>
</div>

<div>
<dt>Valid manifest, no log proof</dt>
<dt><span className="stigmem-fields__type">0.7</span></dt>
<dd></dd>
</div>

<div>
<dt>Valid capability token from trusted issuer</dt>
<dt><span className="stigmem-fields__type">0.5</span></dt>
<dd></dd>
</div>

<div>
<dt>Known <code>entity_uri</code> registered on local API key</dt>
<dt><span className="stigmem-fields__type">0.4</span></dt>
<dd></dd>
</div>

<div>
<dt>Unrecognized but syntactically valid</dt>
<dt><span className="stigmem-fields__type">0.1</span></dt>
<dd></dd>
</div>

<div>
<dt>Absent or syntactically invalid</dt>
<dt><span className="stigmem-fields__type">0.0</span></dt>
<dd></dd>
</div>

</div>

`peer_history(source)` — derived from the node's interaction history:

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Value</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>≥ 100 facts with 0 attestation failures in 30 days</dt>
<dt><span className="stigmem-fields__type">1.0</span></dt>
<dd></dd>
</div>

<div>
<dt>≥ 10 facts with &lt; 5% attestation failures</dt>
<dt><span className="stigmem-fields__type">0.7</span></dt>
<dd></dd>
</div>

<div>
<dt>New source (&lt; 10 facts or no history)</dt>
<dt><span className="stigmem-fields__type">0.5</span></dt>
<dd>Default when no peer history exists.</dd>
</div>

<div>
<dt>Recent attestation failure rate ≥ 5%</dt>
<dt><span className="stigmem-fields__type">0.3</span></dt>
<dd></dd>
</div>

<div>
<dt>Explicitly blocklisted by admin</dt>
<dt><span className="stigmem-fields__type">0.0</span></dt>
<dd></dd>
</div>

</div>

`scope_authority(source, scope)`:

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Value</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Valid capability token for this scope with <code>verb: write</code></dt>
<dt><span className="stigmem-fields__type">1.0</span></dt>
<dd></dd>
</div>

<div>
<dt>Admin API key holder for this node</dt>
<dt><span className="stigmem-fields__type">0.9</span></dt>
<dd></dd>
</div>

<div>
<dt>Source's entity_uri prefix matches the node's authority</dt>
<dt><span className="stigmem-fields__type">0.7</span></dt>
<dd></dd>
</div>

<div>
<dt>External entity with a <code>federate</code> token</dt>
<dt><span className="stigmem-fields__type">0.5</span></dt>
<dd></dd>
</div>

<div>
<dt>No explicit scope authority</dt>
<dt><span className="stigmem-fields__type">0.2</span></dt>
<dd></dd>
</div>

</div>

`attestation_mode_factor(mode)`:

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Value</span></dt>
<dd></dd>
</div>

<div>
<dt><code>enforce</code></dt>
<dt><span className="stigmem-fields__type">1.0</span></dt>
<dd></dd>
</div>

<div>
<dt><code>warn</code></dt>
<dt><span className="stigmem-fields__type">0.6</span></dt>
<dd></dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">0.2</span></dt>
<dd></dd>
</div>

</div>

#### §19.4.3 Trust mode configuration \{#section-19-4-3\}

Configure via `STIGMEM_TRUST_MODE=strict|relaxed|off`.

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Posture</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>strict</code></dt>
<dt><span className="stigmem-fields__type">enforced</span></dt>
<dd>Nodes MUST verify log inclusion proofs for all peer manifests; <code>source_trust</code> is computed for all inbound facts; facts from sources with <code>t &lt; 0.2</code> are quarantined (§19.5).</dd>
</div>

<div>
<dt><code>relaxed</code> (default)</dt>
<dt><span className="stigmem-fields__type">observed</span></dt>
<dd>Nodes SHOULD compute <code>source_trust</code> but MUST NOT quarantine facts based solely on a low score; attestation failures are logged.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">disabled</span></dt>
<dd><code>source_trust</code> is not computed; <code>source_trust</code> field is <code>null</code> on all stored facts.</dd>
</div>

</div>

#### §19.4.4 Recall-time multiplier \{#section-19-4-4\}

At recall time, the `effective_confidence` of a fact is computed as:

```
effective_confidence = fact.confidence × t(fact.source)
```

Where `t(fact.source)` is recomputed live at recall time using
current peer state (not the stored `source_trust` snapshot).
Implementations SHOULD cache per-source trust scores with a TTL of
no less than 60 seconds.

Recall results SHOULD include `effective_confidence` alongside
`confidence` when `trust_mode` is `strict` or `relaxed`. Callers
MUST NOT rely on `effective_confidence` being identical to
`confidence`.

:::warning Multi-worker deployments
The default source-trust cache is per-worker and in-memory. In
multi-worker deployments (gunicorn, uvicorn `--workers`), each
worker holds an independent cache. Cache misses and stale entries
can cause non-deterministic trust scoring. For production
multi-worker deployments, configure
`STIGMEM_TRUST_CACHE_BACKEND=redis` and provide
`STIGMEM_REDIS_URL`. This will be required in a future release.
:::

#### §19.4.5 Bounds and defaults \{#section-19-4-5\}

<div className="stigmem-grid">

<div><h4>Always clamped</h4><p><code>t</code> is always clamped to [0.0, 1.0].</p></div>
<div><h4>No-component default</h4><p>A source with no computable score (all components unavailable) MUST default to <code>t = 0.5</code>.</p></div>
<div><h4>Blocklist override</h4><p>Admin blocklisted sources MUST return <code>t = 0.0</code> regardless of other components.</p></div>

</div>

### §19.5 Quarantine garden \{#section-19-5\}

#### §19.5.1 Purpose \{#section-19-5-1\}

A quarantine garden is a special-purpose Memory Garden (§17) that
holds facts pending human or automated review before they are
integrated into production scope.

#### §19.5.2 Relationship to §17 garden machinery \{#section-19-5-2\}

A quarantine garden is a `Garden` record (§17) with an additional
`quarantine: true` flag set at creation time. It inherits all §17
mechanics: it is scope-bound, ACL-controlled, facts within it are
isolated from federation, and standard garden CRUD applies.

Differences from a standard garden:

<ol className="stigmem-steps">
<li>A quarantine garden adds a <code>quarantine:moderator</code> role (§19.5.3) not present in standard gardens.</li>
<li>Facts in a quarantine garden MAY NOT be asserted directly — they are only populated by the node's automatic quarantine policy (§19.5.4) or by explicit operator action.</li>
<li>A quarantine garden MUST NOT be deleted while it holds unreviewed facts (status <code>pending</code>). Attempting deletion returns HTTP 409 <code>quarantine_has_pending_facts</code>.</li>
</ol>

#### §19.5.3 Roles \{#section-19-5-3\}

<div className="stigmem-fields">

<div>
<dt>Role</dt>
<dt><span className="stigmem-fields__type">Permissions</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>admin</code></dt>
<dt><span className="stigmem-fields__type">full</span></dt>
<dd>All §17 admin permissions; can promote/reject; can add/remove moderators.</dd>
</div>

<div>
<dt><code>quarantine:moderator</code></dt>
<dt><span className="stigmem-fields__type">moderation</span></dt>
<dd>Can promote and reject pending facts; read-only otherwise.</dd>
</div>

<div>
<dt><code>writer</code></dt>
<dt><span className="stigmem-fields__type">standard write</span></dt>
<dd>Same as §17; cannot promote/reject quarantined facts.</dd>
</div>

<div>
<dt><code>reader</code></dt>
<dt><span className="stigmem-fields__type">read-only</span></dt>
<dd>Can see quarantined facts and review metadata.</dd>
</div>

</div>

The node MUST automatically add the garden's creating principal as
`admin`. A quarantine garden MUST have at least one `admin` or
`quarantine:moderator` at all times.

#### §19.5.4 Automatic quarantine policy \{#section-19-5-4\}

When `trust_mode: strict` is set (§19.4.3), the node MUST route
inbound federated facts to the node's designated quarantine garden
when:

<div className="stigmem-grid">

<div><h4>Low trust score</h4><p>The fact's source has <code>source_trust t &lt; 0.2</code>.</p></div>
<div><h4>Missing manifest</h4><p>The fact's source lacks a valid org manifest.</p></div>
<div><h4>Provenance failure</h4><p>The fact fails provenance chain verification (§19.6.3).</p></div>

</div>

When no quarantine garden has been designated, the node MUST reject
these facts with HTTP 403 `trust_below_threshold` rather than
silently dropping them.

The node MAY also quarantine facts that trigger the recall-time
sanitizer (§19.7) in `quarantine` enforcement mode.

:::warning Pre-flight check: configure a quarantine garden before enabling strict mode
Enabling `trust_mode=strict` without configuring a quarantine
garden will cause all low-trust facts (score < 0.2) to be
permanently rejected with `403 trust_below_threshold`. Before
setting `trust_mode=strict`, create a quarantine garden and set
`quarantine_garden_id` in your federation config. A future release
will add a startup check that enforces this.
:::

#### §19.5.5 Promote and reject mechanics \{#section-19-5-5\}

**Promote.** A `quarantine:moderator` or `admin` calls
`POST /v1/gardens/:id/promote` (§5.25) with a `target_garden_id`.
The node:

<ol className="stigmem-steps">
<li>Moves the fact's <code>garden_id</code> to the <code>target_garden_id</code> (or clears it for no-garden).</li>
<li>Removes the <code>quarantine:pending</code> status marker from the fact.</li>
<li>Logs a <code>quarantine_promote</code> event to the attestation audit log.</li>
</ol>

**Reject.** A `quarantine:moderator` or `admin` calls
`POST /v1/gardens/:id/reject` (§5.25). The node:

<ol className="stigmem-steps">
<li>Sets <code>confidence = 0.0</code> on the fact (logical retraction).</li>
<li>Sets a <code>quarantine:rejected</code> marker.</li>
<li>Logs a <code>quarantine_reject</code> event to the attestation audit log.</li>
</ol>

A rejected fact is retained in the quarantine garden for audit
purposes. It MUST NOT be served in normal recall results. It MUST
be visible to garden admins and moderators via the garden-filtered
fact query.

#### §19.5.6 Auditability \{#section-19-5-6\}

All promote and reject events MUST be written to the attestation
audit log (§18.10) with the additional fields:

```
quarantine_action: "promote" | "reject"
quarantine_garden_id: <garden_id>
target_garden_id:  <garden_id> | null   // promote only
reason:            string
acted_by:          <entity_uri>
acted_at:          RFC3339
```

The audit log MUST be queryable by `quarantine_garden_id` and
`quarantine_action`.

### §19.6 Provenance chain \{#section-19-6\}

#### §19.6.1 Purpose \{#section-19-6-1\}

The provenance chain allows a fact to declare its intellectual
antecedents (`derived_from`) and carry cryptographic attestations
from intermediate processors (`attestation_chain`). Together they
create a verifiable lineage from source to recall, enabling
detection of data tampering or unexplained derivation gaps.

#### §19.6.2 Fact hash computation \{#section-19-6-2\}

A fact hash is the hex-encoded SHA-256 digest of the fact's
canonical JSON representation. The canonical form MUST be JCS
(RFC 8785) of:

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

The following fields MUST be excluded from the hash input: `id`,
`garden_id`, `attested`, `source_trust`, `derived_from`,
`attestation_chain`. This ensures the hash is stable regardless of
storage metadata or trust annotations.

#### §19.6.3 Provenance field shapes \{#section-19-6-3\}

`derived_from: [FactHash]`

<div className="stigmem-grid">

<div><h4>64-char lowercase hex</h4><p>Each <code>FactHash</code> MUST be a 64-character lowercase hex string.</p></div>
<div><h4>Logical derivation order</h4><p>Array ordered by logical derivation precedence (first = most direct antecedent).</p></div>
<div><h4>Empty = null</h4><p>An empty array is equivalent to <code>null</code> (no declared provenance).</p></div>
<div><h4>DAG required</h4><p>The reference graph MUST be a DAG. Implementations MUST detect circular references using a visited-set during traversal and MUST reject any fact that would create a cycle with HTTP 400 <code>provenance_cycle_detected</code>.</p></div>
<div><h4>Resolvable references</h4><p>The referenced facts MUST either exist in the same node or be resolvable via federation. Nodes SHOULD validate at write time in <code>trust_mode: strict</code>; in <code>relaxed</code>, MAY log a warning for dangling references.</p></div>

</div>

`attestation_chain: [Signature]`

<div className="stigmem-grid">

<div><h4>Ed25519 sigs over canonical hash</h4><p>Each <code>Signature</code> is a base64url-encoded Ed25519 signature over the canonical fact hash.</p></div>
<div><h4>Innermost-to-outermost order</h4><p>Signatures are ordered from innermost processor to outermost (first processor = index 0).</p></div>
<div><h4>Max 16 entries</h4><p><code>attestation_chain</code> MUST NOT exceed 16 entries. Nodes MUST reject facts with longer chains with HTTP 400 <code>attestation_chain_too_long</code>.</p></div>
<div><h4>Parallel issuer URIs</h4><p>Each signature is bound to a specific entity URI: the signing entity MUST include their entity URI in a parallel <code>attestation_chain_issuers: [URI]</code> field (same indexing). Implementations MUST include both fields together or neither.</p></div>
<div><h4>Verify each signature</h4><p>Verifiers MUST verify each signature in the chain using the corresponding issuer's manifest public key. A chain with an invalid signature at any position MUST be rejected entirely.</p></div>

</div>

#### §19.6.4 Verification rules \{#section-19-6-4\}

A provenance chain is **valid** if all of the following hold.

<ol className="stigmem-steps">
<li>Every <code>FactHash</code> in <code>derived_from</code> references a fact that exists and whose stored hash matches the declared value.</li>
<li>Every signature in <code>attestation_chain</code> verifies under the corresponding issuer's current manifest public key.</li>
<li>No issuer in <code>attestation_chain_issuers</code> appears more than once (no circular attestation).</li>
<li>The issuers' entity URIs each appear in their respective manifest's <code>entities</code> list.</li>
<li>If any field included in the fact hash is modified after attestation, the node MUST either: (a) clear <code>attestation_chain</code> and <code>attestation_chain_issuers</code> (treating the updated fact as unattested), or (b) reject the update with HTTP 409 <code>fact_is_attested</code>. Nodes MUST NOT retain stale attestation chains after hash-relevant field changes.</li>
</ol>

Nodes MUST reject facts with invalid provenance chains in
`trust_mode: strict`. Nodes SHOULD log warnings for invalid chains
in `trust_mode: relaxed`.

### §19.7 Recall-time content sanitizer \{#section-19-7\}

#### §19.7.1 Purpose \{#section-19-7-1\}

The recall-time content sanitizer prevents prompt-injection
payloads and malformed values from reaching the recall layer's
consumers. It is a defense-in-depth control applied at recall time,
not at write time, so that future policy changes can be retroactively
applied to already-stored facts.

The sanitizer is NOT applied at write time (storage is a transparent
record layer). It is applied immediately before facts are serialized
into the API response for `GET /v1/facts` and `GET /v1/recall`
endpoints.

#### §19.7.2 Default-deny sentinel patterns \{#section-19-7-2\}

Before applying sentinel patterns, implementations MUST normalize
all string input to Unicode NFKC form. Implementations MUST also
strip or reject the following Unicode categories: bidirectional
control characters (U+200F, U+200E, U+202A–U+202E, U+2066–U+2069)
and invisible formatting characters (U+200B–U+200D, U+FEFF).

The following patterns are checked against all string-typed
`FactValue` fields:

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

This list is the default. Operators MAY add patterns via node
configuration (`STIGMEM_SANITIZER_EXTRA_PATTERNS` as a
newline-delimited regex file). Operators MUST NOT remove default
patterns in `trust_mode: strict`.

#### §19.7.3 Schema enforcement for typed FactValues \{#section-19-7-3\}

<div className="stigmem-fields">

<div>
<dt>FactValue type</dt>
<dt><span className="stigmem-fields__type">Enforcement</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>string</code></dt>
<dt><span className="stigmem-fields__type">UTF-8 valid</span></dt>
<dd>Control characters (U+0000–U+001F except U+0009, U+000A, U+000D) MUST be removed before return.</dd>
</div>

<div>
<dt><code>number</code></dt>
<dt><span className="stigmem-fields__type">finite IEEE 754</span></dt>
<dd><code>NaN</code>, <code>+Inf</code>, <code>-Inf</code> MUST be replaced with <code>null</code>.</dd>
</div>

<div>
<dt><code>bool</code></dt>
<dt><span className="stigmem-fields__type">true/false only</span></dt>
<dd>Coercion from <code>0</code>/<code>1</code> is NOT performed; unexpected values MUST be returned as <code>null</code>.</dd>
</div>

<div>
<dt><code>ref</code></dt>
<dt><span className="stigmem-fields__type">syntactically valid URI</span></dt>
<dd>Malformed refs MUST be replaced with <code>null</code>.</dd>
</div>

<div>
<dt><code>json</code></dt>
<dt><span className="stigmem-fields__type">valid JSON</span></dt>
<dd>Malformed values MUST be replaced with <code>null</code>.</dd>
</div>

<div>
<dt><code>text</code></dt>
<dt><span className="stigmem-fields__type">string + sentinel matching</span></dt>
<dd>Same as <code>string</code>, plus sentinel pattern matching.</dd>
</div>

</div>

Facts where type enforcement produces a `null` substitution MUST
include a `sanitizer_redacted: true` marker in the API response
alongside the `null` value.

#### §19.7.4 Enforcement modes \{#section-19-7-4\}

Configured via `STIGMEM_SANITIZER_MODE`.

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Default in</span></dt>
<dd>Behavior on match</dd>
</div>

<div>
<dt><code>block</code></dt>
<dt><span className="stigmem-fields__type"><code>trust_mode: strict</code></span></dt>
<dd>Entire fact excluded; placeholder <code>{`{ "fact_id": "...", "sanitized": true }`}</code> returned in its position.</dd>
</div>

<div>
<dt><code>quarantine</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd>Fact moved to the node's quarantine garden (§19.5) and excluded from the current recall result.</dd>
</div>

<div>
<dt><code>warn</code></dt>
<dt><span className="stigmem-fields__type"><code>trust_mode: relaxed</code></span></dt>
<dd>Fact returned with <code>sanitizer_warnings: ["&lt;matched pattern&gt;"]</code>; content unmodified.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">implied by <code>trust_mode: off</code></span></dt>
<dd>No sanitizer check.</dd>
</div>

</div>

Operators MAY configure a more restrictive mode than the
`trust_mode` default. Operators MUST NOT configure a less
restrictive mode in `trust_mode: strict`.

#### §19.7.5 Placement and ordering \{#section-19-7-5\}

The sanitizer is the final processing step before serialization in
the recall pipeline:

```
Storage layer
  → Scope/garden ACL filter (§17.3)
  → Source-trust multiplier applied to effective_confidence (§19.4.4)
  → Provenance chain verification (§19.6.4, strict mode only)
  → Content sanitizer  ← HERE
  → API response serializer
```

The sanitizer MUST run after trust scoring and provenance
verification so that trust metadata is available to the enforcement
decision.

#### §19.7.6 Audit logging \{#section-19-7-6\}

Every sanitizer action MUST be logged to the attestation audit log
(§18.10):

```
sanitizer_action:  "block" | "quarantine" | "warn"
fact_id:           <uuid>
matched_pattern:   string   // the regex that triggered; "schema_enforcement" for type failures
recall_endpoint:   string   // "/v1/facts" or "/v1/recall"
ts:                RFC3339
```

### §19.8 Schema migration (migration 006) \{#section-19-8\}

Migration 006 adds three tables to support the federation trust
layer. `federation_manifests` stores org manifests indexed by
`entity_uri` and `key_id` for fast lookup during token verification.
`capability_tokens` records every token the node has issued or
accepted. `source_trust_scores` caches computed trust scores per
source URI and scope pair.

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

### §19.9 Error reference \{#section-19-9\}

<div className="stigmem-fields">

<div>
<dt>HTTP · Code</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400 · <code>manifest_signature_invalid</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd>Manifest <code>signature</code> does not verify under <code>public_key</code>.</dd>
</div>

<div>
<dt>400 · <code>manifest_rotation_chain_invalid</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd>Rotation chain verification fails.</dd>
</div>

<div>
<dt>400 · <code>token_nonce_invalid</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd>Nonce is not 32 bytes or is malformed.</dd>
</div>

<div>
<dt>400 · <code>provenance_hash_invalid</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd><code>derived_from</code> entry is not a 64-char lowercase hex string.</dd>
</div>

<div>
<dt>400 · <code>provenance_cycle_detected</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd><code>derived_from</code> graph contains a cycle.</dd>
</div>

<div>
<dt>400 · <code>attestation_chain_too_long</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd><code>attestation_chain</code> exceeds 16 entries.</dd>
</div>

<div>
<dt>400 · <code>inclusion_proof_invalid</code></dt>
<dt><span className="stigmem-fields__type">bad request</span></dt>
<dd>Checkpoint signature or Merkle path fails verification.</dd>
</div>

<div>
<dt>403 · <code>trust_below_threshold</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Fact source <code>t &lt; 0.2</code> in <code>trust_mode: strict</code> and no quarantine garden configured.</dd>
</div>

<div>
<dt>403 · <code>token_expired</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Capability token <code>expiry</code> has passed.</dd>
</div>

<div>
<dt>403 · <code>token_revoked</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Token found in revocation log.</dd>
</div>

<div>
<dt>403 · <code>token_replay</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Token nonce already seen within its validity window.</dd>
</div>

<div>
<dt>403 · <code>insufficient_capability</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Bearer's capability token does not cover the requested verb/object.</dd>
</div>

<div>
<dt>403 · <code>entity_not_in_manifest</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Source entity_uri not in the issuer's manifest <code>entities</code> list.</dd>
</div>

<div>
<dt>409 · <code>quarantine_has_pending_facts</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Attempted deletion of quarantine garden with pending facts.</dd>
</div>

<div>
<dt>409 · <code>fact_not_quarantine_pending</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Promote/reject attempted on a fact not in <code>pending</code> quarantine state.</dd>
</div>

<div>
<dt>409 · <code>fact_is_attested</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Update to a hash-relevant field rejected because <code>attestation_chain</code> is present and node configured to reject rather than clear.</dd>
</div>

<div>
<dt>422 · <code>attestation_chain_mismatch</code></dt>
<dt><span className="stigmem-fields__type">unprocessable</span></dt>
<dd><code>attestation_chain</code> and <code>attestation_chain_issuers</code> array lengths differ.</dd>
</div>

<div>
<dt>503 · <code>transparency_log_unavailable</code></dt>
<dt><span className="stigmem-fields__type">unavailable</span></dt>
<dd>Transparency log was unreachable; in <code>trust_mode: strict</code>, the manifest MUST be rejected.</dd>
</div>

</div>

### §19.10 Well-known advertisement \{#section-19-10\}

Nodes MUST extend their `/.well-known/stigmem` response to include
federation trust configuration:

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

`trust_weights` MUST be included when non-default values are
configured.
