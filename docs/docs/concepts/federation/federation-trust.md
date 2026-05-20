---
title: Federation Trust (Spec-05-Federation-Trust)
sidebar_label: Federation Trust
description: Org manifests, capability tokens, source-trust scoring, quarantine garden, provenance chains, and the recall-time sanitizer across the modular spec set.
audience: Integrator
---

# Federation Trust

<p className="stigmem-meta"><span>9 min read</span><span>Node operator · Spec contributor</span><span>Spec-04 + Spec-05 + Spec-06 + Spec-08 + Spec-15</span></p>

<div className="stigmem-lead">

**What this page is**

The mechanism by which Stigmem nodes establish verifiable identity,
delegate cross-org write permissions, score incoming sources,
quarantine untrusted facts, and sanitize recall output — without
centralized coordination.

</div>

Federation trust is described across the modular specs. It builds on
Spec-X6-Source-Attestation machinery and adds seven interlocking
subsystems.

<div className="stigmem-fields">

<div>
<dt>Subsystem</dt>
<dt><span className="stigmem-fields__type">Spec</span></dt>
<dd>Summary</dd>
</div>

<div>
<dt>Org manifests</dt>
<dt><span className="stigmem-fields__type">Spec-04-Manifests</span></dt>
<dd>Signed identity document; binds entity URIs to an Ed25519 public key.</dd>
</div>

<div>
<dt>Transparency log</dt>
<dt><span className="stigmem-fields__type">Spec-05</span></dt>
<dd>Append-only audit anchor for manifests and revocations.</dd>
</div>

<div>
<dt>Capability tokens</dt>
<dt><span className="stigmem-fields__type">Spec-06-Capability-Tokens</span></dt>
<dd>Short-lived signed credentials delegating specific verbs on specific resources.</dd>
</div>

<div>
<dt>Source-trust score</dt>
<dt><span className="stigmem-fields__type">Spec-05</span></dt>
<dd>Scalar <code>t ∈ [0,1]</code> per source; modulates effective confidence at recall time.</dd>
</div>

<div>
<dt>Quarantine garden</dt>
<dt><span className="stigmem-fields__type">Spec-08-Quarantine-Garden</span></dt>
<dd>Isolation zone for facts that fail trust thresholds.</dd>
</div>

<div>
<dt>Provenance chain</dt>
<dt><span className="stigmem-fields__type">Spec-05</span></dt>
<dd><code>derived_from</code> + <code>attestation_chain</code> for verifiable fact lineage.</dd>
</div>

<div>
<dt>Recall-time sanitizer</dt>
<dt><span className="stigmem-fields__type">ADR-003</span></dt>
<dd>Strips prompt-injection sentinels from recalled string values.</dd>
</div>

</div>

## Org manifest

An **org manifest** declares the canonical Ed25519 public key for a
node or organisation and the entity URIs it is authoritative for.
Peers use the manifest key to verify capability tokens and provenance
signatures.

### Publish your manifest

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

<div className="stigmem-keypoint">

**Signature MUST be computed over the JCS (RFC 8785) canonical encoding of all other manifest fields.**

</div>

### Well-known endpoint

Nodes MUST publish their manifest at
`/.well-known/stigmem-manifest.json`. Peers resolve it with:

```bash
curl https://peer-node.example.com/.well-known/stigmem-manifest.json
```

### Key rotation

When rotating your signing key, add a `rotation_events` entry signed
by the **old** private key. This preserves a verifiable chain of
custody back to the original manifest.

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

Submit the updated manifest to the transparency log after every
rotation.

### Manifest resolution

```bash
ENTITY_URI_ENCODED=$(python3 -c "import urllib.parse, sys; \
  print(urllib.parse.quote(sys.argv[1], safe=''))" \
  "stigmem://peer-org.example")

curl https://your-node.example.com/v1/federation/manifest/$ENTITY_URI_ENCODED
# → 200 { ...manifest object... }
# → 404 if no manifest found for entity_uri
```

## Transparency log

The transparency log is an append-only, tamper-evident audit anchor.
Implementations SHOULD integrate with
[Rekor](https://docs.sigstore.dev/rekor/overview/) (Sigstore) or an
equivalent log that provides Merkle-tree inclusion proofs.

After submitting a manifest, store the `LogEntry` at
`/.well-known/stigmem-manifest-proof.json` so peers can independently
verify inclusion.

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

<div className="stigmem-keypoint">

**In `trust_mode: strict`, peers MUST verify log inclusion proofs before trusting a manifest.**

Capability token revocations MUST also be submitted as separate log
entries.

</div>

## Capability tokens

A **capability token** grants a specific subject a specific verb on a
specific resource. Tokens replace ad-hoc per-peer trust agreements
with a verifiable, revocable delegation primitive.

### Token shape

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>token_version</code></dt>
<dt><span className="stigmem-fields__type">int</span></dt>
<dd>MUST be 1 for this spec version.</dd>
</div>

<div>
<dt><code>token_id</code></dt>
<dt><span className="stigmem-fields__type">UUID</span></dt>
<dd>Used for revocation lookup.</dd>
</div>

<div>
<dt><code>issuer</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd>MUST be in issuer's manifest <code>entities</code> list.</dd>
</div>

<div>
<dt><code>subject</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd>The token bearer's entity URI.</dd>
</div>

<div>
<dt><code>verb</code></dt>
<dt><span className="stigmem-fields__type">enum</span></dt>
<dd><code>read</code> · <code>write</code> · <code>admin</code> · <code>federate</code></dd>
</div>

<div>
<dt><code>object</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd>Scope, garden, or <code>"&#42;"</code>.</dd>
</div>

<div>
<dt><code>issued_at</code></dt>
<dt><span className="stigmem-fields__type">RFC3339</span></dt>
<dd></dd>
</div>

<div>
<dt><code>expiry</code></dt>
<dt><span className="stigmem-fields__type">RFC3339</span></dt>
<dd>MUST be set; MUST NOT exceed 90 days from <code>issued_at</code>.</dd>
</div>

<div>
<dt><code>nonce</code></dt>
<dt><span className="stigmem-fields__type">hex</span></dt>
<dd>32 bytes cryptographically random.</dd>
</div>

<div>
<dt><code>signature</code></dt>
<dt><span className="stigmem-fields__type">base64url</span></dt>
<dd>Ed25519 sig over JCS-canonical body, signed by issuer key.</dd>
</div>

</div>

### Issue a token

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

### Verify a token

Receivers MUST verify a token before honoring it.

<ol className="stigmem-steps">
<li>Resolve the issuer's org manifest.</li>
<li>Verify the manifest's self-signature.</li>
<li>Verify the token's <code>signature</code> under the manifest's <code>public_key</code>.</li>
<li>Confirm <code>subject</code> appears in the issuer's <code>entities</code> list or is an explicitly delegated external entity.</li>
<li>Check <code>expiry &gt; now</code>.</li>
<li>Confirm the token is not revoked.</li>
</ol>

### Revoke a token

```bash
curl -X POST https://your-node.example.com/v1/federation/capability-tokens/$TOKEN_ID/revoke \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -d '{}'
# → 204; revocation is logged to the transparency log
```

A revoked token MUST be rejected even if it has not yet expired.
Nodes SHOULD cache revocation events with a TTL of at least 60
seconds.

## Source-trust score

Every inbound fact source receives a scalar `t ∈ [0,1]`. At recall
time, effective confidence is:

```
effective_confidence = fact.confidence × t(fact.source)
```

`t` is recomputed live at recall time using current peer state. The
`source_trust` snapshot stored on the fact is informational only.

### Derivation formula

```
t = clamp(
      0.35 × identity_strength(source)
    + 0.30 × peer_history(source)
    + 0.25 × scope_authority(source, scope)
    + 0.10 × attestation_mode_factor(node.attestation_mode),
    0.0, 1.0
  )
```

<div className="stigmem-fields">

<div>
<dt>Component</dt>
<dt><span className="stigmem-fields__type">Weight</span></dt>
<dd>What it measures</dd>
</div>

<div>
<dt><code>identity_strength</code></dt>
<dt><span className="stigmem-fields__type">0.35</span></dt>
<dd>Rewards sources with a verified org manifest and log inclusion proof (max 1.0); penalizes unrecognized or absent sources (min 0.0).</dd>
</div>

<div>
<dt><code>peer_history</code></dt>
<dt><span className="stigmem-fields__type">0.30</span></dt>
<dd>Rewards sources with a clean attestation track record; new sources default to 0.5.</dd>
</div>

<div>
<dt><code>scope_authority</code></dt>
<dt><span className="stigmem-fields__type">0.25</span></dt>
<dd>Rewards sources holding a valid <code>write</code> capability token for the target scope (1.0) or an admin key (0.9).</dd>
</div>

<div>
<dt><code>attestation_mode_factor</code></dt>
<dt><span className="stigmem-fields__type">0.10</span></dt>
<dd>Reflects the node's attestation strictness: <code>enforce</code> → 1.0, <code>warn</code> → 0.6, <code>off</code> → 0.2.</dd>
</div>

</div>

If all components are unavailable, `t` defaults to 0.5.
Admin-blocklisted sources always receive `t = 0.0`.

### Trust mode

Configure via `STIGMEM_TRUST_MODE`.

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Posture</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>strict</code></dt>
<dt><span className="stigmem-fields__type">enforced</span></dt>
<dd>Log inclusion proofs required; sources with <code>t &lt; 0.2</code> are quarantined.</dd>
</div>

<div>
<dt><code>relaxed</code> (default)</dt>
<dt><span className="stigmem-fields__type">observed</span></dt>
<dd>Trust scoring active; low scores logged but not quarantined.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">disabled</span></dt>
<dd>No scoring; <code>source_trust</code> is <code>null</code> on all stored facts.</dd>
</div>

</div>

When using non-default trust weights, declare them at
`/.well-known/stigmem` under `federation_trust.trust_weights`.

## Quarantine garden

A **quarantine garden** is a Memory Garden (Spec-02-Scopes-and-ACL)
with `quarantine: true` set at creation. It holds facts pending human
or automated review before they enter production scope.

In `trust_mode: strict`, the node automatically routes inbound facts
to the designated quarantine garden when:

<div className="stigmem-grid">

<div><h4>Low trust score</h4><p>The source has <code>t &lt; 0.2</code>.</p></div>
<div><h4>Missing manifest</h4><p>The source lacks a valid org manifest.</p></div>
<div><h4>Provenance failure</h4><p>The fact fails provenance chain verification.</p></div>

</div>

If no quarantine garden is designated, these facts are rejected with
HTTP 403 `trust_below_threshold`.

### Review quarantined facts

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

Callers need the `quarantine:moderator` or `admin` role on the
quarantine garden. All promote and reject events are written to the
attestation audit log.

A rejected fact is retained in the quarantine garden for audit and
MUST NOT appear in normal recall results.

## Provenance chain

Facts may declare their intellectual antecedents and carry
cryptographic attestations from intermediate processors. Two new
fields extend the modular fact record.

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>derived_from</code></dt>
<dt><span className="stigmem-fields__type"><code>[FactHash]</code></span></dt>
<dd>SHA-256 hashes of antecedent facts; ordered by derivation precedence.</dd>
</div>

<div>
<dt><code>attestation_chain</code></dt>
<dt><span className="stigmem-fields__type"><code>[Signature]</code></span></dt>
<dd>Ed25519 signatures from intermediate processors; paired with <code>attestation_chain_issuers</code>.</dd>
</div>

</div>

### Fact hash computation

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

The following fields are excluded: `id`, `garden_id`, `attested`,
`source_trust`, `derived_from`, `attestation_chain`,
`attestation_chain_issuers`. Excluding trust annotations keeps the
hash stable across metadata updates.

### Example fact with provenance

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

### Verification rules

A provenance chain is **valid** if all of the following hold.

<ol className="stigmem-steps">
<li>Every <code>FactHash</code> in <code>derived_from</code> references a fact that exists and whose stored hash matches the declared value.</li>
<li>Every signature in <code>attestation_chain</code> verifies under the corresponding issuer's current manifest public key.</li>
<li>No issuer appears more than once in <code>attestation_chain_issuers</code>.</li>
<li>Each issuer's entity URI appears in their manifest's <code>entities</code> list.</li>
</ol>

In `trust_mode: strict`, facts with invalid provenance chains MUST be
rejected. In `relaxed` mode, warnings are logged.

## Recall-time content sanitizer

The sanitizer prevents prompt-injection payloads from reaching recall
consumers. It is applied immediately before API response
serialization — **not at write time** — so future policy changes
apply retroactively to stored facts.

The sanitizer runs as the final step in the recall pipeline:

```
Storage
  → Scope/garden ACL filter
  → Source-trust multiplier → effective_confidence
  → Provenance chain verification (strict only)
  → Content sanitizer   ← HERE
  → API response serialiser
```

### Enforcement modes

Configure via `STIGMEM_SANITIZER_MODE`.

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Default in</span></dt>
<dd>Behavior on match</dd>
</div>

<div>
<dt><code>block</code></dt>
<dt><span className="stigmem-fields__type">strict</span></dt>
<dd>Fact excluded; <code>{`{ "fact_id": "...", "sanitized": true }`}</code> placeholder returned.</dd>
</div>

<div>
<dt><code>quarantine</code></dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd>Fact moved to quarantine garden and excluded from current result.</dd>
</div>

<div>
<dt><code>warn</code></dt>
<dt><span className="stigmem-fields__type">relaxed</span></dt>
<dd>Fact returned with <code>sanitizer_warnings: ["&lt;matched pattern&gt;"]</code>.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">implied by <code>trust_mode: off</code></span></dt>
<dd>No sanitization.</dd>
</div>

</div>

Operators MAY configure a stricter mode than the `trust_mode`
default; they MUST NOT configure a less restrictive mode in
`trust_mode: strict`.

### Default sentinel patterns

The following are checked against string- and text-typed `FactValue`
fields.

<div className="stigmem-grid">

<div><h4>Imperative override</h4><p><code>ignore [all] previous instructions</code> · <code>disregard [all] previous prompt/instructions</code></p></div>
<div><h4>Mode hijack</h4><p><code>you are now [in a] different/new mode</code> · <code>act as [an] evil/unfiltered/uncensored/dan</code></p></div>
<div><h4>System prompt leak</h4><p><code>system prompt:</code></p></div>
<div><h4>Chat-template tokens</h4><p><code>&lt;|im_start|&gt;</code> · <code>&lt;|im_end|&gt;</code> · <code>[INST]</code> · <code>[/INST]</code></p></div>
<div><h4>Role markers</h4><p><code>Human:</code> · <code>Assistant:</code> (chat-template leaks).</p></div>
<div><h4>Prototype pollution</h4><p><code>{`{"__proto__":`}</code> · <code>{`{"constructor":`}</code></p></div>

</div>

Add extra patterns via `STIGMEM_SANITIZER_EXTRA_PATTERNS`
(newline-delimited regex file). Operators MUST NOT remove default
patterns in `trust_mode: strict`.

### Schema enforcement at recall time

The sanitizer also enforces type correctness for structured values.
`NaN` / `±Inf` numbers, malformed refs, and invalid JSON blobs are
replaced with `null`. Facts where substitution occurs are marked
`sanitizer_redacted: true` in the response.

### Audit logging

Every sanitizer action is logged to the attestation audit log
(Spec-X6-Source-Attestation section 10) with `sanitizer_action`,
`fact_id`, `matched_pattern`, and `recall_endpoint`.

## Well-known advertisement

Nodes MUST extend their `/.well-known/stigmem` response to declare
federation trust configuration:

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

`trust_weights` is required only when non-default values are
configured.

## Error reference

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
<dt>403 · <code>trust_below_threshold</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Source <code>t &lt; 0.2</code> in strict mode; no quarantine garden configured.</dd>
</div>

<div>
<dt>403 · <code>token_expired</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Capability token expiry has passed.</dd>
</div>

<div>
<dt>403 · <code>token_revoked</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Token found in revocation log.</dd>
</div>

<div>
<dt>403 · <code>token_replay</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Token nonce already seen within validity window.</dd>
</div>

<div>
<dt>403 · <code>insufficient_capability</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Token does not cover the requested verb/object.</dd>
</div>

<div>
<dt>403 · <code>entity_not_in_manifest</code></dt>
<dt><span className="stigmem-fields__type">forbidden</span></dt>
<dd>Source entity URI not in issuer's manifest <code>entities</code> list.</dd>
</div>

<div>
<dt>409 · <code>quarantine_has_pending_facts</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Attempted deletion of quarantine garden with pending facts.</dd>
</div>

<div>
<dt>409 · <code>fact_not_quarantine_pending</code></dt>
<dt><span className="stigmem-fields__type">conflict</span></dt>
<dd>Promote/reject on a non-pending fact.</dd>
</div>

<div>
<dt>422 · <code>attestation_chain_mismatch</code></dt>
<dt><span className="stigmem-fields__type">unprocessable</span></dt>
<dd><code>attestation_chain</code> and <code>attestation_chain_issuers</code> array lengths differ.</dd>
</div>

</div>

## See also

<div className="stigmem-next">

<a href="./federation">
<strong>Concepts</strong>
<span>Federation overview</span>
<small>Peer handshake and Spec-05 wire protocol.</small>
</a>

<a href="./federation-4node">
<strong>Concepts</strong>
<span>4-node topology</span>
<small>Multi-node setup examples.</small>
</a>

<a href="../../spec/index">
<strong>Spec</strong>
<span>Spec-X6 Source Attestation</span>
<small>The Spec-X6 foundation Spec-05 builds on.</small>
</a>

</div>
