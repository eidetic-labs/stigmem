# Synthesis Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/synthesis/spec.md` | Legacy compatibility pointer used by the generated protocol index. |
| `experimental/synthesis/concept.md` | Legacy compatibility pointer for concept links. |
| `node/tests/recall/test_synthesis_decay.py` | Current executable evidence for synthesis behavior. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Synthesis and decay tests | `node/tests/recall/test_synthesis_decay.py` | Summary generation, confidence filtering, contradiction signals, and related decay behavior. |
| Protocol index | `uv run python scripts/generate_protocol_md.py --check` | Confirms experimental Spec-X metadata remains indexed. |
| Feature record validator | `python3 scripts/check_feature_records.py` | Confirms this feature record is complete. |

## Coverage Gaps

- Adapter-specific rendering conformance is incomplete.
- Operator guidance for using summaries in agent prompts is incomplete.
- External operator soak evidence is not recorded.
