# Decay Semantics Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/decay/spec.md` | Legacy compatibility pointer used by the generated protocol index. |
| `experimental/decay/concept.md` | Legacy compatibility pointer for concept links. |
| `node/src/stigmem_node/decay.py` | Decay sweep behavior. |
| `node/src/stigmem_node/routes/decay.py` | HTTP route surface for decay sweep operations. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Synthesis and decay tests | `node/tests/recall/test_synthesis_decay.py` | TTL, min-confidence, dry-run, scope validation, and system-fact exclusion. |
| Protocol conformance imports | `node/tests/conformance/test_conformance_v1.py` | Ensures decay modules remain importable in conformance setup. |
| Protocol index | `uv run python scripts/generate_protocol_md.py --check` | Confirms experimental Spec-X metadata remains indexed. |

## Coverage Gaps

- Operator policy examples are incomplete.
- Legal-hold and tombstone interaction evidence is incomplete.
- External operator soak evidence is not recorded.
