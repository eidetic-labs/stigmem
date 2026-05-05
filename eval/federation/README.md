# Federation Soak Harness

End-to-end federation evaluation: 3-node cluster, conflict convergence, replication-lag
measurement, capability-token verification, audit completeness.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker + Compose plugin | ≥ 24 | `docker compose version` |
| Python | ≥ 3.11 | workspace Python (uv) |
| uv workspace sync | — | `uv sync --all-packages` |
| Ports 8780–8782 | free | eval cluster host ports |

Install Python dependencies (if not already synced):

```sh
uv sync --all-packages
```

## Quick start — smoke (5 min, all 5 CC scenarios)

```sh
make eval-soak-smoke
```

This builds the stigmem Docker image, starts a 3-node cluster, runs a 5-minute
abbreviated workload including all five conflict-convergence scenarios, writes
results to `eval/results/soak-<date>.{json,md}`, then tears down the cluster.

Exit code: `0` = `overall_pass`, `1` = failure.

## Full soak (≥ 1 hour)

```sh
make eval-soak
```

Runs for 3 600 seconds (configurable via `--duration`).  Suitable for nightly
CI.  Conflict scenarios are injected at T+2 min, T+5 min, T+10 min, T+15 min,
and T+20 min during the run.

## Manual invocation

```sh
python eval/federation/soak_driver.py [--duration 3600] [--smoke] [--no-teardown]
```

`--no-teardown` leaves the cluster running after the soak (useful for manual
inspection with `docker logs eval-fed-node-a`).

## Cluster topology

```
node-a (:8780) ←→ node-b (:8781)
     ↑                  ↑
     └─────────────── node-c (:8782)
```

- Ed25519 keypairs generated idempotently to `eval/federation/.env`
- Full-mesh pull replication at 5-second interval
- Each node: `STIGMEM_AUTH_REQUIRED=true`, distinct keypair, shared Docker
  network `eval_fed_net`

## Metrics collected

| Metric | Threshold |
|--------|-----------|
| Replication lag P99 (A→B, A→C) | warn > 2 s, fail > 10 s |
| Capability-token verification rate | must = 1.0 |
| Audit completeness | must = 1.0 |

## Conflict-convergence scenarios

| ID | Description |
|----|-------------|
| CC-1 | Simultaneous contradicting asserts on A and B → both nodes converge |
| CC-2 | Assert on A while C is partitioned → convergence after heal |
| CC-3 | Three-way contradiction (A, B, C each assert a different value) |
| CC-4 | Tombstone on A concurrent with re-assert on B → tombstone wins |
| CC-5 | Invalid capability token → 401/403 (clean failure, no partial data) |

Pass criterion: all nodes report identical `(entity, relation)` state within
30 seconds of conflict injection.

## Artifact schema

Output: `eval/results/soak-<date>.json`

```json
{
  "run_date": "ISO8601",
  "duration_s": 3600,
  "smoke": false,
  "replication_lag": {
    "node_a_to_b": {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "buckets": [], "sample_count": 0},
    "node_a_to_c": {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "buckets": [], "sample_count": 0}
  },
  "token_verification_rate": 1.0,
  "audit_completeness": 1.0,
  "conflict_convergence": [
    {"scenario": "CC-1", "passed": true, "convergence_s": 0.0}
  ],
  "overall_pass": true
}
```

## Nightly CI

Added to `.github/workflows/nightly.yml`; fires at 02:00 UTC on `main`.
Artifacts uploaded as GitHub Actions artifacts (`soak-results-<date>`).

## Troubleshooting

```sh
# View cluster logs
docker logs eval-fed-node-a
docker logs eval-fed-node-b
docker logs eval-fed-node-c

# Force cluster teardown
docker compose -f eval/federation/docker-compose.yml --env-file eval/federation/.env down -v

# Regenerate keypairs (delete .env first)
rm eval/federation/.env
python eval/federation/soak_driver.py --smoke
```
