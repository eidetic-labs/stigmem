# Evaluation Harness Security

The evaluation harness is intended to validate adversarial behavior against a
live Stigmem node, but the current feature surface is concept-only. Its security
posture is therefore a future validation target, not current release evidence.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Deferred surface | The harness is outside the current alpha artifact set. | `experimental/eval-harness/STATUS.md`; this feature record |
| Adversarial scope | The concept describes typo-squatting, contradiction floods, tombstone bypass, capability-token forgery, and sanitizer bypass. | `experimental/eval-harness/concept.md` |
| Credential handling | Intended runs use `STIGMEM_EVAL_URL` and optional `STIGMEM_API_KEY`. | `experimental/eval-harness/concept.md` |

## Security References

No dedicated R-* audit item is assigned to this feature. The concept maps to
security regression testing but does not currently provide runnable evidence.

## Advisories and Findings

None currently recorded for the feature.

## Residual Risk

- Concept-level adversarial counts and thresholds may be stale until the
  runnable corpus is restored.
- A future harness that targets live nodes must protect API keys and generated
  results artifacts.
- Security conclusions should not rely on this feature until implementation and
  CI evidence exist.

## Operator Guidance

- Treat this feature as deferred until a runnable harness and corpus are
  present.
- Do not use concept-only counts as release evidence.
- Revalidate API-key handling and artifact retention when the harness is
  implemented.
