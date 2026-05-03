# 4-Node Federation Failure Modes

**Issue:** ACM-61  
**Status:** Documented from integration test observations and protocol analysis  
**Protocol version:** stigmem spec v0.7-draft (§6)

---

## Overview

A 4-node full-mesh federation cluster (pull replication, interval 10s default) was exercised against six failure classes. Each entry documents the observable behavior, the invariants that hold, and the action required to recover.

---

## FM-1: Node Partition (network isolation)

**Scenario:** One node is disconnected from the network (Docker: `network disconnect`, or firewall drop). Other 3 nodes continue operating.

**Observed behavior (test_4node_federation.py / infra/soak/run_soak.sh T+4h injection):**
- The partitioned node's pull loop logs connection errors and backs off exponentially (1s → 2s → … → 300s max, per `federation_pull.py` `_MAX_BACKOFF_S`).
- Facts asserted on the partitioned node accumulate locally but do not replicate.
- The 3-node partition continues replicating among themselves normally.
- Contradiction detection on the 3-node side continues to fire for any conflicting facts within that partition.

**On reconnect:**
- The partitioned node resumes its pull loop on the next interval (backoff resets after a successful pull).
- HLC cursor resumes from last committed position — no facts are skipped.
- Facts accumulated on the isolated node during partition replicate outward on reconnect.
- Cross-partition contradiction detection fires when the post-reconnect pull ingests divergent facts. **This is the highest-risk moment: contradiction storms proportional to writes-during-partition.**

**Invariants that hold:**
- `local`-scope facts on the isolated node are never visible on the 3-node partition (verified: `test_local_fact_does_not_replicate`).
- No data is lost: all facts on both sides are preserved and replicated after reconnect.
- No unrecovered split-brain: both sides' facts coexist with contradiction records, not silent overwrites.

**PACELC note:** During partition, the system chooses **Availability + Eventual Consistency** over strong consistency. This is intentional. Contradiction records are first-class events, not errors.

**Recovery time:** O(backoff) to detect reconnect + O(facts-accumulated × pull-batch-size / pull-interval) to catch up. Default 100-fact pages at 10s intervals → ~10s per 100 facts of divergence.

---

## FM-2: Slow Peer (high network latency)

**Scenario:** One node has artificially elevated RTT (e.g., 500ms added via `tc netem`).

**Observed behavior:**
- Pull requests to the slow peer time out or succeed slowly. The `pull_from_peer_once` caller has a 30s timeout (`httpx.AsyncClient(timeout=30.0)`).
- At 500ms RTT, pull succeeds but at reduced throughput (one pull per interval + RTT).
- Other 3 nodes' inter-pull latency is unaffected.
- Peer token TTL (default 1h) does not expire during typical delay windows.

**Degradation profile:**
- Replication latency from/to slow peer degrades approximately linearly with RTT.
- At 2000ms+ RTT, effective throughput drops to 1 pull page per ~12s (10s interval + 2s RTT).
- At RTT > 30s, the httpx timeout fires; pull returns the old cursor and retries next cycle. No facts lost.

**Invariants that hold:**
- No data loss, no contradiction cascade.
- Other node-pairs not affected.

**Note for spec v0.8:** The `federation_pull_interval_s` advisory from the peer (if we add it) could allow the slow node to signal a preferred pull rate. Currently there is no backpressure signal beyond 429.

---

## FM-3: Node Restart / Crash Recovery

**Scenario:** A node process exits (clean `SIGTERM` or unclean `SIGKILL`) and restarts.

**Observed behavior (verified: `TestCursorResume::test_node_restart_resumes_without_gaps`):**
- On restart, the node reads `replication_cursors` from SQLite (persisted across restarts via WAL).
- Pull loop resumes from the last committed HLC cursor per peer — no facts asserted during downtime are missed.
- Restart-to-healthy time: < 5s (uvicorn startup + migration check).
- Node rejoins the mesh and catches up within `N_missed_facts / 100 × pull_interval_s` seconds.

**Invariants that hold:**
- No facts lost from the restarting node's perspective.
- No duplicate ingest: `federation_ingest.py` is idempotent on fact ID (silent no-op for already-seen IDs).

**Edge case (gap in cursor):** If the DB file is lost or corrupted, the cursor resets to `NULL` (start of time). This causes a full re-pull of all facts from each peer. This is safe (idempotent ingest) but expensive for large datasets. See [cursor-reset-recovery.md](./cursor-reset-recovery.md) for the recovery procedure and the `stigmem federation cursor-export / cursor-import` helper that bounds re-pull cost on large datasets (ACM-102).

---

## FM-4: Contradiction Storm

**Scenario:** Many contradicting facts are asserted rapidly from multiple nodes (e.g., 50+ conflicting `(entity, relation, scope)` tuples in 60s).

**Observed behavior:**
- Each ingested contradiction generates 2 system facts (`stigmem:conflict:between`, `stigmem:conflict:status=unresolved`) plus a `conflicts` row.
- These system facts use the `stigmem:` prefix and are **not** re-replicated across federation (scope exemption, `federation_ingest.py` `_is_reserved_stigmem` check). Each node independently generates its own conflict records on ingest.
- Under storm conditions, HLC counter increments rapidly (conflict system facts each call `node_hlc.tick()`). At 50 conflicts/s, the HLC counter could reach thousands per millisecond, but remains monotonically correct per spec §2.4.
- SQLite WAL mode handles concurrent writes without deadlock; storm throughput is bounded by SQLite I/O (~1000 writes/s on SSD for typical fact sizes).

**Invariants that hold:**
- All contradiction pairs are recorded; none silently dropped.
- HLC invariant maintained under storm.
- `local`-scope conflict system facts do not cross node boundaries.

**Risk:** A sustained storm (e.g., agents continuously asserting conflicting values) can grow the `conflicts` table unboundedly. **No eviction or TTL on conflict records currently exists.** This is a spec v0.8 edge case to address (see D3 ACM-63).

---

## FM-5: Malformed / Expired Peer Token

**Scenario:** A peer sends a token that is expired, has an invalid signature, or contains a replayed nonce.

**Observed behavior (spec §6.6, verified in `test_federation.py`):**
- `verify_peer_token` raises `TokenError` with one of: `token_expired`, `invalid_signature`, `invalid_sub`, `missing_nonce`, `nonce_already_seen`.
- The pull endpoint returns HTTP 401.
- An audit log entry is written (`rejected_token` or `replay_attempt`).
- The pull loop in the caller logs a warning and retains the old cursor; no facts are lost from the caller's perspective.
- The valid peer token is refreshed on the next pull cycle (`create_peer_token` is called fresh each pull).

**Invariants that hold:**
- Replayed tokens are rejected silently and logged.
- No facts are delivered under an invalid token.

**Note:** If the server clock drifts beyond `exp` (epoch_ms), tokens will start expiring early. NTP sync is assumed for production deployments. A monotonic clock guarantee is needed per spec §2.4.

---

## FM-6: Scope Boundary Violation Attempt

**Scenario:** A peer is registered with `allowed_scopes=["public"]` but its token claims `scopes=["public","company","local"]`.

**Observed behavior (spec §5.8):**
- `_allowed_output_scopes` computes the intersection of peer's declared `allowed_scopes` and the token's `scopes` claim.
- `local` is always discarded from output scopes.
- `team` is discarded unless `STIGMEM_FEDERATION_ALLOW_TEAM=true`.
- If the intersection is empty, the pull endpoint returns 403.
- The audit log records a `scope_violation` entry.

**Invariants that hold:**
- `local`-scope facts NEVER leave origin (verified: `TestScopeIsolation`).
- Peers can only pull facts for scopes declared in their PeerDeclaration, regardless of token claims.

---

## Summary Table

| Failure Mode | Data Loss | Invariant Breach | Recovery | Blast Radius |
|---|---|---|---|---|
| FM-1: Partition | None (facts persist) | None | Automatic on reconnect | Single node |
| FM-2: Slow peer | None | None | Automatic (backoff) | Single peer link |
| FM-3: Node restart | None (cursor persists) | None | Automatic on restart | Single node |
| FM-4: Contradiction storm | None | None (all recorded) | Manual conflict resolution | Unbounded `conflicts` table growth |
| FM-5: Bad/expired token | None | None (audit-logged) | Automatic next cycle | Single pull cycle |
| FM-6: Scope violation | None | None (enforced at API) | None needed | Blocked at gateway |

---

## Open Edge Cases for Spec v0.8 (D3)

These emerged from test iteration and are surfaced for ACM-63:

1. **Contradiction storm eviction:** No TTL or eviction policy for `conflicts` table. Long-running deployments with frequent contradictions will grow unboundedly. Need a conflict archival / auto-resolution policy.

2. ~~**Cursor reset on DB loss**~~ — **Resolved (ACM-102):** Recovery procedure documented in [cursor-reset-recovery.md](./cursor-reset-recovery.md); `stigmem federation cursor-export / cursor-import` CLI helpers bound re-pull cost.

3. **Backpressure signal:** The `federation_pull_interval_s` hint from peer well-known is mentioned in spec but not yet implemented. The 429 response is the only backpressure mechanism. Under high load, 429 back-off compounds with contradiction storms.

4. **HLC counter overflow under storm:** Under extremely high write rates, the HLC counter advances very rapidly. The current format (`{wall_ms}.{counter}`) stores counter as decimal in a TEXT column. No overflow boundary is defined. Need a bound or normalization rule.
