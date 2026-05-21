# Async Jobs Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `opt-in` |

Async jobs exist in the reference node as the shared background execution path
for lint and decay sweeps. The surface is experimental because queue durability,
operator controls, and broader job families remain future-horizon work.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Async lint and decay job behavior existed in the alpha-era node and was tracked as a deferred experimental feature. | `experimental/async-jobs/STATUS.md`; `node/tests/lifecycle/test_async_jobs.py` |
| `0.9.xA` planned | Keep the feature outside the default surface while deciding whether broader background job APIs remain core, move behind a plugin boundary, or stay operation-specific. | `ROADMAP.md`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Contract tests | Validate async/sync threshold selection, polling, terminal result stability, and cross-type isolation. | Partial | `node/tests/lifecycle/test_async_jobs.py` |
| Operator controls | Define retention, cancellation, visibility, and queue limits for broader job usage. | Open | None currently recorded. |
| Durability posture | Decide whether node-local job state is sufficient or whether persistent/durable queues are needed. | Open | `node/src/stigmem_node/jobs.py` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No standalone Spec-X assignment exists.
- No cancellation endpoint is defined.
- No operator-facing retention or purge controls are documented.
- The feature does not yet define a general-purpose job API beyond lint and
  decay polling surfaces.
