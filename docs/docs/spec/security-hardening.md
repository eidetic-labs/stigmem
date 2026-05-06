---
title: §22. Security Hardening
sidebar_label: §22 Security Hardening
audience: Spec
description: "Stigmem spec section 22 — mTLS federation, key rotation, audit log, per-principal quotas, container baseline."
---

# §22. Security Hardening {#section-22}

**Status:** DRAFT normative (v1.1-draft, Phase 12)

mTLS federation, key rotation, audit log, per-principal quotas, container baseline.

**Authoritative source:** [`spec/stigmem-spec-v1.1-draft.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.1-draft.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** DRAFT normative (Phase 12). §22.1–§22.7 carry MUST/SHOULD/MAY normative language.

### §22.1 mTLS Federation Transport {#section-22-1}

#### §22.1.1 Scope {#section-22-1-1}

This section specifies mutual TLS requirements for all transport connections between federated Stigmem nodes. The spec otherwise treats the federation wire protocol as transport-agnostic (§6); §22.1 narrows that flexibility for deployments connecting more than one node.

#### §22.1.2 Normative Requirements {#section-22-1-2}

1. All federation transport connections between distinct Stigmem nodes MUST use mutual TLS (mTLS): both the dialing node and the accepting node MUST present a valid X.509 certificate and MUST verify the peer's certificate before data exchange begins.
2. The TLS version floor is **TLS 1.3**. Nodes MUST NOT negotiate TLS 1.2 or earlier on federation ports. Implementations MUST configure their TLS stack to refuse downgrade to TLS < 1.3.
3. The cipher suite floor for TLS 1.3 connections MUST include at a minimum:
   - `TLS_AES_128_GCM_SHA256`
   - `TLS_AES_256_GCM_SHA384`
   - `TLS_CHACHA20_POLY1305_SHA256`

   Operators MAY restrict to a subset of the above for compliance purposes, but MUST NOT add cipher suites outside this list without board-level security approval documented in their node's ops runbook.
4. Node certificate Subject Alternative Names (SANs) MUST include the node's canonical `entity_uri` (as a URI SAN). Verifying nodes MUST check that the peer's SAN matches the `entity_uri` declared in the peer's org manifest (§19.1.2) before accepting the connection as authenticated.
5. Nodes MUST reject any federation connection from a peer whose certificate chain cannot be verified against a locally configured trust root or whose SAN does not match the expected `entity_uri`.

:::warning Reverse-proxy deployments
If a reverse proxy (nginx, Caddy, Envoy) terminates TLS before the stigmem node process, mTLS peer certificate validation is bypassed. Set `STIGMEM_MTLS_REQUIRED=true` to force the node to reject any connection without a verified peer certificate, even behind a proxy. Verify this configuration in staging before enabling federation.
:::

#### §22.1.3 Cert Rotation Hook into §19 Manifest {#section-22-1-3}

When a node rotates its mTLS node certificate:

1. The node MUST generate a new X.509 certificate for the new key pair.
2. The new certificate's public key fingerprint MUST be recorded in the node's org manifest (§19.1) as a new `RotationEvent` (§19.1.4) alongside the Ed25519 key rotation, or in a dedicated `tls_cert_fingerprint` field on the manifest if the TLS key is distinct from the Ed25519 signing key. Implementations MUST NOT rotate the mTLS certificate silently — every rotation MUST produce a manifest update.
3. The updated manifest MUST be re-signed and re-published to `/.well-known/stigmem-manifest.json` (§19.1.6) before the new certificate is put into service.
4. The updated manifest MUST be submitted to the transparency log (§19.2) as part of the rotation event. Nodes MUST NOT activate the new certificate until the transparency log submission has been acknowledged (i.e., until a `LogEntry` is received). Nodes SHOULD retry the transparency log submission for up to 24 hours before proceeding with rotation. If rotation proceeds without a log acknowledgement (e.g., due to a Rekor maintenance window), the node MUST record a `pending_log_submission: true` flag in the manifest and MUST complete the submission as soon as the log is reachable.
5. During the transition window (see §22.2.2 for dual-trust period), nodes MUST accept both the old and new TLS certificates from the rotating peer. The transition window MUST NOT exceed the dual-trust period defined in §22.2.

#### §22.1.4 Client Certificate Provisioning {#section-22-1-4}

Nodes SHOULD use short-lived mTLS client certificates (≤ 24 hours) issued by a local certificate authority dedicated to federation transport. Operators MAY use longer-lived certificates (≤ 90 days) provided they implement automated rotation (e.g., via cert-manager or equivalent). Long-lived certificates MUST be listed in the node's org manifest as described in §22.1.3.

---

### §22.2 Key Rotation {#section-22-2}

#### §22.2.1 Scope {#section-22-2-1}

This section applies to two key types:
- **Ed25519 node signing keys** — used to sign org manifests and capability tokens (§19.1, §19.3).
- **Capability issuer keys** — the subset of node signing keys used as issuers in live capability tokens.

#### §22.2.2 Rollover Window and Dual-Trust Period {#section-22-2-2}

1. The **rollover window** begins when a new key pair is generated and ends when all previously issued capability tokens signed by the old key have expired or been explicitly revoked.
2. During the rollover window, nodes MUST maintain a **dual-trust period**: both the old and new public keys are simultaneously trusted for signature verification. The dual-trust period MUST cover at least the maximum outstanding capability token lifetime from the time rotation is initiated. Since capability tokens MUST NOT exceed 90 days (§19.3.2), the dual-trust period MUST be at least 90 days unless all outstanding tokens are explicitly revoked before rotation completes.
3. Nodes MUST reject tokens signed by a key older than the dual-trust period (i.e., keys for which the dual-trust period has elapsed and which are no longer in the org manifest's rotation chain).
4. The rollover window MUST be recorded in the org manifest via a `RotationEvent` (§19.1.4). The transparency log MUST receive a separate log entry for the rotation event with `event_type: "key_rotation"` and a `dual_trust_expires_at` field indicating when the old key's trust period ends.
5. During the dual-trust period, verifiers SHOULD consult the org manifest rotation chain (§19.1.4) to identify which historic key signed a given token, rather than assuming the current manifest key.

#### §22.2.3 Transparency Log Entry on Rotation {#section-22-2-3}

Every key rotation MUST produce a transparency log entry so that federation
peers and auditors can verify the chain of identity across key transitions.
The entry is signed by the **old** (retiring) key — this anchors the new key
to the prior identity and prevents a compromised new key from fabricating a
rotation event. The signed payload uses RFC 8785 JSON Canonicalization Scheme
(JCS) to ensure deterministic byte-for-byte serialisation.

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

#### §22.2.4 Rotation Cadence {#section-22-2-4}

Nodes SHOULD rotate Ed25519 node signing keys on a cadence no longer than **365 days**. For capability issuer keys specifically, the SHOULD cadence is **90 days** (matching the maximum token lifetime). Operators MAY define shorter cadences. Cadence MUST be documented in the node's operational runbook and MAY be declared in the node's `/.well-known/stigmem` advertisement.

---

### §22.3 Audit Log Surface {#section-22-3}

#### §22.3.1 Required Event Types {#section-22-3-1}

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

#### §22.3.2 Ordering Guarantee {#section-22-3-2}

Audit log events MUST be totally ordered by a monotonically increasing sequence number within a single node. Events SHOULD include the node's HLC tick (§2.4) alongside the wall-clock timestamp to allow cross-node ordering reconstruction. The sequence MUST NOT reset across node restarts.

#### §22.3.3 Retention Contract {#section-22-3-3}

- Audit logs MUST be retained for a minimum of **90 days**.
- Operators SHOULD retain logs for **1 year** for forensic purposes.
- Logs MUST be stored in a medium that is append-only with respect to normal operational access (i.e., ordinary application processes MUST NOT be able to overwrite or delete log entries).
- Logs MUST NOT be stored exclusively in the same database that serves the production fact store unless that database provides an independent, append-only audit trail mechanism (e.g., PostgreSQL audit extension with restricted DDL access).

#### §22.3.4 Admin Export Shape {#section-22-3-4}

Admins MUST be able to export audit logs via the following HTTP route. The
export endpoint supports time-range filtering, event-type filtering, and
cursor-based pagination so that large exports can be consumed incrementally.
Events are returned in ascending sequence order to support idempotent
incremental ingestion by SIEM systems and compliance pipelines.

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

### §22.4 Per-Principal Quotas {#section-22-4}

#### §22.4.1 Model {#section-22-4-1}

Stigmem implements per-principal rate limiting using a **token-bucket** model.
Each `(principal, dimension)` pair maintains an independent token bucket. The
principal is the `actor_entity` URI derived from the authenticated caller's
capability token or API key. The bucket shape below describes the state
maintained per principal per quota dimension — `capacity` sets the burst
ceiling, `rate` controls sustained throughput, and `current` / `last_refill`
track the live token count.

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

#### §22.4.2 Quota Dimensions and Default Ceilings {#section-22-4-2}

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

#### §22.4.3 Backpressure Response Shape {#section-22-4-3}

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

### §22.5 Replay Protection {#section-22-5}

#### §22.5.1 Scope {#section-22-5-1}

This section extends §19.3.5 (capability token nonce) with normative clock-skew bounds and a unified replay protection model applicable to both capability tokens and federation handshake messages.

#### §22.5.2 Nonce and Timestamp Window {#section-22-5-2}

1. Every capability token MUST include a `nonce` of 32 cryptographically random bytes (§19.3.5). Every federation handshake message MUST include an independent `nonce` of 32 cryptographically random bytes.
2. The **timestamp acceptance window** is ± **5 minutes** from the verifier's local clock. Tokens or messages with an `issued_at` timestamp outside this window MUST be rejected with a `timestamp_out_of_window` error, even if the nonce is fresh.
3. The **nonce cache** MUST retain seen nonces for at least the **duration of the acceptance window plus the maximum token lifetime** (5 minutes + 90 days for capability tokens; 5 minutes + session duration for handshake messages). Implementations MUST NOT prune nonces from the cache before this window elapses.
4. Nonces MUST be stored in a persistent cache (survives node restarts within the retention window). An in-memory-only nonce cache MUST NOT be used in production; a brief restart MUST NOT create a replay window.

#### §22.5.3 Clock-Skew Bounds {#section-22-5-3}

| Scenario | Bound | Behaviour on violation |
|---|---|---|
| `issued_at` > verifier clock + 5 min | Future-dated | Reject: `timestamp_future_dated` |
| `issued_at` < verifier clock − 5 min | Stale | Reject: `timestamp_stale` |
| `expiry` < verifier clock | Expired | Reject: `token_expired` |
| `expiry` > `issued_at` + 90 days | Excessive lifetime | Reject: `token_lifetime_exceeded` |

Nodes MUST synchronise their system clocks via NTP (or equivalent). Operators SHOULD configure alerts if clock drift exceeds 30 seconds.

#### §22.5.4 Error Codes {#section-22-5-4}

| HTTP | Error code | Condition |
|---|---|---|
| 401 | `timestamp_future_dated` | `issued_at` more than 5 minutes in the future |
| 401 | `timestamp_stale` | `issued_at` more than 5 minutes in the past |
| 401 | `token_expired` | Token `expiry` has passed |
| 401 | `token_lifetime_exceeded` | Token `expiry` − `issued_at` > 90 days |
| 401 | `token_replay` | Nonce already seen within the retention window |

---

### §22.6 Container Baseline {#section-22-6}

#### §22.6.1 Scope {#section-22-6-1}

This section specifies the normative security posture for reference operator container images published by Eidetic-Labs. Third-party operators running Stigmem from source SHOULD adopt the same baseline.

#### §22.6.2 Distroless Image {#section-22-6-2}

1. Reference operator images MUST be built FROM a [distroless base](https://github.com/GoogleContainerTools/distroless) (e.g., `gcr.io/distroless/cc-debian12` or equivalent). Images MUST NOT include a shell (`sh`, `bash`) in the production layer.
2. Multi-stage builds MUST be used: build dependencies and tools MUST be confined to a builder stage and MUST NOT appear in the final image layer.
3. The image MUST contain only the Stigmem node binary and its minimal runtime dependencies (shared libraries, CA bundle, tzdata).

#### §22.6.3 Non-Root User {#section-22-6-3}

1. The container MUST run as a non-root user. The `Dockerfile` MUST include a `USER` directive setting a non-zero UID (SHOULD use UID 1000) in the final stage.
2. The container MUST NOT be run with `--privileged` or with `CAP_SYS_ADMIN`. Operators MUST NOT grant any Linux capabilities beyond the minimum required for the Stigmem node to bind its listen port (if < 1024, use `CAP_NET_BIND_SERVICE`; SHOULD use a port ≥ 1024 to avoid requiring any capability grant).
3. Kubernetes / container runtime manifests for reference deployments MUST include:
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     allowPrivilegeEscalation: false
   ```

#### §22.6.4 Read-Only Root Filesystem {#section-22-6-4}

1. The container's root filesystem MUST be mounted read-only (`readOnlyRootFilesystem: true` in Kubernetes). All writable state (database files, log buffers, temporary files) MUST be mounted as explicit volumes or `emptyDir` mounts.
2. Reference Helm charts MUST configure `readOnlyRootFilesystem: true` by default and MUST document which volumes require write access.

#### §22.6.5 Seccomp Profile {#section-22-6-5}

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

#### §22.6.6 Image Signing {#section-22-6-6}

Reference images MUST be signed using [Sigstore Cosign](https://github.com/sigstore/cosign) and the signature MUST be pushed to the same registry. Operators SHOULD verify the image signature before deployment using `cosign verify`. Image digests (not mutable tags) MUST be used in all reference Kubernetes manifests and Helm chart `values.yaml` defaults.

---

### §22.7 Transparency Log Own-Instance Decision Memo {#section-22-7}

#### §22.7.1 Purpose {#section-22-7-1}

§19.2.2 permits but does not require operating a self-hosted Rekor instance. This section provides normative decision criteria so that operators can determine whether self-hosting is appropriate, and records the Eidetic-Labs reference deployment position.

#### §22.7.2 Decision Criteria {#section-22-7-2}

An operator SHOULD self-host a Rekor instance if and only if ALL of the following criteria are met:

| Criterion | Rationale |
|---|---|
| The deployment operates in a private network without external internet egress | Public Rekor requires egress to `rekor.sigstore.dev` |
| Federation peers are all internal (no public or third-party peers) | Public log provides independent verifiability for external peers; private log acceptable for closed meshes |
| The operator can commit to operating the log with ≥ 99.9% uptime | Federation peers depend on the log for manifest verification in `trust_mode: strict` |
| The operator can provide independent accessibility of the log to all federation peers | §19.2.2 SHOULD: log SHOULD be independently accessible to all peers |
| A dedicated ops team or automation pipeline manages log key ceremonies | Rekor key rotation is operationally complex and MUST NOT be performed ad-hoc |

If any criterion is not met, the operator SHOULD use the public Rekor instance at `https://rekor.sigstore.dev` (or a hosted equivalent). Operators MUST NOT self-host without documented answers to each criterion in their ops runbook.

#### §22.7.3 Reference Deployment Position (Eidetic-Labs) {#section-22-7-3}

The Eidetic-Labs reference deployment uses the **public Rekor instance** (`https://rekor.sigstore.dev`). Criteria evaluation:

| Criterion | Status |
|---|---|
| Private network without egress | Not met — reference node targets public deployments |
| Internal-only federation | Not met — external federation is a core use-case |
| Ops commitment ≥ 99.9% uptime | Not evaluated — would require dedicated SRE investment |
| Independent peer accessibility | Not evaluated — moot given above |
| Dedicated key ceremony team | Not evaluated — moot given above |

**Decision: defer self-hosted Rekor to backlog.** A self-hosted Rekor instance for the Eidetic-Labs reference deployment does not meet the minimum decision criteria at this phase. A backlog issue SHOULD be filed when the following change conditions are met: (a) a private-network deployment tier is productised, or (b) a dedicated SRE function is established. Implementation of a self-hosted instance is explicitly out of scope for Phase 12.

#### §22.7.4 Configuration {#section-22-7-4}

Two environment variables configure the transparency log connection. The URL
points to the Rekor instance (public or self-hosted), and the public key is
pinned explicitly rather than discovered at runtime — this ensures the node
always verifies log entries against a known trust anchor even if the Rekor URL
is compromised. When using the public Rekor instance (default):

```
STIGMEM_TRANSPARENCY_LOG_URL=https://rekor.sigstore.dev
STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY=<base64-encoded ECDSA key from GET /api/v1/log>
```

When using a self-hosted instance, replace the above with the self-hosted instance URL and its corresponding public key. The `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST be pinned explicitly; key discovery via the URL alone MUST NOT be the sole trust anchor in production.

#### §22.7.5 Transparency Log Public-Key Rotation {#section-22-7-5}

The Sigstore/Rekor root signing key is subject to rotation (a root key rotation occurred in 2022). Operators pinning `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` MUST have a documented procedure for updating the pin.

1. Operators SHOULD subscribe to Sigstore transparency log key rotation announcements (the [sigstore-announce mailing list](https://groups.google.com/g/sigstore-announce) and the CT log transparency dashboard) and SHOULD update `STIGMEM_TRANSPARENCY_LOG_PUBLIC_KEY` within **30 days** of a published rotation.
2. A node MUST NOT treat a persistent transparency log key verification failure as a permanent misconfiguration without first checking whether a Rekor root key rotation has occurred. On repeated verification failures, the node SHOULD emit a `transparency_log_key_mismatch` audit log event and surface an operator alert before entering a degraded-verification state.

---

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §22.1.2.3 {#section-22-1-2-3}

### §22.1.2.4 {#section-22-1-2-4}

### §22.1.3.4 {#section-22-1-3-4}

### §22.1.3.5 {#section-22-1-3-5}

