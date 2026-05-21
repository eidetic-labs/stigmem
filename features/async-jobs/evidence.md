# Async Jobs Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/jobs.py` | Shared job creation, lookup, status updates, result storage, and terminal failure handling. |
| `node/src/stigmem_node/routes/lint.py` | Lint threshold evaluation, background task scheduling, and lint job polling. |
| `node/src/stigmem_node/routes/decay.py` | Decay threshold evaluation, background task scheduling, and decay job polling. |
| `node/src/stigmem_node/settings.py` | `async_job_threshold` setting. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `node/tests/lifecycle/test_async_jobs.py` | Unknown job 404s, async 202 responses, polling completion, result stability, and lint/decay cross-type isolation. |
| `node/tests/conftest.py` | Test client fixture forces the async threshold to exercise the 202 path. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- No retention or cleanup test exists for old jobs.
- No cancellation behavior exists.
- No external queue or multi-process durability evidence exists.
