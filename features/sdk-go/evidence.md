# Go SDK Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `experimental/sdk-go/client.go` | Client construction, HTTP request handling, API methods, subscriptions, recall, and memory-card calls. |
| `experimental/sdk-go/types.go` | Fact, scope, node metadata, peer, conflict, recall, and memory-card model types. |
| `experimental/sdk-go/errors.go` | Typed HTTP error mapping. |
| `experimental/sdk-go/go.mod` | Module path and Go version declaration. |
| `experimental/sdk-go/examples/assert_recall_subscribe/main.go` | Example covering fact assertion, recall, and polling subscription. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `experimental/sdk-go/stigmem_test.go` | Unit coverage for node info, facts, conflicts, federation, recall, memory cards, subscriptions, errors, and fact-value constructors. |
| `go test ./...` from `experimental/sdk-go` | Package test entry point. |

## Public Docs

| Path | Coverage |
| --- | --- |
| `experimental/sdk-go/concept.md` | Legacy SDK reference and usage guide. |
| `docs/docs/get-started/sdk-quickstart.md` | Public SDK quickstart with Go example. |
| `docs/docs/sdks/index.md` | SDK overview listing. |
| `docs/docs/sdks/typescript.md` | Cross-link to Go SDK reference. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Live-node smoke evidence is not complete.
- API parity with current generated node API docs needs release-line review.
- Package publication/tag evidence remains deferred.
