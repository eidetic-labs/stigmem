---
title: §11. Failure Mode Scenarios
sidebar_label: §11 Failure Mode Scenarios
audience: Spec
description: "Stigmem spec section 11 — Acceptance test scenarios — split-brain, malicious peer, partial failure, replay attack."
---

# §11. Failure Mode Scenarios {#section-11}

**Status:** Stable

Acceptance test scenarios — split-brain, malicious peer, partial failure, replay attack.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

These scenarios are **acceptance gates** for Phase 3. All four MUST pass before
the phase is considered complete.

### §11.1 Split-Brain {#section-11-1}

**Setup:** Two nodes A and B are federated with `scope=public`. Both are initially
in sync (same public facts).

**Scenario:**
1. Cut network connectivity between A and B (simulated partition).
2. Write fact `F_a` to node A: `(entity="stigmem://node-a/test/entity", relation="test:value", value="from-a", scope="public")`.
3. Write fact `F_b` to node B: `(entity="stigmem://node-a/test/entity", relation="test:value", value="from-b", scope="public")`.
4. Maintain partition for >5 minutes. Both nodes continue accepting reads and writes.
5. Restore connectivity.
6. Allow replication to complete (pull cycle fires on both sides).

**Expected outcomes:**
- Both nodes store both `F_a` and `F_b`.
- A `stigmem:conflict:between` fact exists on both nodes (or at minimum on the node
  that ingested the second fact — the local node MUST detect the conflict on ingestion).
- `GET /v1/conflicts?status=unresolved` returns the conflict on both nodes.
- `GET /v1/facts?entity=stigmem://node-a/test/entity&relation=test:value&include_contradicted=true` returns
  both facts with `contradicted: true`.
- No fact is silently discarded.

### §11.2 Malicious Peer {#section-11-2}

**Setup:** Node A and Node B are federated. A third process ("attacker") obtains
a valid peer token for the `node_b` → `node_a` direction (simulating a compromised
peer or MITM).

**Scenario:**
1. Attacker attempts to push a fact with `scope="company"` to node A's
   `/v1/federation/facts/push`, where the PeerDeclaration only allows `["public"]`.
2. Attacker attempts to push a fact with `source="stigmem://node-c/user/alice"` (an entity not
   belonging to node B's declared namespace).
3. Attacker replays a previously-seen valid peer token (captured from an earlier
   legitimate exchange) after the nonce window expires. Then replays within the window.

**Expected outcomes:**
1. HTTP 403. Fact rejected. `federation_audit` record written: `event_type="scope_violation"`.
2. HTTP 403. Fact rejected. `federation_audit` record written: `event_type="rejected_fact"`, reason=`source_not_owned`.
3. First replay (outside nonce window): token accepted (nonce evicted). Second replay (inside window): HTTP 401. `federation_audit` record: `event_type="replay_attempt"`.
   - Node A's fact store is not corrupted by either replay attempt.

### §11.3 Partial Failure (Peer Down Mid-Replication) {#section-11-3}

**Setup:** Node A (subscriber) is pulling from Node B (publisher). Node B has 1000
public facts. A has pulled 500 so far; cursor is stored.

**Scenario:**
1. Node B crashes after returning facts 501–600 but before node A persists the cursor
   for that batch. (Simulate: kill node B's process; reset A's cursor to the 500 mark.)
2. Node A attempts its next pull; node B is unreachable.
3. Node A continues serving read and write requests normally.
4. Node B restarts.
5. Node A's next pull cycle fires.

**Expected outcomes:**
- During step 2: Node A returns 503 or times out on the pull attempt; no crash; local
  reads/writes unaffected.
- After step 5: Node A resumes from cursor 500 (not 0, not 600). Facts 501–1000 are
  ingested. No duplicates created (idempotency check passes on facts 501–600 that may
  have been partially ingested).
- Final state: Node A has all 1000 facts.

### §11.4 Replay Attack {#section-11-4}

**Setup:** Node A and B are federated. A valid peer token `T` is intercepted.

**Scenario:**
1. Token `T` is used legitimately for a pull request by node B. Succeeds.
2. Token `T` is immediately replayed by an attacker. (Within nonce window.)
3. A new token `T2` is generated with the same nonce as `T` but a fresh `iat`/`exp`.
4. Token `T3` is generated with a past `exp` (already expired).

**Expected outcomes:**
1. First use: HTTP 200, facts returned.
2. Replay of `T`: HTTP 401, `error: "nonce_already_seen"`. Audit log entry.
3. `T2` (duplicate nonce): HTTP 401. The nonce cache matches on nonce value, not token identity.
4. `T3` (expired): HTTP 401, `error: "token_expired"`.

---
