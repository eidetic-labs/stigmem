---
title: "Tutorial: SDK Quickstart"
sidebar_label: SDK Quickstart
description: Assert a fact, run a recall, and subscribe to changes — in Python, TypeScript, and Go.
audience: Integrator
---

# Tutorial: SDK Quickstart

**Audience:** Developers integrating with Stigmem for the first time. Pick your language — each section is self-contained.

This tutorial walks through three operations that cover the core Stigmem workflow:

1. **Assert a fact** — write structured knowledge to the node.
2. **Recall** — retrieve relevant facts using hybrid search.
3. **Subscribe** — watch for new facts in real time.

**Prerequisites:**

- A running Stigmem node at `http://localhost:8765` (see [Installation](./installation))
- An API key (`STIGMEM_API_KEY` environment variable)

---

## Python

### Install

```bash
pip install stigmem
```

### Assert, recall, subscribe

```python
import os
from stigmem import StigmemClient, string_value

client = StigmemClient(
    url="http://localhost:8765",
    api_key=os.environ["STIGMEM_API_KEY"],
)

# 1. Assert a fact
fact = client.assert_fact(
    entity="user:alice",
    relation="memory:role",
    value=string_value("engineer"),
    source="agent:onboarding",
    scope="local",
)
print(f"Asserted fact {fact.id} (CID: {fact.cid})")

# 2. Recall relevant facts
result = client.recall("What is Alice's role?", scope="local", token_budget=1000)
for sf in result.facts:
    print(f"  [{sf.score:.3f}] {sf.fact.entity} — {sf.fact.relation}: {sf.fact.value}")

# 3. Subscribe to new facts (blocking — Ctrl+C to stop)
def on_facts(batch):
    for f in batch:
        print(f"  New: {f.entity} {f.relation}")

client.subscribe_scope("local", on_facts, interval_s=5.0)
```

### Async variant

```python
import asyncio
import os
from stigmem import AsyncStigmemClient, string_value

async def main():
    async with AsyncStigmemClient(
        url="http://localhost:8765",
        api_key=os.environ["STIGMEM_API_KEY"],
    ) as client:
        fact = await client.assert_fact(
            entity="user:bob",
            relation="memory:team",
            value=string_value("platform"),
            source="agent:onboarding",
            scope="local",
        )
        print(f"Asserted: {fact.id}")

        result = await client.recall("Bob's team", scope="local", token_budget=500)
        print(f"Recalled {len(result.facts)} facts, used {result.tokens_used} tokens")

asyncio.run(main())
```

---

## TypeScript

### Install

```bash
npm install stigmem-ts
# or
pnpm add stigmem-ts
```

### Assert, recall, subscribe

```ts
import { StigmemClient, sv } from "stigmem-ts";

const client = new StigmemClient({
  url: "http://localhost:8765",
  apiKey: process.env.STIGMEM_API_KEY,
});

// 1. Assert a fact
const fact = await client.assertFact(
  "user:alice",
  "memory:role",
  sv("engineer"),
  "agent:onboarding",
  { scope: "local" },
);
console.log(`Asserted fact ${fact.id}`);

// 2. Recall relevant facts
const result = await client.recall("What is Alice's role?", {
  scope: "local",
  token_budget: 1000,
});
for (const sf of result.facts) {
  console.log(`  [${sf.score.toFixed(3)}] ${sf.fact.entity} — ${sf.fact.relation}`);
}

// 3. Subscribe to new facts (async generator)
const ac = new AbortController();
setTimeout(() => ac.abort(), 30_000); // stop after 30s

for await (const batch of client.subscribeScope("local", {
  intervalMs: 5_000,
  signal: ac.signal,
})) {
  console.log(`  ${batch.length} new fact(s)`);
  for (const f of batch) {
    console.log(`    ${f.entity} ${f.relation}`);
  }
}
```

---

## Go

### Install

```bash
go get github.com/eidetic-labs/stigmem-go@latest
```

### Assert, recall, subscribe

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	stigmem "github.com/eidetic-labs/stigmem-go"
)

func main() {
	c := stigmem.New("http://localhost:8765",
		stigmem.WithAPIKey(os.Getenv("STIGMEM_API_KEY")),
	)
	ctx := context.Background()

	// 1. Assert a fact
	fact, err := c.AssertFact(ctx,
		"user:alice", "memory:role",
		stigmem.StringValue("engineer"),
		"agent:onboarding",
		stigmem.WithScope(stigmem.ScopeLocal),
	)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Asserted fact %s\n", fact.ID)

	// 2. Recall relevant facts
	recall, err := c.Recall(ctx, "What is Alice's role?",
		stigmem.RecallInScope(stigmem.ScopeLocal),
		stigmem.RecallTokenBudget(1000),
	)
	if err != nil {
		log.Fatal(err)
	}
	for _, sf := range recall.Facts {
		fmt.Printf("  [%.3f] %s — %s\n", sf.Score, sf.Fact.Entity, sf.Fact.Relation)
	}

	// 3. Subscribe to new facts (channel-based)
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	ch := c.Subscribe(ctx, stigmem.ScopeLocal,
		stigmem.SubscribeInterval(5*time.Second),
	)
	for batch := range ch {
		fmt.Printf("  %d new fact(s)\n", len(batch))
		for _, f := range batch {
			fmt.Printf("    %s %s\n", f.Entity, f.Relation)
		}
	}
}
```

---

## What you just did

In each language, you completed the core Stigmem workflow:

| Step | Endpoint | What it does |
|------|----------|-------------|
| Assert | `POST /v1/facts` | Writes a structured (entity, relation, value) triple with provenance |
| Recall | `POST /v1/recall` | Hybrid search (BM25 + vector + graph) that packs results into a token budget |
| Subscribe | `GET /v1/facts` (polling) | Watches a scope for new facts and delivers batches |

Each fact you asserted received a UUID (`id`) and a content identifier (`cid`) — see the [Content Addressing guide](../concepts/facts/content-addressing) for how CIDs enable deduplication and cross-node citation.

---

## Next steps

- [Recall guide](../concepts/recall/) — weight tuning, memory card fast-path, depth control
- [Time-Travel Queries](../concepts/lifecycle/time-travel) — query facts as they existed at a past timestamp
- [RTBF Tombstones](../concepts/lifecycle/rtbf) — entity erasure for GDPR/CCPA compliance
- [Observability](../operators/observability/) — Prometheus metrics and OpenTelemetry tracing
- [TypeScript SDK Reference](../sdks/typescript) — full API reference
- [Go SDK Reference](../sdks/go) — full API reference
- [Python SDK Reference](../sdks/python) — full API reference
