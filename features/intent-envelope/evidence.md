# Intent Envelope Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/intent-envelope/spec.md` | Legacy compatibility pointer used by the generated protocol index. |
| `experimental/intent-envelope/concept-sdk.md` | Preserved concept material for possible SDK integration. |
| `spec/EVOLUTION.md` | Historical explanation of the section 4 deferral. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Protocol index | `uv run python scripts/generate_protocol_md.py --check` | Confirms experimental Spec-X metadata remains indexed. |
| Feature record validator | `python3 scripts/check_feature_records.py` | Confirms this feature record is complete. |

## Coverage Gaps

- No implementation tests exist because the feature is deferred.
- No adapter-specific evidence exists.
- No adversarial conformance vectors exist.
