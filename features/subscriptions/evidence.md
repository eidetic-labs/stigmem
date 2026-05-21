# Subscriptions Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/subscriptions/spec.md` | Legacy compatibility pointer used by the generated protocol index. |
| `experimental/subscriptions/concept.md` | Legacy compatibility pointer for concept links. |
| `docs/docs/reference/api/generated/*subscription*` | Generated public API reference pages for subscription endpoints. |
| `node/src/stigmem_node/subscription_delivery.py` | Delivery behavior referenced by tombstone filtering tests. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Tombstone delivery suppression | `node/tests/tombstones/test_tombstone_filter.py` | Ensures subscription delivery suppresses tombstoned entities. |
| API docs build | `bash scripts/check.sh docs` | Confirms generated subscription reference pages render. |
| Protocol index | `uv run python scripts/generate_protocol_md.py --check` | Confirms experimental Spec-X metadata remains indexed. |

## Coverage Gaps

- Delivery-time garden ACL and token revocation vectors are incomplete.
- Replay-window and webhook retry conformance evidence is incomplete.
- Wake delivery integration evidence is not recorded.
