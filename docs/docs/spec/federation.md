---
title: §6. Federation
sidebar_label: §6 Federation
audience: Spec
description: "Stigmem spec section 6 — Peer handshake, pull replication, scope enforcement, conflict semantics, backpressure."
---

# §6. Federation {#section-6}

**Status:** Stable (the pre-reset spec N-node)

Peer handshake, pull replication, scope enforcement, conflict semantics, backpressure.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Garden isolation invariant:** Facts with `garden_id` set MUST NOT appear in federation pull or push payloads. Nodes MUST filter them before sending. This invariant is enforced independently of scope — a garden-tagged `public` fact is still garden-isolated from the federation perspective.

*All other §6 content unchanged from the pre-reset spec.*

---

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

> **pre-reset status:** §6 promoted from RFC stub to concrete spec. §6.1–§6.6 are stable (normative). §6.7–§6.8 are new the pre-reset spec draft sections covering N-node backpressure and scope propagation invariants.

</details>

### §6.1 Peer Declaration {#section-6-1}

Two nodes federate when operators on both sides exchange a signed
**PeerDeclaration**. The declaration serves three purposes: it identifies the
peer (via `node_id` and `node_url`), establishes a cryptographic trust root
(via `federation_pubkey`), and sets the scope boundary for what data may flow
between the two nodes (via `allowed_scopes`). The signature over the canonical
JSON body ensures that a declaration cannot be replayed or tampered with in
transit — the receiving node verifies it against the sender's published key
before activating the relationship.

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

The `rate_limit` field is optional because most deployments do not need
per-peer throttling — it exists for operators who federate with high-volume
peers and want to cap inbound load without rejecting the relationship entirely.
The `RateLimit` uses a token-bucket model: `facts_per_second` is the refill
rate; `burst` is the bucket depth.

**Canonical JSON** for signing: fields in lexicographic key order, no whitespace, UTF-8.

**Key lifecycle:**
- Nodes SHOULD rotate their federation keypair no more often than weekly to avoid
  verification races during rotation.
- During rotation, nodes MUST keep the old key active for 24 hours and publish the
  new key at `/.well-known/stigmem`. Peers that fail token verification SHOULD
  re-fetch the well-known document once before treating it as an attack.

### §6.2 Capability Negotiation — pre-reset Required {#section-6-2}

**pre-reset open question §8.4 resolved.** Capability negotiation is now required for all
nodes that support federation, based on implementation experience from two pre-reset-era adapters.

After peer registration, nodes MUST exchange capability advertisements before the first
replication pull. The advertisement tells the peer what relation namespaces the
node understands, how it handles conflicts on those relations, and which
replication mode it supports. Without this exchange, a peer cannot distinguish
relations it can meaningfully process from opaque forwarded data — leading to
silent contradiction storms when two nodes disagree on conflict resolution
semantics for a shared relation.

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

**Exchange route:** `GET /v1/federation/peers/:peer_id/capabilities` returns the
remote node's capability advertisement. A node MUST respond to this route if it
supports federation. A node MAY cache the remote capability advertisement for up to
1 hour.

**Required behavior:**
- A node MUST advertise at minimum: `federation_mode` and `relations_understood`.
- A node that receives a capability request MUST respond within 10 seconds or the
  requesting node MAY treat it as `{ federation_mode: "pull", relations_understood: [] }`.
- Unknown fields in a received `CapabilityAd` MUST be ignored (forward compatibility).

**Why now required:** the pre-reset line shipped the Paperclip and OpenClaw adapters, both of
which use distinct relation namespaces (`paperclip:`, `intent:`). Without capability
exchange, a federated peer cannot distinguish relations it understands from opaque
forwarded data — leading to silent contradiction storms on relations the peer cannot
interpret. Capability advertisement gives both sides a shared understanding of what
to replicate and how to resolve conflicts on those relations.

### §6.3 Replication Protocol {#section-6-3}

#### Pull cadence

The **subscriber** (the node that wants facts) polls the **publisher**:

```
loop every pull_interval_s (default: 30s):
  cursor = load_cursor(peer_id) or null
  resp   = GET {peer.node_url}/v1/federation/facts?scope=public&cursor={cursor}
           Authorization: Bearer {fresh_peer_token}
  for fact in resp.facts:
    ingest_fact(fact)
  save_cursor(peer_id, resp.cursor)
```

**Pull interval:** Default 30 seconds. Configurable via `STIGMEM_FEDERATION_PULL_INTERVAL_S`.
The publisher's capability advertisement MAY suggest a different interval; the
subscriber treats this as advisory.

**Back-pressure:** If the publisher returns 429, the subscriber MUST back off
exponentially with jitter. Max backoff: 5 minutes. See §6.7 for N-node cascade
backpressure patterns.

#### Idempotent ingestion

The ingestion handler MUST be idempotent: receiving the same fact twice (whether
from the same peer or a different one in a multi-hop topology) produces exactly
one stored record. The existence check uses the fact's UUID, not its content,
because two distinct facts could contain the same assertion at different times.
A `stigmem:received_from` meta-fact is written alongside the main fact to
preserve provenance — this is what the federation audit endpoint (§5.8) queries
to answer "which peer delivered fact X?"

```python
def ingest_fact(fact):
    if facts.exists(id=fact.id):
        return  # no-op; do not update, do not create duplicate
    assert_fact(fact)
    assert_received_from_meta(fact.id, sender_node_id)
    detect_contradiction(fact)  # see §3.3
```

The `stigmem:received_from` meta-fact MUST be written atomically with the fact.

#### HLC synchronization

When ingesting a federated fact, the receiving node MUST advance its own HLC:
```
local_hlc = max(local_hlc.wall_ms, fact.hlc.wall_ms)
```

### §6.4 Permission Enforcement {#section-6-4}

**Scope boundary rules (strict):**

| Fact scope  | Federatable?                                                                |
|-------------|-----------------------------------------------------------------------------|
| `local`     | Never. Nodes MUST NOT expose `local` facts on federation endpoints.          |
| `team`      | Never, unless operator sets `STIGMEM_FEDERATION_ALLOW_TEAM=true` (audit-logged). |
| `company`   | Only if the active PeerDeclaration's `allowed_scopes` includes `"company"`. |
| `public`    | Yes, to any active peer.                                                     |

**Inbound enforcement:**
- Nodes MUST reject any fact whose scope is not permitted by the peer's PeerDeclaration.
- Nodes MUST reject any fact whose `source` does not match the peer's `node_id` or a
  sub-entity explicitly delegated by the peer (i.e., a fact from `peer-b` should not claim
  `source="stigmem://node-c/user/alice"` unless `peer-b`'s declaration covers that entity space).

**Audit log:** All rejected inbound facts MUST be recorded with: peer_id, fact_id,
rejection reason, timestamp. Accessible at `GET /v1/federation/audit?peer_id=<id>`.

### §6.5 Conflict-First-Class Semantics {#section-6-5}

When a federated fact conflicts with a locally-held fact (same entity/relation/scope,
different non-zero-confidence values), the receiving node MUST:

1. Store both facts.
2. Assert the system-generated `stigmem:conflict:between` fact (§3.3).
3. Return both facts when queried, with `contradicted: true`.
4. NOT silently prefer either fact without explicit resolution.

**Cross-node conflicts are expected.** The protocol treats them as information, not errors.
Nodes SHOULD surface unresolved conflicts in monitoring/alerting.

**Contradiction entity namespace:** All conflict entities use `stigmem:conflict:<uuid>`.
These entities MUST NOT be federated (they are local accounting artifacts).

### §6.6 Security Invariants {#section-6-6}

The following invariants MUST hold at all times:

1. **Scope non-escalation.** An inbound fact may not raise its own scope. A fact
   arriving with `scope="public"` on a wire that the PeerDeclaration restricts to
   `["public"]` is valid. A fact arriving with `scope="company"` on a `["public"]`-only
   peer MUST be rejected.

2. **Provenance non-forgery.** A peer MUST NOT assert facts with `source` values it
   does not own. The receiving node validates `source` against the sender's declared
   `node_id` and any explicitly delegated entity namespaces.

3. **Replay resistance.** Peer tokens carry a `nonce` and `exp`. The receiving node
   MUST maintain a nonce cache for the duration of the token's validity window (max 1
   hour). Tokens with already-seen nonces MUST be rejected with 401.

4. **Partition safety.** During a network partition, each node MUST continue accepting
   local reads and writes without degradation. Replication resumes from the last
   persisted cursor when connectivity is restored.

5. **No silent data loss.** A node MUST NOT discard facts during reconciliation after
   a partition. All divergent writes MUST be ingested; contradictions are surfaced to
   callers.

:::note Draft sections — §6.7 and §6.8
Multi-node relay topologies (3+ nodes) are supported but §6.7 (backpressure) and §6.8 (scope propagation) are draft specifications not yet covered by the conformance test suite. Test your topology before relying on it in production. Scope propagation behavior in relay chains will be formally validated in v2.1.
:::

### §6.7 N-node Backpressure Patterns — the pre-reset spec Draft {#section-6-7}

> **Pre-reset status:** These patterns were identified during the pre-reset spec 4-node local topology
> work. They are draft guidance, pending validation in the D1 correctness test suite.
> Promotion to normative is a the pre-reset spec target.

In topologies with N > 2 nodes, backpressure from one publisher can cascade through
relay nodes (nodes that both ingest from peers and are themselves pulled from).

#### §6.7.1 The relay cascade problem {#section-6-7-1}

Consider a 4-node topology: A ← B ← C ← D (each node pulls from the next).

If node A emits a burst of 10,000 public facts within a short window:
1. B receives the burst and its ingest queue grows.
2. C is pulling from B at the normal cadence. B may return 429 if its write
   path is saturated (disk I/O, WAL flush, etc.).
3. C backs off on B, but D continues pulling from C at the normal rate.
4. C now has a growing lag behind B AND is serving D at full pull rate.

Without relay-aware backpressure, C can fall further and further behind B while
continuing to serve D with stale data, without any signal to D that it is receiving
lagged facts.

#### §6.7.2 Recommended relay behavior (draft) {#section-6-7-2}

Nodes that are simultaneously a subscriber and publisher (relay nodes) SHOULD:

1. **Propagate backpressure signals.** If a relay node's inbound replication lag
   exceeds `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` (default: 60,000 ms), it SHOULD
   include a `X-Stigmem-Replication-Lag: <lag_ms>` response header on pull responses
   to its own subscribers. Subscribers MAY use this to slow their pull cadence.

2. **Apply admission throttle.** If the relay node's inbound lag exceeds
   `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` (default: 300,000 ms — 5 minutes), the node
   MAY return HTTP 503 on pull requests from its own subscribers with body:
   ```json
   { "error": "relay_lag_exceeded", "lag_ms": <integer>, "retry_after_s": <integer> }
   ```
   The `retry_after_s` SHOULD be proportional to the lag: `lag_ms / 1000`.

3. **Expose lag in well-known.** Nodes SHOULD include a `replication_lag_ms` field in
   `/.well-known/stigmem` (value: max lag across all inbound peers; omit if not a relay
   or if lag is within normal bounds). This allows topology health tools to detect
   degraded relay nodes without polling pull endpoints.

#### §6.7.3 Backpressure conformance (draft) {#section-6-7-3}

These env vars configure relay behavior:

| Variable | Default | Description |
|---|---|---|
| `STIGMEM_FEDERATION_RELAY_LAG_WARNING_MS` | `60000` | Lag threshold for warning header |
| `STIGMEM_FEDERATION_RELAY_LAG_HARD_MS` | `300000` | Lag threshold for 503 throttle |
| `STIGMEM_FEDERATION_RELAY_ENABLED` | `true` | Set `false` to disable relay behavior (leaf nodes) |

Conformance tests for relay backpressure will be added to the 4-node topology test
suite (`stigmem/node/tests/test_federation_4node.py`) before the pre-reset spec stabilization.

### §6.8 Scope Propagation Invariants — the pre-reset spec Draft {#section-6-8}

> **Pre-reset status:** These invariants close the transitive scope escalation gap identified
> during the pre-reset spec 4-node topology work. Draft; to be validated against correctness tests
> before promotion to normative.

In a 2-node topology, scope enforcement is bilateral and straightforward. In an N-node
topology, a fact can travel through multiple hops. The following invariants ensure that
scope boundaries set by the originating node are respected end-to-end.

#### §6.8.1 Transitive scope non-escalation {#section-6-8-1}

**Invariant:** A fact's scope MUST NOT be escalated at any relay hop.

A relay node (node B, receiving from node A and serving node C) MUST NOT:
- Return a fact with `scope="company"` to node C if node A's PeerDeclaration with
  node B restricts to `allowed_scopes=["public"]`.
- Infer that because node C is permitted `company` scope with node B, node B can
  re-federate `company` facts it received from node A under a `["public"]`-only declaration.

**Implementation requirement:** Nodes MUST tag every ingested federated fact with its
**source peer's declaration scope** at ingest time. When serving a pull request, a
relay node MUST intersect the fact's `origin_allowed_scopes` (the scope permitted when
the fact first entered the federation) with the current peer's `allowed_scopes`. Only
facts where `fact.scope ∈ origin_allowed_scopes ∩ current_peer.allowed_scopes` are
returned.

The `received_from` meta-fact (§3.1) records the immediate sender, not the origin.
Relay nodes MUST also store `origin_node_id` and `origin_allowed_scopes` per-fact when
ingesting federated facts. These fields are internal to the node and MUST NOT be
re-replicated.

#### §6.8.2 Re-federation restriction for company-scoped facts {#section-6-8-2}

**the pre-reset spec resolves §8.5 (pre-reset open question).** The following rule is normative as of the pre-reset spec:

A node that receives a `company`-scoped fact from peer A (where peer A's declaration
explicitly includes `"company"` in `allowed_scopes`) MUST NOT re-federate that fact
to any third node C, regardless of what node C's PeerDeclaration allows.

**Rationale:** `company`-scoped facts represent internal knowledge of the originating
organization. The originating node's explicit `allowed_scopes=["company"]` declaration
is an authorization grant to a specific peer, not a grant to that peer's downstream
federation network.

**Implementation requirement:** `company`-scoped ingested facts MUST be tagged
`re_federation_blocked=true` at ingest. Federation pull responses MUST exclude facts
with `re_federation_blocked=true`.

**Exception:** If the originating node explicitly sets
`STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=true` (default `false`), the
re-federation restriction is lifted for that node's outbound `company` facts. This
flag is operator-level and MUST be logged to the federation audit log each time it
is applied.

#### §6.8.3 Scope propagation edge cases {#section-6-8-3}

The following edge cases were identified during the pre-reset spec 4-node topology testing:

1. **Mixed-scope batch push.** A push payload (`POST /v1/federation/facts/push`) may
   contain facts of multiple scopes. Nodes MUST enforce per-fact scope checking within
   a batch; a scope violation on one fact MUST NOT cause the entire batch to be rejected.
   The response's `rejected` count and `errors` array MUST enumerate each rejected fact.

2. **Scope of contradiction meta-facts.** When a federated fact creates a contradiction,
   the `stigmem:conflict:between` meta-fact MUST inherit the scope of the conflicting
   facts. If two facts in `company` scope conflict, the conflict record is `company`-scoped.
   If a `public` fact from a peer conflicts with a local `company` fact (same entity, same
   relation), the conflict record is `company`-scoped (the narrower scope wins).

3. **`team`-scoped fact from a misbehaving peer.** If a peer sends a `team`-scoped fact
   and the PeerDeclaration does not include `"team"` in `allowed_scopes`, the fact MUST be
   rejected with HTTP 403 and logged as `event_type="scope_violation"` in the federation
   audit log. This applies even if `STIGMEM_FEDERATION_ALLOW_TEAM=true` is set locally —
   the PeerDeclaration is the authoritative grant, not the local env flag.

---
