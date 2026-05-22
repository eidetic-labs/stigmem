# Evaluation Harness Evidence

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/eval-harness/concept.md` | Concept documentation for intended adversarial and recall suites. |
| `experimental/eval-harness/STATUS.md` | Legacy status pointer to this feature record. |

No runnable harness implementation, corpus fixtures, pytest entry points, or
results directory are present under the current feature surface.

## Test Evidence

No executable test suite is currently recorded for the evaluation harness
feature. Validation for this migration is limited to documentation and
projection checks.

## Documentation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/eval-harness/concept.md` | Intended operator audience, suite descriptions, metrics, baseline concepts, and corpus shape. |
| `docs/internal/feature-tracker.md` | Migration inventory row for the deferred evaluation tooling. |

## Validation Commands

Use repository docs checks for feature-record and projection validation:

```bash
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

## Missing Evidence

- Runnable adversarial suite is not present.
- Runnable recall benchmark is not present.
- Corpus and baseline fixtures are not present.
- Live-node validation is not complete.
