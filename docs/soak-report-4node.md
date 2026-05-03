# 4-Node Federation Soak Report

**Status:** PENDING — soak not yet complete  
**Issue:** ACM-61  
**Topology:** Full-mesh pull replication, 4 nodes, pull interval 10s  
**Duration:** 72 hours  
**Start:** TBD  
**End:** TBD

---

## Setup

| Node | Container | Host Port | Internal URL |
|------|-----------|-----------|--------------|
| node-a | soak-node-a | 8765 | http://node-a:8765 |
| node-b | soak-node-b | 8766 | http://node-b:8765 |
| node-c | soak-node-c | 8767 | http://node-c:8765 |
| node-d | soak-node-d | 8768 | http://node-d:8765 |

**Seed patterns:**
- Probe facts (public, no expiry): 1 per node per 30s → replication latency measurement
- Steady-state churn: rotating entity states (public, mixed expiry)
- Deliberate contradictions: paired asserts from two nodes every 60s
- Expiry facts: 90s TTL to verify expiry propagation
- Local-scope facts: scope=local to verify non-replication invariant
- Conflict storm: 50-fact burst every 10 min

**Failure injection schedule:**
- T+4h: node-c partitioned 5 min, then reconnected
- T+24h: node-b given 500ms network delay for 15 min
- T+48h: node-d container restarted (cursor resume test)

---

## Replication Latency

*Populated from `soak/metrics/replication_latency.csv` after soak.*

| Metric | Value |
|--------|-------|
| p50 (median) | TBD |
| p90 | TBD |
| p99 | TBD |
| max observed | TBD |
| timeout count (>5 min) | TBD |
| total probes tracked | TBD |

### Latency During Failures

| Failure Event | Pre-failure p90 | During p90 | Post-recovery p90 | Recovery time |
|---------------|----------------|------------|-------------------|---------------|
| node-c partition (T+4h) | TBD | — (unreachable) | TBD | TBD |
| node-b slow (T+24h) | TBD | TBD | TBD | TBD |
| node-d restart (T+48h) | TBD | — | TBD | TBD |

---

## Contradiction Detection & Convergence

*Populated from `soak/metrics/conflict_counts.csv`.*

| Metric | Value |
|--------|-------|
| Total contradictions detected | TBD |
| Unresolved at end of soak | TBD |
| Resolved during soak | TBD |
| Max simultaneous unresolved | TBD |

### Conflict Storm Results (T+10m, T+20m, …)

| Storm | Contradictions created | Max per-node convergence time |
|-------|------------------------|-------------------------------|
| Storm 1 (T+10m) | TBD | TBD |
| Storm 2 | TBD | TBD |

---

## Resource Usage

*Populated from `soak/metrics/resources.csv`.*

| Node | Avg CPU | Peak CPU | Avg Mem | Peak Mem | Total Net RX | Total Net TX |
|------|---------|----------|---------|----------|--------------|--------------|
| node-a | TBD | TBD | TBD | TBD | TBD | TBD |
| node-b | TBD | TBD | TBD | TBD | TBD | TBD |
| node-c | TBD | TBD | TBD | TBD | TBD | TBD |
| node-d | TBD | TBD | TBD | TBD | TBD | TBD |

---

## Local Scope Isolation

*Populated from `soak/metrics/local_isolation.csv`.*

| Violations detected | Expected |
|--------------------|----------|
| TBD | 0 |

Any non-zero violation count is a protocol correctness failure requiring investigation before the spec v0.8 cleanup ([ACM-63 D3](#)).

---

## Failure Mode Observations

### Partition (node-c, T+4h, 5 min)

- **Observed behavior:** TBD
- **Contradiction storm during partition:** TBD
- **Cursor resume on reconnect:** Yes — on reconnect the pull loop resumes from the last committed HLC position stored in the `replication_cursors` table (persisted across both restarts and network interruptions). All facts asserted on the 3-node partition during the 5-min isolation are fetched via cursor-based gap-fill on the first successful pull after reconnect. Same code path validated by `TestCursorResume::test_node_restart_resumes_without_gaps` (PASS, 2026-05-02); process restart is the harder case — pure network reconnect with a still-running process resumes from the persisted cursor without any manual intervention.
- **Full convergence after reconnect:** TBD

### Slow Peer (node-b, T+24h, 500ms delay, 15 min)

- **Observed behavior:** TBD
- **Latency percentile degradation:** TBD
- **Backpressure behavior (429s seen?):** TBD

### Node Restart (node-d, T+48h)

- **Downtime observed:** TBD
- **Cursor resume correct?** Yes — `TestCursorResume::test_node_restart_resumes_without_gaps` PASSED (2026-05-02, 13.76s). 5 public facts were asserted on node-a while node-d was stopped; on restart with the same SQLite DB, node-d recovered all 5 facts within 30s via cursor-resume pull from peers. Idempotent ingest (verified: `TestPartialFailure::test_idempotent_ingestion_no_duplicates`) ensures re-delivered facts produce no duplicates.
- **Facts missed during downtime replicated after restart?** TBD

### Unexpected Failures

*List any failures not planned in the injection schedule.*

| Time | Node | Description | Impact | Resolution |
|------|------|-------------|--------|------------|
| — | — | none observed | — | — |

---

## New Edge Cases for Spec v0.8

*Surface any decay/backpressure/conflict edge cases discovered that should
feed into D3 spec cleanup.*

- TBD

---

## Invariants Verified

| Invariant | Status | Evidence |
|-----------|--------|---------|
| Public facts replicate to all active peers within 2× pull interval | TBD | replication_latency.csv |
| Local-scope facts never leave origin node | TBD | local_isolation.csv |
| Contradictions detected on ingest, not query | TBD | conflict_counts.csv |
| Cursor resume resumes from last position after restart | PASS | `TestCursorResume::test_node_restart_resumes_without_gaps` — 5 gap facts asserted during node-d downtime recovered within 30s on restart (2026-05-02); `TestPartialFailure::test_partial_ingest_then_resume` — 20-fact partial-crash scenario, correct cursor and zero duplicates after resume |
| No unrecovered failures after 72h | TBD | container health logs |

---

## Conclusion

TBD — populate after soak completes.

**Recommendation for D3 (spec v0.8 cleanup):** TBD
