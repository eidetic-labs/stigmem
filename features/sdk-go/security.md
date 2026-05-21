# Go SDK Security

## Threat Model Delta

The Go SDK is an external client library. It sends API keys, fact writes, recall
queries, and conflict-resolution requests to a configured Stigmem node. It does
not add an independent authorization boundary; node-side auth, quotas, audit,
scope, and validation controls remain authoritative.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| API key exposure in client code | API keys are configured through client options; application code is responsible for secret storage. | `experimental/sdk-go/client.go`; `experimental/sdk-go/concept.md` |
| Transport configuration | Client construction supports custom TLS configuration and custom HTTP clients for mTLS or operator-controlled transports. | `experimental/sdk-go/client.go` |
| Error handling ambiguity | HTTP auth, not-found, and conflict statuses map to typed Go errors. | `experimental/sdk-go/errors.go`; `experimental/sdk-go/stigmem_test.go` |

## Residual Risk

- Applications using the SDK must protect API keys and configure trusted node
  URLs.
- The SDK can issue writes and conflict resolutions when given credentials with
  those permissions; least-privilege key issuance is a node/operator concern.
- The SDK is experimental and not yet release-line certified.

## Advisories and Findings

None currently recorded.
