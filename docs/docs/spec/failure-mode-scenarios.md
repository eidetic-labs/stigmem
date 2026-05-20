---
title: Spec-18 Conformance and Failure Modes
sidebar_label: Spec-18 Failure Modes
audience: Spec
description: "Spec-18-Conformance-and-Failure-Modes rendered entry point — split-brain, malicious peer, partial failure, and replay scenarios."
---

# Spec-18-Conformance-and-Failure-Modes \{#section-11\}

<p className="stigmem-meta"><span>3 min read</span><span>Spec contributor · Conformance test author</span><span>Acceptance gates</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-18-Conformance-and-Failure-Modes`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/18-conformance-and-failure-modes.md).
Acceptance test scenarios — split-brain, malicious peer, partial
failure, replay attack.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source.
:::

<div className="stigmem-keypoint">

**These scenarios are acceptance gates for the pre-reset design work.**

All four MUST pass before the phase is considered complete.

</div>

### §11.1 Split-Brain \{#section-11-1\}

**Setup:** Two nodes A and B are federated with `scope=public`. Both
are initially in sync (same public facts).

**Scenario:**

<ol className="stigmem-steps">
<li>Cut network connectivity between A and B (simulated partition).</li>
<li>Write fact <code>F_a</code> to node A: <code>(entity="stigmem://node-a/test/entity", relation="test:value", value="from-a", scope="public")</code>.</li>
<li>Write fact <code>F_b</code> to node B: <code>(entity="stigmem://node-a/test/entity", relation="test:value", value="from-b", scope="public")</code>.</li>
<li>Maintain partition for &gt;5 minutes. Both nodes continue accepting reads and writes.</li>
<li>Restore connectivity.</li>
<li>Allow replication to complete (pull cycle fires on both sides).</li>
</ol>

**Expected outcomes:**

<div className="stigmem-grid">

<div><h4>Both facts stored</h4><p>Both nodes store both <code>F_a</code> and <code>F_b</code>.</p></div>
<div><h4>Conflict fact exists</h4><p>A <code>stigmem:conflict:between</code> fact exists on both nodes (or at minimum on the node that ingested the second fact — the local node MUST detect the conflict on ingestion).</p></div>
<div><h4>Conflict surfaced</h4><p><code>GET /v1/conflicts?status=unresolved</code> returns the conflict on both nodes.</p></div>
<div><h4>Both contradicted</h4><p><code>GET /v1/facts?entity=stigmem://node-a/test/entity&relation=test:value&include_contradicted=true</code> returns both facts with <code>contradicted: true</code>.</p></div>
<div><h4>No silent discard</h4><p>No fact is silently discarded.</p></div>

</div>

### §11.2 Malicious Peer \{#section-11-2\}

**Setup:** Node A and Node B are federated. A third process
("attacker") obtains a valid peer token for the `node_b → node_a`
direction (simulating a compromised peer or MITM).

**Scenario:**

<ol className="stigmem-steps">
<li>Attacker attempts to push a fact with <code>scope="company"</code> to node A's <code>/v1/federation/facts/push</code>, where the PeerDeclaration only allows <code>["public"]</code>.</li>
<li>Attacker attempts to push a fact with <code>source="stigmem://node-c/user/alice"</code> (an entity not belonging to node B's declared namespace).</li>
<li>Attacker replays a previously-seen valid peer token (captured from an earlier legitimate exchange) after the nonce window expires. Then replays within the window.</li>
</ol>

**Expected outcomes:**

<div className="stigmem-fields">

<div>
<dt>Attack</dt>
<dt><span className="stigmem-fields__type">Response</span></dt>
<dd>Audit event</dd>
</div>

<div>
<dt>1 · Out-of-scope push</dt>
<dt><span className="stigmem-fields__type">HTTP 403, rejected</span></dt>
<dd><code>federation_audit</code>: <code>event_type="scope_violation"</code>.</dd>
</div>

<div>
<dt>2 · Forged source</dt>
<dt><span className="stigmem-fields__type">HTTP 403, rejected</span></dt>
<dd><code>federation_audit</code>: <code>event_type="rejected_fact"</code>, reason=<code>source_not_owned</code>.</dd>
</div>

<div>
<dt>3 · Token replay outside window</dt>
<dt><span className="stigmem-fields__type">token accepted (nonce evicted)</span></dt>
<dd>—</dd>
</div>

<div>
<dt>3 · Token replay inside window</dt>
<dt><span className="stigmem-fields__type">HTTP 401</span></dt>
<dd><code>federation_audit</code>: <code>event_type="replay_attempt"</code>. Node A's fact store is not corrupted.</dd>
</div>

</div>

### §11.3 Partial Failure (Peer Down Mid-Replication) \{#section-11-3\}

**Setup:** Node A (subscriber) is pulling from Node B (publisher).
Node B has 1000 public facts. A has pulled 500 so far; cursor is
stored.

**Scenario:**

<ol className="stigmem-steps">
<li>Node B crashes after returning facts 501–600 but before node A persists the cursor for that batch.</li>
<li>Node A attempts its next pull; node B is unreachable.</li>
<li>Node A continues serving read and write requests normally.</li>
<li>Node B restarts.</li>
<li>Node A's next pull cycle fires.</li>
</ol>

**Expected outcomes:**

<div className="stigmem-grid">

<div><h4>During peer-down</h4><p>Node A returns 503 or times out on the pull attempt; no crash; local reads/writes unaffected.</p></div>
<div><h4>After restart</h4><p>Node A resumes from cursor 500 (not 0, not 600). Facts 501–1000 are ingested. No duplicates created (idempotency check passes on facts 501–600 that may have been partially ingested).</p></div>
<div><h4>Final state</h4><p>Node A has all 1000 facts.</p></div>

</div>

### §11.4 Replay Attack \{#section-11-4\}

**Setup:** Node A and B are federated. A valid peer token `T` is
intercepted.

**Scenario:**

<ol className="stigmem-steps">
<li>Token <code>T</code> is used legitimately for a pull request by node B. Succeeds.</li>
<li>Token <code>T</code> is immediately replayed by an attacker. (Within nonce window.)</li>
<li>A new token <code>T2</code> is generated with the same nonce as <code>T</code> but a fresh <code>iat</code>/<code>exp</code>.</li>
<li>Token <code>T3</code> is generated with a past <code>exp</code> (already expired).</li>
</ol>

**Expected outcomes:**

<div className="stigmem-fields">

<div>
<dt>Step</dt>
<dt><span className="stigmem-fields__type">Response</span></dt>
<dd>Reason</dd>
</div>

<div>
<dt>1 · First legitimate use</dt>
<dt><span className="stigmem-fields__type">HTTP 200</span></dt>
<dd>Facts returned.</dd>
</div>

<div>
<dt>2 · Immediate replay of <code>T</code></dt>
<dt><span className="stigmem-fields__type">HTTP 401</span></dt>
<dd><code>error: "nonce_already_seen"</code>. Audit log entry.</dd>
</div>

<div>
<dt>3 · <code>T2</code> with duplicate nonce</dt>
<dt><span className="stigmem-fields__type">HTTP 401</span></dt>
<dd>The nonce cache matches on nonce value, not token identity.</dd>
</div>

<div>
<dt>4 · <code>T3</code> already expired</dt>
<dt><span className="stigmem-fields__type">HTTP 401</span></dt>
<dd><code>error: "token_expired"</code>.</dd>
</div>

</div>
