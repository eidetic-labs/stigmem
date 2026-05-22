# Evaluation Harness Spec

The evaluation harness concept defines live-node validation for Stigmem
correctness and quality. It is intended to combine adversarial security
scenarios with recall-quality benchmarks, but the current repository surface is
documentation-only.

## Intended Suites

| Suite | Intended focus |
| --- | --- |
| Adversarial scenarios | Typo-squatting, contradiction floods, tombstone bypass, capability-token forgery, and sanitizer bypass. |
| Recall benchmarks | nDCG@10 and Recall@5 against seeded corpus probes. |

## Intended Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_EVAL_URL` | Target live node for evaluation. |
| `STIGMEM_API_KEY` | Optional API key for authenticated nodes. |

## Intended Artifacts

The concept document describes an `eval/` tree with adversarial corpora, recall
probes, baseline metrics, runners, pytest entry points, and results artifacts.
Those files are not present in the current repository state for this feature.

## Out of Scope

- Treating the concept document as runnable implementation evidence.
- Blocking current alpha release work on a harness that has not been restored.
- Declaring conformance or quality thresholds until the corpus and runners
  exist in source control.

## Spec Assignment

There is no Spec-X assignment for the evaluation harness. It is deferred
internal tooling rather than a protocol-bearing feature.
