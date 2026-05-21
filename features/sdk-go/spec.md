# Go SDK Spec

## Scope

The Go SDK wraps the Stigmem node HTTP API for Go applications. It does not own
the node API, protocol semantics, or release artifact policy. It owns the Go
client surface, option types, response models, error mapping, and example usage.

This feature covers:

- client construction for a Stigmem node base URL;
- API key, timeout, custom HTTP client, and TLS configuration options;
- fact value constructors and scope constants;
- node metadata, fact assertion, retraction, fact lookup, and fact querying;
- conflict list and resolution helpers;
- federation peer listing;
- channel-based polling subscriptions;
- recall and memory-card helper methods;
- Go error types for common HTTP response classes.

## Client Surface

| Area | Go surface |
| --- | --- |
| Construction | `New`, `WithAPIKey`, `WithTimeout`, `WithTLSConfig`, `WithHTTPClient` |
| Facts | `AssertFact`, `Retract`, `GetFact`, `QueryFacts` |
| Conflicts | `ListConflicts`, `ResolveConflict` |
| Federation | `FederationStatus` |
| Recall | `Recall`, recall option helpers, `GetCard` |
| Subscription | `Subscribe`, `SubscribeInterval`, `SubscribePageSize` |
| Errors | `StigmemError`, `StigmemAuthError`, `StigmemNotFoundError`, `StigmemConflictError` |

## Packaging

The module path is `github.com/eidetic-labs/stigmem-go` and the implementation
currently lives under `experimental/sdk-go`. The module requires Go 1.22 or
later and has no external dependencies.

The SDK is not part of the current alpha artifact set. Consumers should treat
it as experimental and pin to an explicit commit or pre-release tag until
release-line package validation is complete.

## Non-Goals

- Replacing the Python SDK as the primary supported SDK for the active alpha
  release line.
- Defining new node API semantics.
- Claiming stable package availability before release-line validation.
- Providing generated-code parity with every node endpoint.

## Canonical Spec Assignment

There is no Spec-X assignment for the Go SDK. It is an external client library
around existing node API behavior, not a standalone Stigmem protocol module.
