# Evaluation Harness Status

The evaluation harness is deferred for the current alpha artifact set. The
concept document describes adversarial and recall benchmarks, but the runnable
`eval/` implementation and corpus files are not present in the current feature
surface.

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `deferred` |
| Stability | `experimental` |
| Default surface | `internal` |
| Owner | `unowned` |
| Package | `none` |
| Implementation | `experimental/eval-harness` |
| Publication state | `defer` - concept-only in the current repository state; no runnable harness/corpus package exists. |

## Release History

| Release line | State | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Evaluation harness concept documentation existed outside the supported artifact set. | `experimental/eval-harness/concept.md`; `experimental/eval-harness/STATUS.md` |
| `0.9.xA` planned | Keep the concept discoverable while runnable implementation, corpus, CI, and ownership remain future alpha work. | `docs/internal/feature-tracker.md`; this feature record |

## Gates

| Gate | Status | Notes |
| --- | --- | --- |
| Concept inventory | Complete | `experimental/eval-harness/concept.md` describes intended suites and metrics. |
| Feature record | Complete | ADR-020 feature record added under `features/eval-harness`. |
| Runnable harness | Open | No current `eval/` implementation tree is present under this feature. |
| Corpus fixtures | Open | Adversarial and recall corpus files are not present. |
| CI integration | Open | No current runnable harness evidence is recorded for this deferred feature. |
| Live-node validation | Open | No current live-node eval evidence is recorded. |
| Ownership | Open | Owner remains unassigned. |

## Current Gaps

- The feature is concept-only in the current repository state.
- Counts and thresholds in the concept document need revalidation when the
  runnable harness is restored.
- Security and quality claims should not be treated as release evidence until
  the corpus and runners exist.
