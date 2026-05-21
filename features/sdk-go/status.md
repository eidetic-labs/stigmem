# Go SDK Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `external` |

The Go SDK source exists and has local unit tests, but it remains experimental
and outside the current alpha artifact set. Release-line promotion requires API
parity review, packaging validation, and fresh smoke evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Go SDK source and documentation existed as experimental SDK surface area. | `experimental/sdk-go/STATUS.md`; `experimental/sdk-go/` |
| `0.9.xA` planned | Validate API parity, package metadata, examples, and release artifact policy before promotion. | `docs/internal/feature-tracker.md`; `docs/compatibility-matrix.yaml` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Client surface | Provide idiomatic Go helpers for the main node API paths. | Partial | `experimental/sdk-go/client.go`; `experimental/sdk-go/types.go` |
| Error mapping | Return typed errors for auth, not-found, conflict, and generic HTTP failures. | Partial | `experimental/sdk-go/errors.go`; `experimental/sdk-go/stigmem_test.go` |
| Unit coverage | Cover client request behavior, option handling, subscription polling, and value constructors. | Partial | `experimental/sdk-go/stigmem_test.go` |
| Example coverage | Provide an assert, recall, and subscribe example. | Partial | `experimental/sdk-go/examples/assert_recall_subscribe/main.go` |
| Package alignment | Align module/tag policy with the active release line. | Open | `experimental/sdk-go/go.mod`; `docs/compatibility-matrix.yaml` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- The Go SDK is not shipped in the current alpha artifact set.
- API parity with all current node endpoints needs review before promotion.
- The public install guidance should not imply a stable `latest` release until
  release-line packaging is validated.
- Integration smoke evidence against a live node is not complete.
