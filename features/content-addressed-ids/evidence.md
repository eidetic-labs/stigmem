# Content-Addressed Fact IDs Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/cid.py` | CID computation, syntax checks, stored-row verification, and mismatch error. |
| `node/src/stigmem_node/routes/facts/cid.py` | Fact CID verification route. |
| `node/src/stigmem_node/routes/facts/single.py` | Single-fact read path, including CID lookup and mismatch handling. |
| `node/src/stigmem_node/routes/facts/query.py` | Fact query read path, including CID mismatch handling. |
| `node/src/stigmem_node/routes/cid_admin.py` | CID backfill status route. |
| `sdks/stigmem-py/src/stigmem/verification.py` | Client-side CID recomputation and verification helpers. |
| `node/src/stigmem_node/db.py` | Migrations and storage setup for CID columns and aliases. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| CID computation and canonicalization | `node/tests/time_travel/test_phase13_time_travel_cid.py` | CID format, determinism, field sensitivity, and independent canonical JSON check. |
| Write-path persistence | `node/tests/time_travel/test_phase13_time_travel_cid.py` | Fact writes store non-null CIDs and create `fact_cid_aliases` rows. |
| CID lookup and verification | `node/tests/time_travel/test_phase13_time_travel_cid.py` | CID lookup, malformed CID handling, verify route, null stored CID, and backfill status. |
| Read-path tamper detection | `node/tests/time_travel/test_phase13_time_travel_cid.py` | Single-fact read, fact query, and recall hydration return `409 cid_mismatch` after simulated tampering. |
| SDK verification | `sdks/stigmem-py/tests/test_client.py` | Client-side CID mismatch handling. |
| Fast gate | `bash scripts/check.sh python` | Runs Python lint, type, tests, and security checks. |

## Conformance and Fixtures

CID behavior is covered by the Phase 13 Python tests and by the protocol
dependency from `Spec-21-Content-Addressed-IDs` to fact model, HTTP API,
federation trust, audit log, and schema/migration specs.

## Coverage Gaps

- Hash algorithm rotation does not yet have conformance vectors.
- Federation CID-null policy is covered by federation trust work, not by this
  feature alone.
- Long-running operator backfill evidence is release-specific and belongs in
  release evidence when a tagged artifact is cut.
