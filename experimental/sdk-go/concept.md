---
title: Go SDK
sidebar_label: Go SDK
audience: Integrator
---

# Go SDK

The stigmem Go SDK (`stigmem-go`) is an idiomatic Go client for the stigmem memory-node HTTP API (spec v0.4+). It requires **Go 1.22 or later** and has no external dependencies.

## Installation

```bash
go get github.com/eidetic-labs/stigmem-go@latest
```

## Quick start

```go
package main

import (
    "context"
    "fmt"
    "log"

    stigmem "github.com/eidetic-labs/stigmem-go"
)

func main() {
    c := stigmem.New("http://localhost:8765",
        stigmem.WithAPIKey("sk-..."),
    )
    ctx := context.Background()

    // Assert a fact
    fact, err := c.AssertFact(ctx,
        "user:alice", "memory:role",
        stigmem.StringValue("lead engineer"),
        "my-agent",
        stigmem.WithScope(stigmem.ScopeCompany),
    )
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("Asserted:", fact.ID)

    // Query facts
    page, err := c.QueryFacts(ctx,
        stigmem.QueryEntity("user:alice"),
        stigmem.QueryLimit(10),
    )
    if err != nil {
        log.Fatal(err)
    }
    for _, f := range page.Facts {
        fmt.Printf("%s %s = %v\n", f.Entity, f.Relation, f.Value.V)
    }

    // Hybrid recall (spec §20)
    recall, err := c.Recall(ctx, "alice engineering role",
        stigmem.RecallInScope(stigmem.ScopeCompany),
    )
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("%d facts recalled\n", len(recall.Facts))
}
```

## Client options

| Option | Default | Description |
|---|---|---|
| `WithAPIKey(key)` | — | Bearer capability token |
| `WithTimeout(d)` | 10s | Per-request HTTP timeout |
| `WithTLSConfig(cfg)` | — | mTLS / custom TLS settings |
| `WithHTTPClient(h)` | — | Replace the underlying `*http.Client` entirely |

## FactValue constructors

```go
stigmem.StringValue("hello")          // {"type":"string","v":"hello"}
stigmem.TextValue("long body text")   // {"type":"text","v":"..."}
stigmem.NumberValue(42.0)             // {"type":"number","v":42}
stigmem.BooleanValue(true)            // {"type":"boolean","v":true}
stigmem.DatetimeValue("2026-05-04T00:00:00Z")
stigmem.RefValue("stigmem://entity")
stigmem.NullValue()                   // {"type":"null"}
```

## Scopes

```go
stigmem.ScopeLocal
stigmem.ScopeTeam
stigmem.ScopeCompany
stigmem.ScopePublic
```

## Subscribe (channel-based polling)

`Subscribe` spawns a background goroutine that polls the node at a configurable interval and sends non-empty fact batches to a `<-chan []Fact`. The channel is closed when the context is cancelled.

```go
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

ch := c.Subscribe(ctx, stigmem.ScopeCompany,
    stigmem.SubscribeInterval(15*time.Second),
)
for batch := range ch {
    for _, f := range batch {
        fmt.Println(f.ID, f.Relation)
    }
}
```

## mTLS

```go
import "crypto/tls"

cert, _ := tls.LoadX509KeyPair("client.crt", "client.key")
c := stigmem.New("https://node.example.com",
    stigmem.WithTLSConfig(&tls.Config{
        Certificates: []tls.Certificate{cert},
    }),
    stigmem.WithAPIKey("sk-..."),
)
```

## Error handling

All HTTP errors are returned as typed errors. Use `errors.As` to inspect them.

```go
_, err := c.GetFact(ctx, "missing-id")

var nfe *stigmem.StigmemNotFoundError
if errors.As(err, &nfe) {
    fmt.Println("not found:", nfe.Detail)
}
```

| Error type | HTTP status |
|---|---|
| `*StigmemAuthError` | 401, 403 |
| `*StigmemNotFoundError` | 404 |
| `*StigmemConflictError` | 409 |
| `*StigmemError` | all other 4xx/5xx |

## API reference

| Method | Description |
|---|---|
| `NodeInfo(ctx)` | Node metadata from `/.well-known/stigmem` |
| `AssertFact(ctx, entity, relation, value, source, ...opts)` | Assert a new fact |
| `Retract(ctx, entity, relation, scope, source)` | Retract a fact (confidence = 0) |
| `GetFact(ctx, factID)` | Fetch a fact by ID |
| `QueryFacts(ctx, ...opts)` | Paginated fact query |
| `ListConflicts(ctx, ...opts)` | List detected conflicts |
| `ResolveConflict(ctx, conflictID, ...opts)` | Resolve a conflict |
| `FederationStatus(ctx)` | List federation peers |
| `Subscribe(ctx, scope, ...opts)` | Channel-based fact subscription |
| `Recall(ctx, query, ...opts)` | Hybrid recall — BM25 + vector + graph (spec §20) |
| `GetCard(ctx, entityURI, ...opts)` | Synthesized entity memory card (spec §20) |

## Running the example

```bash
cd sdks/stigmem-go/examples/assert_recall_subscribe
STIGMEM_URL=http://localhost:8765 STIGMEM_API_KEY=sk-... go run .
```

## Tests

```bash
cd sdks/stigmem-go
go test ./... -race
```

## v1.0 / v1.1 advanced features

### Content-addressed fact IDs (§25)

Every fact returned by the node includes a `CID` field — a SHA-256 content hash of the fact's canonical body. You can fetch a fact by either UUID or CID:

```go
factByUUID, _ := c.GetFact(ctx, "550e8400-e29b-41d4-a716-446655440000")
factByCID, _  := c.GetFact(ctx, "sha256:a3f2b8c901d4...")
```

Asserting the same (entity, relation, value, source, scope) tuple twice returns the existing fact — CID-based deduplication is automatic. See the [Content Addressing guide](../concepts/facts/content-addressing.md).

### Time-travel queries (§24)

The `as_of` parameter is available on the fact query and recall endpoints via the REST API. Use `net/http` directly for time-travel queries:

```go
req, _ := http.NewRequestWithContext(ctx, "GET",
    "http://localhost:8765/v1/facts?entity=user:alice&as_of=2026-04-15T00:00:00Z", nil)
req.Header.Set("Authorization", "Bearer "+apiKey)
resp, _ := http.DefaultClient.Do(req)
```

See the [Time-Travel Queries guide](../concepts/lifecycle/time-travel.md).

---

## See also

- [Tutorial: SDK Quickstart](../get-started/sdk-quickstart.md) — assert, recall, and subscribe in Python / TS / Go
- [TypeScript SDK Reference](./typescript.md) — TypeScript client
- [Python SDK Reference](./python) — Python client

---

## Public release tag plan

A `v1.0.0` tag at `github.com/eidetic-labs/stigmem-go` will be created after board approval for public release. Until then, consumers should pin to a pre-release tag (`v0.x.y`) or a specific Git SHA. No tag will be pushed without board sign-off.
