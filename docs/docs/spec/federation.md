---
title: Spec-05 Federation Trust
sidebar_label: Spec-05 Federation Trust
audience: Spec
description: "Spec-05-Federation-Trust rendered entry point — peer declaration, negotiation, replication, and federation scope rules."
---

# Spec-05-Federation-Trust \{#section-6\}

<p className="stigmem-meta"><span>8 min read</span><span>Spec contributor · Node operator</span><span>Peer handshake + replication</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-05-Federation-Trust`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/05-federation-trust.md).
Peer handshake, pull replication, scope enforcement, conflict
semantics, backpressure.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source.
:::

<div className="stigmem-keypoint">

**Garden isolation invariant.**

Facts with <code>garden_id</code> set MUST NOT appear in federation
pull or push payloads. Nodes MUST filter them before sending. This
invariant is enforced independently of scope — a garden-tagged
<code>public</code> fact is still garden-isolated from the federation
perspective.

</div>

Legacy §6 anchors are retained for existing links while the
maintained federation-trust prose lives in
`Spec-05-Federation-Trust`.

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

> **pre-reset status:** §6 promoted from RFC stub to concrete spec. §6.1–§6.6 are stable (normative). §6.7–§6.8 are new the pre-reset spec draft sections covering N-node backpressure and scope propagation invariants.

</details>

### §6.1 Peer declaration \{#section-6-1\}

Two nodes federate when operators on both sides exchange a signed
**PeerDeclaration**. The declaration serves three purposes:

<div className="stigmem-grid">

<div><h4>Identify the peer</h4><p>Via <code>node_id</code> and <code>node_url</code>.</p></div>
<div><h4>Establish a cryptographic trust root</h4><p>Via <code>federation_pubkey</code>.</p></div>
<div><h4>Set the scope boundary</h4><p>Via <code>allowed_scopes</code> — what data may flow between the two nodes.</p></div>

</div>

The signature over the canonical JSON body ensures that a declaration
cannot be replayed or tampered with in transit.

```
PeerDeclaration {
  node_url:          string       // reachable HTTPS base URL of the declaring node
  node_id:           URI          // stable identity URI for the node
  federation_pubkey: string       // base64url Ed25519 public key for token verification
  allowed_scopes:    FactScope[]  // which scopes this node is willing to share with the peer
  rate_limit:        RateLimit?   // optional: max facts/second this peer may pull
  signed_at:         ISO 8601 UTC
  declaration_sig:   string       // Ed25519 sig over canonical JSON of the above fields
}

RateLimit {
  facts_per_second: integer
  burst:            integer
}
```

The `rate_limit` field is optional. The `RateLimit` uses a
token-bucket model: `facts_per_second` is the refill rate; `burst`
is the bucket depth.

**Canonical JSON** for signing: fields in lexicographic key order, no
whitespace, UTF-8.

**Key lifecycle:**

<div className="stigmem-grid">

<div><h4>Rotate weekly at most</h4><p>Nodes SHOULD rotate their federation keypair no more often than weekly to avoid verification races during rotation.</p></div>
<div><h4>24-hour dual-trust window</h4><p>During rotation, nodes MUST keep the old key active for 24 hours and publish the new key at <code>/.well-known/stigmem</code>. Peers that fail token verification SHOULD re-fetch the well-known document once before treating it as an attack.</p></div>

</div>

### §6.2 Capability negotiation — pre-reset required \{#section-6-2\}

<div className="stigmem-keypoint">

**pre-reset open question §8.4 resolved.**

Capability negotiation is now required for all nodes that support
federation, based on implementation experience from two pre-reset-era
adapters.

</div>

After peer registration, nodes MUST exchange capability advertisements
before the first replication pull. Without this exchange, a peer
cannot distinguish relations it can meaningfully process from opaque
forwarded data — leading to silent contradiction storms.

```
CapabilityAd {
  relations_understood:    string[]
  decay_policies:          { relation: string, policy: string }[]
  contradiction_overrides: { relation: string, policy: "latest" | "highest_confidence" | "caller_decides" }[]
  federation_mode:         "push" | "pull" | "both"
  push_interval_s:         integer?   // if mode includes push
  pull_interval_s:         integer?   // recommended pull cadence; advisory only
}
```

**Exchange route:** `GET /v1/federation/peers/:peer_id/capabilities`
returns the remote node's capability advertisement. A node MUST
respond to this route if it supports federation. A node MAY cache
the remote capability advertisement for up to 1 hour.

**Required behavior:**

<ol className="stigmem-steps">
<li>A node MUST advertise at minimum: <code>federation_mode</code> and <code>relations_understood</code>.</li>
<li>A node that receives a capability request MUST respond within 10 seconds or the requesting node MAY treat it as <code>{`{ federation_mode: "pull", relations_understood: [] }`}</code>.</li>
<li>Unknown fields in a received <code>CapabilityAd</code> MUST be ignored (forward compatibility).</li>
</ol>

**Why now required:** the pre-reset line shipped the Paperclip and
OpenClaw adapters, both of which use distinct relation namespaces
(`paperclip:`, `intent:`). Without capability exchange, a federated
peer cannot distinguish relations it understands from opaque
forwarded data.

### §6.3 Replication protocol \{#section-6-3\}

#### Pull cadence

The **subscriber** (the node that wants facts) polls the
**publisher**:

```
loop every pull_interval_s (default: 30s):
  cursor = load_cursor(peer_id) or null
  resp   = GET {peer.node_url}/v1/federation/facts?scope=public&cursor={cursor}
           Authorization: Bearer {fresh_peer_token}
  for fact in resp.facts:
    ingest_fact(fact)
  save_cursor(peer_id, resp.cursor)
```

**Pull interval:** Default 30 seconds. Configurable via
`STIGMEM_FEDERATION_PULL_INTERVAL_S`. The publisher's capability
advertisement MAY suggest a different interval; the subscriber treats
this as advisory.

**Back-pressure:** If the publisher returns 429, the subscriber MUST
back off exponentially with jitter. Max backoff: 5 minutes. See §6.7
for N-node cascade backpressure patterns.

#### Idempotent ingestion

The ingestion handler MUST be idempotent: receiving the same fact
twice produces exactly one stored record. The existence check uses
the fact's UUID, not its content.

```python
def ingest_fact(fact):
    if facts.exists(id=fact.id):
        return  # no-op; do not update, do not create duplicate
    assert_fact(fact)
    assert_received_from_meta(fact.id, sender_node_id)
    detect_contradiction(fact)  # see §3.3
```

The `stigmem:received_from` meta-fact MUST be written atomically with
the fact.

#### HLC synchronization

When ingesting a federated fact, the receiving node MUST advance its
own HLC:

```
local_hlc = max(local_hlc.wall_ms, fact.hlc.wall_ms)
```

### §6.4 Permission enforcement \{#section-6-4\}

**Scope boundary rules (strict):**

<div className="stigmem-fields">

<div>
<dt>Fact scope</dt>
<dt><span className="stigmem-fields__type">Federatable?</span></dt>
<dd>Conditions</dd>
</div>

<div>
<dt><code>local</code></dt>
<dt><span className="stigmem-fields__type">Never</span></dt>
<dd>Nodes MUST NOT expose <code>local</code> facts on federation endpoints.</dd>
</div>

<div>
<dt><code>team</code></dt>
<dt><span className="stigmem-fields__type">Never</span></dt>
<dd>Unless operator sets <code>STIGMEM_FEDERATION_ALLOW_TEAM=true</code> (audit-logged).</dd>
</div>

<div>
<dt><code>company</code></dt>
<dt><span className="stigmem-fields__type">Conditional</span></dt>
<dd>Only if the active PeerDeclaration's <code>allowed_scopes</code> includes <code>"company"</code>.</dd>
</div>

<div>
<dt><code>public</code></dt>
<dt><span className="stigmem-fields__type">Yes</span></dt>
<dd>To any active peer.</dd>
</div>

</div>

**Inbound enforcement:**

<ol className="stigmem-steps">
<li>Nodes MUST reject any fact whose scope is not permitted by the peer's PeerDeclaration.</li>
<li>Nodes MUST reject any fact whose <code>source</code> does not match the peer's <code>node_id</code> or a sub-entity explicitly delegated by the peer.</li>
</ol>

**Audit log:** All rejected inbound facts MUST be recorded with
`peer_id`, `fact_id`, rejection reason, timestamp. Accessible at
`GET /v1/federation/audit?peer_id=<id>`.

### §6.5 Conflict-first-class semantics \{#section-6-5\}

When a federated fact conflicts with a locally-held fact (same
entity/relation/scope, different non-zero-confidence values), the
receiving node MUST:

<ol className="stigmem-steps">
<li>Store both facts.</li>
<li>Assert the system-generated <code>stigmem:conflict:between</code> fact (§3.3).</li>
<li>Return both facts when queried, with <code>contradicted: true</code>.</li>
<li>NOT silently prefer either fact without explicit resolution.</li>
</ol>

<div className="stigmem-keypoint">

**Cross-node conflicts are expected.**

The protocol treats them as information, not errors. Nodes SHOULD
surface unresolved conflicts in monitoring/alerting. Contradiction
entity namespace: all conflict entities use
<code>stigmem:conflict:&lt;uuid&gt;</code>. These entities MUST NOT
be federated (they are local accounting artifacts).

</div>

### §6.6 Security invariants \{#section-6-6\}

The following invariants MUST hold at all times.

<div className="stigmem-fields">

<div>
<dt>Invariant</dt>
<dt><span className="stigmem-fields__type">Mechanism</span></dt>
<dd>Effect</dd>
</div>

<div>
<dt>1 · Scope non-escalation</dt>
<dt><span className="stigmem-fields__type">PeerDeclaration check</span></dt>
<dd>An inbound fact may not raise its own scope. A fact arriving with <code>scope="company"</code> on a <code>["public"]</code>-only peer MUST be rejected.</dd>
</div>

<div>
<dt>2 · Provenance non-forgery</dt>
<dt><span className="stigmem-fields__type">source validation</span></dt>
<dd>A peer MUST NOT assert facts with <code>source</code> values it does not own. The receiving node validates <code>source</code> against the sender's declared <code>node_id</code> and any explicitly delegated entity namespaces.</dd>
</div>

<div>
<dt>3 · Replay resistance</dt>
<dt><span className="stigmem-fields__type">nonce cache + <code>exp</code></span></dt>
<dd>Peer tokens carry a <code>nonce</code> and <code>exp</code>. Receiving node MUST maintain a nonce cache for the duration of the token's validity window (max 1 hour). Tokens with already-seen nonces MUST be rejected with 401.</dd>
</div>

<div>
<dt>4 · Partition safety</dt>
<dt><span className="stigmem-fields__type">cursor-resume</span></dt>
<dd>During a network partition, each node MUST continue accepting local reads and writes without degradation. Replication resumes from the last persisted cursor when connectivity is restored.</dd>
</div>

<div>
<dt>5 · No silent data loss</dt>
<dt><span className="stigmem-fields__type">conflict surfacing</span></dt>
<dd>A node MUST NOT discard facts during reconciliation after a partition. All divergent writes MUST be ingested; contradictions are surfaced to callers.</dd>
</div>

</div>

:::note Draft sections — §6.7 and §6.8
Multi-node relay topologies (3+ nodes) are supported but §6.7
(backpressure) and §6.8 (scope propagation) are draft specifications
not yet covered by the conformance test suite. Test your topology
before relying on it in production. Scope propagation behavior in
relay chains will be formally validated in v2.1.
:::

### §6.7 N-node backpressure patterns — pre-reset draft \{#section-6-7\}

<div className="stigmem-keypoint">

**Pre-reset status.**

These patterns were identified during the pre-reset spec 4-node local
topology work. They are draft guidance, pending validation in the D1
correctness test suite. Promotion to normative is a the pre-reset
spec target.

</div>

In topologies with N > 2 nodes, backpressure from one publisher can
cascade through relay nodes.

#### §6.7.1 The relay cascade problem \{#section-6-7-1\}

Consider a 4-node topology: A ← B ← C ← D.

If node A emits a burst of 10,000 public facts within a short window:

<ol className="stigmem-steps">
<li>B receives the burst and its ingest queue grows.</li>
<li>C is pulling from B at the normal cadence. B may return 429 if its write path is saturated (disk I/O, WAL flush, etc.).</li>
<li>C backs off on B, but D continues pulling from C at the normal rate.</li>
<li>C now has a growing lag behind B AND is serving D at full pull rate.</li>
</ol>

Without relay-aware backpressure, C can fall further and further
behind B while continuing to serve D with stale data, without any
signal to D that it is receiving lagged facts.

#### §6.7.2 Recommended relay behavior (draft) \{#section-6-7-2\}

Nodes that are simultaneously a subscriber and publisher (relay
nodes) SHOULD:

<div className="stigmem-fields">

<div>
<dt>Behavior</dt>
<dt><span className="stigmem-fields__type">Trigger</span></dt>
<dd>Action</dd>
</div>

<div>
<dt>1 · Propagate backpressure signals</dt>
<dt><span className="stigmem-fields__type">lag &gt; warning threshold</span></dt>
<dd>Include <code>X-Stigmem-Replication-Lag: &lt;lag_ms&gt;</code> response header on pull responses to subscribers. Default warning: 60,000ms.</dd>
</div>

<div>
<dt>2 · Apply admission throttle</dt>
<dt><span className="stigmem-fields__type">lag &gt; hard threshold</span></dt>
<dd>MAY return HTTP 503 with <code>{`{ "error": "relay_lag_exceeded", "lag_ms": ..., "retry_after_s": ... }`}</code>. Default hard: 5 minutes. <code>retry_after_s</code> SHOULD be proportional to lag.</dd>
</div>

<div>
<dt>3 · Expose lag in well-known</dt>
<dt><span className="stigmem-fields__type">always when relay</span></dt>
<dd>Include <code>replication_lag_ms</code> field in <code>/.well-known/stigmem</code> (max lag across all inbound peers).</dd>
</div>

</div>

#### §6.7.3 Backpressure conformance (draft) \{#section-6-7-3\}

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS</code></dt>
<dt><span className="stigmem-fields__type"><code>60000</code></span></dt>
<dd>Lag threshold for warning header.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_LAG_HARD_MS</code></dt>
<dt><span className="stigmem-fields__type"><code>300000</code></span></dt>
<dd>Lag threshold for 503 throttle.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_RELAY_ENABLED</code></dt>
<dt><span className="stigmem-fields__type"><code>true</code></span></dt>
<dd>Set <code>false</code> to disable relay behavior (leaf nodes).</dd>
</div>

</div>

Conformance tests for relay backpressure will be added to the 4-node
topology test suite (`node/tests/federation/test_4node_federation.py`)
before the pre-reset spec stabilization.

### §6.8 Scope propagation invariants — pre-reset draft \{#section-6-8\}

<div className="stigmem-keypoint">

**Pre-reset status.**

These invariants close the transitive scope escalation gap identified
during the pre-reset spec 4-node topology work. Draft; to be
validated against correctness tests before promotion to normative.

</div>

In a 2-node topology, scope enforcement is bilateral and
straightforward. In an N-node topology, a fact can travel through
multiple hops. The following invariants ensure that scope boundaries
set by the originating node are respected end-to-end.

#### §6.8.1 Transitive scope non-escalation \{#section-6-8-1\}

<div className="stigmem-keypoint">

**Invariant: a fact's scope MUST NOT be escalated at any relay hop.**

</div>

A relay node (node B, receiving from node A and serving node C) MUST
NOT:

<div className="stigmem-grid">

<div><h4>Widen scope to peer</h4><p>Return a fact with <code>scope="company"</code> to node C if node A's PeerDeclaration with node B restricts to <code>allowed_scopes=["public"]</code>.</p></div>
<div><h4>Re-grant via transitivity</h4><p>Infer that because node C is permitted <code>company</code> scope with node B, node B can re-federate <code>company</code> facts it received from node A under a <code>["public"]</code>-only declaration.</p></div>

</div>

**Implementation requirement:** Nodes MUST tag every ingested
federated fact with its source peer's declaration scope at ingest
time. When serving a pull request, a relay node MUST intersect the
fact's `origin_allowed_scopes` with the current peer's
`allowed_scopes`. Only facts where
`fact.scope ∈ origin_allowed_scopes ∩ current_peer.allowed_scopes`
are returned.

The `received_from` meta-fact records the immediate sender, not the
origin. Relay nodes MUST also store `origin_node_id` and
`origin_allowed_scopes` per-fact when ingesting federated facts.
These fields are internal to the node and MUST NOT be re-replicated.

#### §6.8.2 Re-federation restriction for company-scoped facts \{#section-6-8-2\}

<div className="stigmem-keypoint">

**the pre-reset spec resolves §8.5 (pre-reset open question).**

A node that receives a <code>company</code>-scoped fact from peer A
(where peer A's declaration explicitly includes <code>"company"</code>
in <code>allowed_scopes</code>) MUST NOT re-federate that fact to any
third node C, regardless of what node C's PeerDeclaration allows.

</div>

**Rationale:** `company`-scoped facts represent internal knowledge of
the originating organization. The originating node's explicit
`allowed_scopes=["company"]` declaration is an authorization grant
to a specific peer, not a grant to that peer's downstream federation
network.

**Implementation requirement:** `company`-scoped ingested facts MUST
be tagged `re_federation_blocked=true` at ingest. Federation pull
responses MUST exclude facts with `re_federation_blocked=true`.

**Exception:** If the originating node explicitly sets
`STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=true` (default
`false`), the re-federation restriction is lifted for that node's
outbound `company` facts. This flag is operator-level and MUST be
logged to the federation audit log each time it is applied.

#### §6.8.3 Scope propagation edge cases \{#section-6-8-3\}

The following edge cases were identified during the pre-reset spec
4-node topology testing.

<div className="stigmem-fields">

<div>
<dt>Edge case</dt>
<dt><span className="stigmem-fields__type">Requirement</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt>Mixed-scope batch push</dt>
<dt><span className="stigmem-fields__type">per-fact, not all-or-nothing</span></dt>
<dd>A push payload may contain facts of multiple scopes. Nodes MUST enforce per-fact scope checking within a batch; a scope violation on one fact MUST NOT cause the entire batch to be rejected. Response's <code>rejected</code> count and <code>errors</code> array MUST enumerate each rejected fact.</dd>
</div>

<div>
<dt>Scope of contradiction meta-facts</dt>
<dt><span className="stigmem-fields__type">narrower scope wins</span></dt>
<dd>The <code>stigmem:conflict:between</code> meta-fact MUST inherit the scope of the conflicting facts. If a <code>public</code> fact from a peer conflicts with a local <code>company</code> fact, the conflict record is <code>company</code>-scoped.</dd>
</div>

<div>
<dt><code>team</code>-scoped fact from misbehaving peer</dt>
<dt><span className="stigmem-fields__type">PeerDeclaration is authoritative</span></dt>
<dd>If a peer sends a <code>team</code>-scoped fact and the PeerDeclaration does not include <code>"team"</code>, the fact MUST be rejected with HTTP 403 and logged as <code>event_type="scope_violation"</code>. This applies even if <code>STIGMEM_FEDERATION_ALLOW_TEAM=true</code> is set locally — the PeerDeclaration is the authoritative grant.</dd>
</div>

</div>
