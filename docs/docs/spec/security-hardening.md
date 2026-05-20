---
title: Security Hardening Components
sidebar_label: Security Hardening
audience: Spec
description: "Rendered entry point for hardening component specs: audit log, transport hardening, replay protection, and HLC skew bounds."
---

# Security Hardening Components \{#section-22\}

<p className="stigmem-meta"><span>10 min read</span><span>Spec contributor · Node operator</span><span>Spec-09 + Spec-10 + Spec-11 + Spec-12</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for the four hardening component
specs:
[Spec-09-Audit-Log](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/09-audit-log.md),
[Spec-10-Hardening](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/10-hardening.md),
[Spec-11-Replay-Protection](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/11-replay-protection.md),
and
[Spec-12-HLC-Bounded-Skew](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/12-hlc-bounded-skew.md).
mTLS federation, key rotation, audit log, per-principal quotas,
container baseline.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Legacy §22 anchors are retained for existing links while the
maintained hardening prose lives in the modular component specs
listed above.
:::

### §22.1 mTLS federation transport \{#section-22-1\}

#### §22.1.1 Scope \{#section-22-1-1\}

This section specifies mutual TLS requirements for all transport
connections between federated Stigmem nodes. The spec otherwise
treats the federation wire protocol as transport-agnostic (§6);
§22.1 narrows that flexibility for deployments connecting more than
one node.

#### §22.1.2 Normative requirements \{#section-22-1-2\}

<ol className="stigmem-steps">
<li>All federation transport connections between distinct Stigmem nodes MUST use mutual TLS (mTLS): both the dialing node and the accepting node MUST present a valid X.509 certificate and MUST verify the peer's certificate before data exchange begins.</li>
<li>The TLS version floor is <strong>TLS 1.3</strong>. Nodes MUST NOT negotiate TLS 1.2 or earlier on federation ports. Implementations MUST configure their TLS stack to refuse downgrade to TLS &lt; 1.3.</li>
<li>The cipher suite floor for TLS 1.3 connections MUST include at a minimum <code>TLS_AES_128_GCM_SHA256</code>, <code>TLS_AES_256_GCM_SHA384</code>, and <code>TLS_CHACHA20_POLY1305_SHA256</code>. Operators MAY restrict to a subset but MUST NOT add cipher suites outside this list without board-level security approval documented in the ops runbook.</li>
<li>Node certificate Subject Alternative Names (SANs) MUST include the node's canonical <code>entity_uri</code> (as a URI SAN). Verifying nodes MUST check that the peer's SAN matches the <code>entity_uri</code> declared in the peer's org manifest (§19.1.2) before accepting the connection as authenticated.</li>
<li>Nodes MUST reject any federation connection from a peer whose certificate chain cannot be verified against a locally configured trust root or whose SAN does not match the expected <code>entity_uri</code>.</li>
</ol>

:::warning Reverse-proxy deployments
If a reverse proxy (nginx, Caddy, Envoy) terminates TLS before the
stigmem node process, mTLS peer certificate validation is bypassed.
Set `STIGMEM_MTLS_REQUIRED=true` to force the node to reject any
connection without a verified peer certificate, even behind a proxy.
Verify this configuration in staging before enabling federation.
:::

#### §22.1.3 Cert rotation hook into §19 manifest \{#section-22-1-3\}

When a node rotates its mTLS node certificate:

<ol className="stigmem-steps">
<li>The node MUST generate a new X.509 certificate for the new key pair.</li>
<li>The new certificate's public key fingerprint MUST be recorded in the node's org manifest (§19.1) as a new <code>RotationEvent</code> (§19.1.4) alongside the Ed25519 key rotation, or in a dedicated <code>tls_cert_fingerprint</code> field on the manifest if the TLS key is distinct from the Ed25519 signing key. Implementations MUST NOT rotate the mTLS certificate silently — every rotation MUST produce a manifest update.</li>
<li>The updated manifest MUST be re-signed and re-published to <code>/.well-known/stigmem-manifest.json</code> (§19.1.6) before the new certificate is put into service.</li>
<li id="section-22-1-3-4">The updated manifest MUST be submitted to the transparency log (§19.2) as part of the rotation event. Nodes MUST NOT activate the new certificate until the transparency log submission has been acknowledged (i.e., until a <code>LogEntry</code> is received). Nodes SHOULD retry the transparency log submission for up to 24 hours before proceeding with rotation. If rotation proceeds without a log acknowledgement (e.g., due to a Rekor maintenance window), the node MUST record a <code>pending_log_submission: true</code> flag in the manifest and MUST complete the submission as soon as the log is reachable.</li>
<li id="section-22-1-3-5">During the transition window (see §22.2.2 for dual-trust period), nodes MUST accept both the old and new TLS certificates from the rotating peer. The transition window MUST NOT exceed the dual-trust period defined in §22.2.</li>
</ol>

#### §22.1.4 Client certificate provisioning \{#section-22-1-4\}

Nodes SHOULD use short-lived mTLS client certificates (≤ 24 hours)
issued by a local certificate authority dedicated to federation
transport. Operators MAY use longer-lived certificates (≤ 90 days)
provided they implement automated rotation (e.g., via cert-manager
or equivalent). Long-lived certificates MUST be listed in the node's
org manifest as described in §22.1.3.

### §22.2 Key rotation \{#section-22-2\}

#### §22.2.1 Scope \{#section-22-2-1\}

This section applies to two key types:

<div className="stigmem-fields">

<div>
<dt>Key type</dt>
<dt><span className="stigmem-fields__type">Use</span></dt>
<dd>Reference</dd>
</div>

<div>
<dt>Ed25519 node signing keys</dt>
<dt><span className="stigmem-fields__type">manifests + capability tokens</span></dt>
<dd>§19.1, §19.3.</dd>
</div>

<div>
<dt>Capability issuer keys</dt>
<dt><span className="stigmem-fields__type">live capability token issuers</span></dt>
<dd>Subset of node signing keys.</dd>
</div>

</div>

#### §22.2.2 Rollover window and dual-trust period \{#section-22-2-2\}

<ol className="stigmem-steps">
<li>The <strong>rollover window</strong> begins when a new key pair is generated and ends when all previously issued capability tokens signed by the old key have expired or been explicitly revoked.</li>
<li>During the rollover window, nodes MUST maintain a <strong>dual-trust period</strong>: both the old and new public keys are simultaneously trusted for signature verification. The dual-trust period MUST cover at least the maximum outstanding capability token lifetime from the time rotation is initiated. Since capability tokens MUST NOT exceed 90 days (§19.3.2), the dual-trust period MUST be at least 90 days unless all outstanding tokens are explicitly revoked before rotation completes.</li>
<li>Nodes MUST reject tokens signed by a key older than the dual-trust period (i.e., keys for which the dual-trust period has elapsed and which are no longer in the org manifest's rotation chain).</li>
<li>The rollover window MUST be recorded in the org manifest via a <code>RotationEvent</code> (§19.1.4). The transparency log MUST receive a separate log entry for the rotation event with <code>event_type: "key_rotation"</code> and a <code>dual_trust_expires_at</code> field indicating when the old key's trust period ends.</li>
<li>During the dual-trust period, verifiers SHOULD consult the org manifest rotation chain (§19.1.4) to identify which historic key signed a given token, rather than assuming the current manifest key.</li>
</ol>

#### §22.2.3 Transparency log entry on rotation \{#section-22-2-3\}

Every key rotation MUST produce a transparency log entry so that
federation peers and auditors can verify the chain of identity
across key transitions. The entry is signed by the **old** (retiring)
key — this anchors the new key to the prior identity and prevents a
compromised new key from fabricating a rotation event.

```
KeyRotationLogEntry:
  event_type:           "key_rotation"
  entity_uri:           URI         // the rotating node/org
  old_key_id:           hex         // key_id of the retiring key
  new_key_id:           hex         // key_id of the new key
  rotated_at:           RFC3339
  dual_trust_expires_at: RFC3339    // old key trusted until this time
  manifest_log_index:   integer     // log index of the updated manifest submission
  rotation_sig:         base64url   // Ed25519 sig over RFC 8785 JCS encoding, signed by OLD key
```

The `rotation_sig` MUST verify under the `old_key_id` public key.
The byte sequence signed MUST be the RFC 8785 JSON Canonicalization
Scheme (JCS) serialisation of the other fields: keys lexicographically
sorted, no whitespace, UTF-8 encoding, no trailing newline.

The manifest submission (§22.1.3.4) MUST be acknowledged by the
transparency log before the `KeyRotationLogEntry` is submitted; the
returned log index MUST be recorded as `manifest_log_index`.

#### §22.2.4 Rotation cadence \{#section-22-2-4\}

<div className="stigmem-fields">

<div>
<dt>Key type</dt>
<dt><span className="stigmem-fields__type">SHOULD cadence</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Ed25519 node signing keys</dt>
<dt><span className="stigmem-fields__type">≤ 365 days</span></dt>
<dd>Operators MAY define shorter cadences.</dd>
</div>

<div>
<dt>Capability issuer keys</dt>
<dt><span className="stigmem-fields__type">≤ 90 days</span></dt>
<dd>Matching the maximum token lifetime.</dd>
</div>

</div>

Cadence MUST be documented in the node's operational runbook and MAY
be declared in the node's `/.well-known/stigmem` advertisement.

### §22.3 Audit log surface \{#section-22-3\}

#### §22.3.1 Required event types \{#section-22-3-1\}

Every Stigmem node MUST emit structured audit log events for the
following operations. Each event MUST be written to the audit log
**before** the operation's response is returned to the caller
(write-ahead semantics).

<div className="stigmem-fields">

<div>
<dt>Event type</dt>
<dt><span className="stigmem-fields__type">Trigger</span></dt>
<dd>Minimum fields</dd>
</div>

<div>
<dt><code>fact_write</code></dt>
<dt><span className="stigmem-fields__type">assert/retract</span></dt>
<dd><code>event_type</code>, <code>timestamp</code>, <code>hlc</code>, <code>actor_entity</code>, <code>fact_id</code>, <code>scope</code>, <code>verb</code>.</dd>
</div>

<div>
<dt><code>fact_read</code></dt>
<dt><span className="stigmem-fields__type">recall returning ≥1 fact</span></dt>
<dd><code>event_type</code>, <code>timestamp</code>, <code>actor_entity</code>, <code>scope_filter</code>, <code>fact_ids_returned[]</code>, <code>query_strategy</code>.</dd>
</div>

<div>
<dt><code>capability_token_issue</code></dt>
<dt><span className="stigmem-fields__type">token issued</span></dt>
<dd><code>token_id</code>, <code>issuer</code>, <code>subject</code>, <code>verb</code>, <code>object</code>, <code>expiry</code>.</dd>
</div>

<div>
<dt><code>capability_token_revoke</code></dt>
<dt><span className="stigmem-fields__type">token revoked</span></dt>
<dd><code>token_id</code>, <code>issuer</code>, <code>revoked_at</code>, <code>reason</code>.</dd>
</div>

<div>
<dt><code>manifest_publish</code></dt>
<dt><span className="stigmem-fields__type">manifest published or updated</span></dt>
<dd><code>entity_uri</code>, <code>key_id</code>, <code>manifest_hash</code>.</dd>
</div>

<div>
<dt><code>key_rotation</code></dt>
<dt><span className="stigmem-fields__type">Ed25519 or mTLS key rotated</span></dt>
<dd><code>entity_uri</code>, <code>old_key_id</code>, <code>new_key_id</code>, <code>dual_trust_expires_at</code>.</dd>
</div>

<div>
<dt><code>federation_connect</code></dt>
<dt><span className="stigmem-fields__type">peer connection accepted/rejected</span></dt>
<dd><code>peer_entity_uri</code>, <code>peer_cert_fingerprint</code>, <code>outcome</code>, <code>reject_reason?</code>.</dd>
</div>

<div>
<dt><code>quarantine_admit</code></dt>
<dt><span className="stigmem-fields__type">fact admitted to quarantine</span></dt>
<dd><code>fact_id</code>, <code>source</code>, <code>admit_reason</code>.</dd>
</div>

<div>
<dt><code>quarantine_release</code></dt>
<dt><span className="stigmem-fields__type">fact released from quarantine</span></dt>
<dd><code>fact_id</code>, <code>actor_entity</code>, <code>decision</code>.</dd>
</div>

<div>
<dt><code>quota_breach</code></dt>
<dt><span className="stigmem-fields__type">per-principal quota ceiling hit</span></dt>
<dd><code>principal</code>, <code>quota_dimension</code>, <code>ceiling</code>, <code>actual</code>.</dd>
</div>

<div>
<dt><code>admin_action</code></dt>
<dt><span className="stigmem-fields__type">any admin API call</span></dt>
<dd><code>actor_entity</code>, <code>action</code>, <code>resource</code>, <code>outcome</code>.</dd>
</div>

<div>
<dt><code>replay_rejected</code></dt>
<dt><span className="stigmem-fields__type">capability token replay</span></dt>
<dd><code>token_id</code>, <code>nonce</code>, <code>reject_reason</code>.</dd>
</div>

<div>
<dt><code>instruction_audit</code></dt>
<dt><span className="stigmem-fields__type">lazy instruction preload/recall</span></dt>
<dd><code>agent_id</code>, <code>chunk_id</code>, <code>load_trigger</code>, <code>outcome</code>. MUST emit if the instruction recall layer is active; nodes not implementing the lazy instruction layer are exempt.</dd>
</div>

<div>
<dt><code>instruction_quarantined</code></dt>
<dt><span className="stigmem-fields__type">instruction-namespace quarantine</span></dt>
<dd><code>fact_id</code>, <code>actor_entity</code>, <code>source</code>, <code>reason</code>.</dd>
</div>

<div>
<dt><code>instruction_promoted</code></dt>
<dt><span className="stigmem-fields__type">quarantined instruction promoted</span></dt>
<dd><code>fact_id</code>, <code>actor_entity</code>, <code>quarantine_garden_id</code>, <code>target_garden_id?</code>.</dd>
</div>

</div>

Implementations MUST NOT omit required fields. Optional fields
(marked `?`) SHOULD be included when available.

#### §22.3.2 Ordering guarantee \{#section-22-3-2\}

Audit log events MUST be totally ordered by a monotonically
increasing sequence number within a single node. Events SHOULD
include the node's HLC tick (§2.4) alongside the wall-clock
timestamp to allow cross-node ordering reconstruction. The sequence
MUST NOT reset across node restarts.

#### §22.3.3 Retention contract \{#section-22-3-3\}

<div className="stigmem-grid">

<div><h4>Minimum 90 days</h4><p>Audit logs MUST be retained for at least 90 days.</p></div>
<div><h4>Recommended 1 year</h4><p>Operators SHOULD retain logs for 1 year for forensic purposes.</p></div>
<div><h4>Append-only storage</h4><p>Logs MUST be stored in a medium that is append-only with respect to normal operational access. Ordinary application processes MUST NOT be able to overwrite or delete log entries.</p></div>
<div><h4>Separate from fact store</h4><p>Logs MUST NOT be stored exclusively in the same database that serves the production fact store unless that database provides an independent, append-only audit trail mechanism (e.g., PostgreSQL audit extension with restricted DDL access).</p></div>

</div>

#### §22.3.4 Admin export shape \{#section-22-3-4\}

Admins MUST be able to export audit logs via the following HTTP
route.

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

<div className="stigmem-grid">

<div><h4>Admin-scoped token required</h4><p>The export route MUST require an admin-scoped token.</p></div>
<div><h4>Ascending <code>seq</code> order</h4><p>Events MUST be returned in ascending <code>seq</code> order.</p></div>
<div><h4>Streaming support</h4><p>The route MUST support streaming for large time ranges (chunked transfer or cursor pagination with <code>has_more</code>).</p></div>
<div><h4>CLI wrapper</h4><p>Operators SHOULD provide a CLI wrapper for this endpoint that writes NDJSON to stdout.</p></div>

</div>

### §22.4 Per-principal quotas \{#section-22-4\}

#### §22.4.1 Model \{#section-22-4-1\}

Stigmem implements per-principal rate limiting using a
**token-bucket** model. Each `(principal, dimension)` pair maintains
an independent token bucket. The principal is the `actor_entity` URI
derived from the authenticated caller's capability token or API key.

```
TokenBucket:
  principal:   URI      // entity URI of the caller
  dimension:   string   // quota dimension (see §22.4.2)
  capacity:    integer  // bucket size (max burst)
  rate:        float    // refill rate in tokens/second
  current:     float    // current token count (updated on each request)
  last_refill: RFC3339  // timestamp of last refill computation
```

The bucket refills continuously at `rate` tokens/second up to
`capacity`. Each qualifying request consumes 1 token unless
otherwise specified per dimension.

#### §22.4.2 Quota dimensions and default ceilings \{#section-22-4-2\}

<div className="stigmem-fields">

<div>
<dt>Dimension</dt>
<dt><span className="stigmem-fields__type">Capacity · Rate</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>fact_write</code></dt>
<dt><span className="stigmem-fields__type">100 · 10/s</span></dt>
<dd>Fact assertions and retractions.</dd>
</div>

<div>
<dt><code>fact_read</code></dt>
<dt><span className="stigmem-fields__type">500 · 50/s</span></dt>
<dd>Recall and query operations.</dd>
</div>

<div>
<dt><code>token_issue</code></dt>
<dt><span className="stigmem-fields__type">20 · 0.33/min</span></dt>
<dd>Capability token issuance.</dd>
</div>

<div>
<dt><code>federation_pull</code></dt>
<dt><span className="stigmem-fields__type">30 · 0.5/min</span></dt>
<dd>Outbound federation pull calls.</dd>
</div>

<div>
<dt><code>admin_action</code></dt>
<dt><span className="stigmem-fields__type">10 · 0.17/min</span></dt>
<dd>Admin API calls.</dd>
</div>

<div>
<dt><code>subscription_event</code></dt>
<dt><span className="stigmem-fields__type">200 · 20/s</span></dt>
<dd>Outbound subscription event deliveries.</dd>
</div>

<div>
<dt><code>audit_export</code></dt>
<dt><span className="stigmem-fields__type">10000 · 167/min</span></dt>
<dd>Rows returned from audit export endpoint.</dd>
</div>

</div>

Default ceilings MUST be applied unless overridden by an
admin-configured `QuotaPolicy` document for the principal. Overrides
MUST be stored persistently and survive node restarts.

#### §22.4.3 Backpressure response shape \{#section-22-4-3\}

When a principal's token bucket is exhausted:

<ol className="stigmem-steps">
<li>The node MUST return <strong>HTTP 429 Too Many Requests</strong> with the body shape below. <code>retry_after</code> is a float number of seconds until the bucket refills sufficiently to accept one more request at the current rate. Implementations MUST compute this as <code>(1 - current) / rate</code> (seconds to earn 1 token).</li>
<li>The node MUST include a <code>Retry-After</code> HTTP header with the integer ceiling of <code>retry_after</code>.</li>
<li>The node MUST emit a <code>quota_breach</code> audit log event (§22.3.1) for every request that hits the ceiling.</li>
<li>Nodes SHOULD propagate quota pressure upstream to federated callers via the <code>X-Stigmem-Replication-Lag</code> header (§6.7) when <code>federation_pull</code> quota is exhausted.</li>
<li>Callers MUST honour <code>Retry-After</code> and MUST implement exponential backoff with jitter after two consecutive 429 responses from the same node.</li>
</ol>

```json
{
  "error":        "quota_exceeded",
  "dimension":    "fact_write",
  "principal":    "stigmem://org/my-agent",
  "retry_after":  3.2
}
```

### §22.5 Replay protection \{#section-22-5\}

#### §22.5.1 Scope \{#section-22-5-1\}

This section extends §19.3.5 (capability token nonce) with normative
clock-skew bounds and a unified replay protection model applicable
to both capability tokens and federation handshake messages.

#### §22.5.2 Nonce and timestamp window \{#section-22-5-2\}

<ol className="stigmem-steps">
<li>Every capability token MUST include a <code>nonce</code> of 32 cryptographically random bytes (§19.3.5). Every federation handshake message MUST include an independent <code>nonce</code> of 32 cryptographically random bytes.</li>
<li>The <strong>timestamp acceptance window</strong> is ± <strong>5 minutes</strong> from the verifier's local clock. Tokens or messages with an <code>issued_at</code> timestamp outside this window MUST be rejected with a <code>timestamp_out_of_window</code> error, even if the nonce is fresh.</li>
<li>The <strong>nonce cache</strong> MUST retain seen nonces for at least the duration of the acceptance window plus the maximum token lifetime (5 minutes + 90 days for capability tokens; 5 minutes + session duration for handshake messages). Implementations MUST NOT prune nonces from the cache before this window elapses.</li>
<li>Nonces MUST be stored in a persistent cache (survives node restarts within the retention window). An in-memory-only nonce cache MUST NOT be used in production; a brief restart MUST NOT create a replay window.</li>
</ol>

#### §22.5.3 Clock-skew bounds \{#section-22-5-3\}

<div className="stigmem-fields">

<div>
<dt>Scenario</dt>
<dt><span className="stigmem-fields__type">Bound</span></dt>
<dd>Behavior on violation</dd>
</div>

<div>
<dt><code>issued_at</code> &gt; verifier clock + 5 min</dt>
<dt><span className="stigmem-fields__type">future-dated</span></dt>
<dd>Reject: <code>timestamp_future_dated</code>.</dd>
</div>

<div>
<dt><code>issued_at</code> &lt; verifier clock − 5 min</dt>
<dt><span className="stigmem-fields__type">stale</span></dt>
<dd>Reject: <code>timestamp_stale</code>.</dd>
</div>

<div>
<dt><code>expiry</code> &lt; verifier clock</dt>
<dt><span className="stigmem-fields__type">expired</span></dt>
<dd>Reject: <code>token_expired</code>.</dd>
</div>

<div>
<dt><code>expiry</code> &gt; <code>issued_at</code> + 90 days</dt>
<dt><span className="stigmem-fields__type">excessive lifetime</span></dt>
<dd>Reject: <code>token_lifetime_exceeded</code>.</dd>
</div>

</div>

Nodes MUST synchronise their system clocks via NTP (or equivalent).
Operators SHOULD configure alerts if clock drift exceeds 30 seconds.

#### §22.5.4 Error codes \{#section-22-5-4\}

<div className="stigmem-fields">

<div>
<dt>HTTP · Code</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>401 · <code>timestamp_future_dated</code></dt>
<dt><span className="stigmem-fields__type">replay</span></dt>
<dd><code>issued_at</code> more than 5 minutes in the future.</dd>
</div>

<div>
<dt>401 · <code>timestamp_stale</code></dt>
<dt><span className="stigmem-fields__type">replay</span></dt>
<dd><code>issued_at</code> more than 5 minutes in the past.</dd>
</div>

<div>
<dt>401 · <code>token_expired</code></dt>
<dt><span className="stigmem-fields__type">lifecycle</span></dt>
<dd>Token <code>expiry</code> has passed.</dd>
</div>

<div>
<dt>401 · <code>token_lifetime_exceeded</code></dt>
<dt><span className="stigmem-fields__type">policy</span></dt>
<dd>Token <code>expiry</code> − <code>issued_at</code> &gt; 90 days.</dd>
</div>

<div>
<dt>401 · <code>token_replay</code></dt>
<dt><span className="stigmem-fields__type">replay</span></dt>
<dd>Nonce already seen within the retention window.</dd>
</div>

</div>

### §22.6 Container baseline \{#section-22-6\}

#### §22.6.1 Scope \{#section-22-6-1\}

This section specifies the normative security posture for reference
operator container images published by Eidetic Labs. Third-party
operators running Stigmem from source SHOULD adopt the same baseline.

:::note v0.9.0a1 status
The Docker / Docker Compose requirements in this section apply to
the supported v0.9.0a1 deployment surface. Requirements that
reference **Helm charts** or **Kubernetes manifests** apply
conditionally: in v0.9.0a1 those deployment surfaces are deferred to
[`experimental/deploy-helm/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/deploy-helm)
and unsupported until they pass the
[ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md).
:::

#### §22.6.2 Distroless image \{#section-22-6-2\}

<ol className="stigmem-steps">
<li>Reference operator images MUST be built FROM a <a href="https://github.com/GoogleContainerTools/distroless">distroless base</a> (e.g., <code>gcr.io/distroless/cc-debian12</code> or equivalent). Images MUST NOT include a shell (<code>sh</code>, <code>bash</code>) in the production layer.</li>
<li>Multi-stage builds MUST be used: build dependencies and tools MUST be confined to a builder stage and MUST NOT appear in the final image layer.</li>
<li>The image MUST contain only the Stigmem node binary and its minimal runtime dependencies (shared libraries, CA bundle, tzdata).</li>
</ol>

#### §22.6.3 Non-root user \{#section-22-6-3\}

<ol className="stigmem-steps">
<li>The container MUST run as a non-root user. The <code>Dockerfile</code> MUST include a <code>USER</code> directive setting a non-zero UID (SHOULD use UID 1000) in the final stage.</li>
<li>The container MUST NOT be run with <code>--privileged</code> or with <code>CAP_SYS_ADMIN</code>. Operators MUST NOT grant any Linux capabilities beyond the minimum required (if port &lt; 1024, use <code>CAP_NET_BIND_SERVICE</code>; SHOULD use a port ≥ 1024).</li>
<li>Kubernetes / container runtime manifests for reference deployments MUST include:</li>
</ol>

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
```

#### §22.6.4 Read-only root filesystem \{#section-22-6-4\}

<ol className="stigmem-steps">
<li>The container's root filesystem MUST be mounted read-only (<code>readOnlyRootFilesystem: true</code> in Kubernetes). All writable state (database files, log buffers, temporary files) MUST be mounted as explicit volumes or <code>emptyDir</code> mounts.</li>
<li>Reference Helm charts MUST configure <code>readOnlyRootFilesystem: true</code> by default and MUST document which volumes require write access.</li>
</ol>

#### §22.6.5 Seccomp profile \{#section-22-6-5\}

<ol className="stigmem-steps">
<li>Reference images MUST ship a <a href="https://docs.kernel.org/userspace-api/seccomp_filter.html">seccomp</a> profile that allows only the syscalls required by the Stigmem node binary. The profile MUST deny <code>ptrace</code>, <code>process_vm_readv</code>, <code>process_vm_writev</code>, <code>kexec_load</code>, and <code>perf_event_open</code> at a minimum.</li>
<li>Kubernetes deployments MUST apply the profile via <code>seccompProfile.type: Localhost</code> with <code>localhostProfile: profiles/stigmem-node.json</code>, or <code>type: RuntimeDefault</code> where a restrictive runtime default is confirmed equivalent. <code>Unconfined</code> MUST NOT be used in production.</li>
<li>The seccomp profile MUST be published alongside each release in <code>deploy/seccomp/stigmem-node.json</code> and versioned with the binary.</li>
</ol>

#### §22.6.6 Image signing \{#section-22-6-6\}

Reference images MUST be signed using
[Sigstore Cosign](https://github.com/sigstore/cosign) and the
signature MUST be pushed to the same registry. Operators SHOULD
verify the image signature before deployment using `cosign verify`.
Image digests (not mutable tags) MUST be used in all reference
Kubernetes manifests and Helm chart `values.yaml` defaults.

### §22.7 Transparency log own-instance decision memo \{#section-22-7\}

#### §22.7.1 Purpose \{#section-22-7-1\}

§19.2.2 permits but does not require operating a self-hosted Rekor
instance. This section provides normative decision criteria so that
operators can determine whether self-hosting is appropriate, and
records the Eidetic Labs reference deployment position.

#### §22.7.2 Decision criteria \{#section-22-7-2\}

An operator SHOULD self-host a Rekor instance if and only if ALL of
the following criteria are met.

<div className="stigmem-fields">

<div>
<dt>Criterion</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Rationale</dd>
</div>

<div>
<dt>Private network without external egress</dt>
<dt><span className="stigmem-fields__type">connectivity</span></dt>
<dd>Public Rekor requires egress to <code>rekor.sigstore.dev</code>.</dd>
</div>

<div>
<dt>Federation peers are all internal</dt>
<dt><span className="stigmem-fields__type">topology</span></dt>
<dd>Public log provides independent verifiability for external peers; private log acceptable for closed meshes.</dd>
</div>

<div>
<dt>Commit to ≥ 99.9% uptime</dt>
<dt><span className="stigmem-fields__type">operations</span></dt>
<dd>Federation peers depend on the log for manifest verification in <code>trust_mode: strict</code>.</dd>
</div>

<div>
<dt>Independent peer accessibility</dt>
<dt><span className="stigmem-fields__type">protocol SHOULD</span></dt>
<dd>§19.2.2 SHOULD: log SHOULD be independently accessible to all peers.</dd>
</div>

<div>
<dt>Dedicated ops team / automation</dt>
<dt><span className="stigmem-fields__type">key ceremony</span></dt>
<dd>Rekor key rotation is operationally complex and MUST NOT be performed ad-hoc.</dd>
</div>

</div>

If any criterion is not met, the operator SHOULD use the public
Rekor instance at `https://rekor.sigstore.dev` (or a hosted
equivalent). Operators MUST NOT self-host without documented answers
to each criterion in their ops runbook.

#### §22.7.3 Reference deployment position (Eidetic Labs) \{#section-22-7-3\}

The Eidetic Labs reference deployment uses the **public Rekor
instance** (`https://rekor.sigstore.dev`).

<div className="stigmem-fields">

<div>
<dt>Criterion</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Private network without egress</dt>
<dt><span className="stigmem-fields__type">Not met</span></dt>
<dd>Reference node targets public deployments.</dd>
</div>

<div>
<dt>Internal-only federation</dt>
<dt><span className="stigmem-fields__type">Not met</span></dt>
<dd>External federation is a core use-case.</dd>
</div>

<div>
<dt>Ops commitment ≥ 99.9%</dt>
<dt><span className="stigmem-fields__type">Not evaluated</span></dt>
<dd>Would require dedicated SRE investment.</dd>
</div>

<div>
<dt>Independent peer accessibility</dt>
<dt><span className="stigmem-fields__type">Not evaluated</span></dt>
<dd>Moot given above.</dd>
</div>

<div>
<dt>Dedicated key ceremony team</dt>
<dt><span className="stigmem-fields__type">Not evaluated</span></dt>
<dd>Moot given above.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Decision: defer self-hosted Rekor to backlog.**

A self-hosted Rekor instance for the Eidetic Labs reference
deployment does not meet the minimum decision criteria at this
phase. Reconsider when (a) a private-network deployment tier is
productised, or (b) a dedicated SRE function is established.

</div>

#### §22.7.4 Configuration \{#section-22-7-4\}

```
STIGMEM_TRANSPARENCY_LOG_URL=https://rekor.sigstore.dev
STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY=<base64-encoded ECDSA key from GET /api/v1/log>
```

The public key is pinned explicitly rather than discovered at
runtime — this ensures the node always verifies log entries against
a known trust anchor even if the Rekor URL is compromised.
`STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST be pinned explicitly; key
discovery via the URL alone MUST NOT be the sole trust anchor in
production.

#### §22.7.5 Transparency log public-key rotation \{#section-22-7-5\}

The Sigstore/Rekor root signing key is subject to rotation (a root
key rotation occurred in 2022). Operators pinning
`STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST have a documented
procedure for updating the pin.

<ol className="stigmem-steps">
<li>Operators SHOULD subscribe to Sigstore transparency log key rotation announcements (the <a href="https://groups.google.com/g/sigstore-announce">sigstore-announce mailing list</a> and the CT log transparency dashboard) and SHOULD update <code>STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY</code> within <strong>30 days</strong> of a published rotation.</li>
<li>A node MUST NOT treat a persistent transparency log key verification failure as a permanent misconfiguration without first checking whether a Rekor root key rotation has occurred. On repeated verification failures, the node SHOULD emit a <code>transparency_log_key_mismatch</code> audit log event and surface an operator alert before entering a degraded-verification state.</li>
</ol>

## Subsection anchors \{#subsection-anchors\}

*Anchors below are provided so docs links to specific subsections
always resolve, even when the subsection text lives only in earlier
spec drafts.*

### §22.1.2.3 \{#section-22-1-2-3\}

### §22.1.2.4 \{#section-22-1-2-4\}

### §22.1.3.4 \{#section-22-1-3-4\}

### §22.1.3.5 \{#section-22-1-3-5\}
