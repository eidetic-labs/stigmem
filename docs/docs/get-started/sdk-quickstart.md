---
title: "Tutorial: SDK Quickstart"
sidebar_label: SDK Quickstart
description: Assert a fact, run a recall, and subscribe to changes — in Python, TypeScript, and Go.
audience: Integrator
---

# Tutorial: SDK Quickstart

<p className="stigmem-meta"><span>5 min hands-on</span><span>For integrators</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll do**

Three operations that cover the core Stigmem workflow — assert a fact,
recall relevant facts with hybrid search, subscribe to a scope —
in Python, TypeScript, and Go. Each language section is self-contained.

</div>

<div className="stigmem-keypoint">

**Three operations · same shape across languages.**

The SDK surfaces share the same assert / recall / subscribe vocabulary
across all three languages. Each language section below is independent
— pick yours and follow along.

</div>

## Prerequisites

<div className="stigmem-fields">

<div>
<dt>Requirement</dt>
<dt><span className="stigmem-fields__type">Notes</span></dt>
<dd>Where to set</dd>
</div>

<div>
<dt>Running node</dt>
<dt><span className="stigmem-fields__type">localhost:8765</span></dt>
<dd>See <a href="./installation">Installation</a>.</dd>
</div>

<div>
<dt>API key</dt>
<dt><span className="stigmem-fields__type">env var</span></dt>
<dd><code>STIGMEM_API_KEY</code> in the environment running your SDK code.</dd>
</div>

</div>

## What each operation does

<div className="stigmem-grid">

<div>
<h4>Assert</h4>
<p>Write a structured <code>(entity, relation, value)</code> triple with provenance to the node — <code>POST /v1/facts</code>.</p>
</div>

<div>
<h4>Recall</h4>
<p>Hybrid search (BM25 + vector + graph) that packs results into a token budget — <code>POST /v1/recall</code>.</p>
</div>

<div>
<h4>Subscribe</h4>
<p>Watch a scope for new facts and deliver them in batches — <code>GET /v1/facts</code> polling.</p>
</div>

</div>

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

## What you just did

In each language, you completed the core Stigmem workflow:

<div className="stigmem-fields">

<div>
<dt>Step</dt>
<dt><span className="stigmem-fields__type">Endpoint</span></dt>
<dd>What it does</dd>
</div>

<div>
<dt>Assert</dt>
<dt><span className="stigmem-fields__type"><code>POST /v1/facts</code></span></dt>
<dd>Writes a structured (entity, relation, value) triple with provenance.</dd>
</div>

<div>
<dt>Recall</dt>
<dt><span className="stigmem-fields__type"><code>POST /v1/recall</code></span></dt>
<dd>Hybrid search (BM25 + vector + graph) that packs results into a token budget.</dd>
</div>

<div>
<dt>Subscribe</dt>
<dt><span className="stigmem-fields__type"><code>GET /v1/facts</code> (polling)</span></dt>
<dd>Watches a scope for new facts and delivers batches.</dd>
</div>

</div>

Each fact you asserted received a UUID (`id`) and a content
identifier (`cid`) — see the
[content addressing guide](../concepts/facts/content-addressing) for
how CIDs enable deduplication and cross-node citation.

## What's next

<div className="stigmem-next">

<a href="../concepts/recall/">
<strong>Concept</strong>
<span>Recall</span>
<small>Weight tuning, memory-card fast path, depth control.</small>
</a>

<a href="../operators/observability/">
<strong>Operate</strong>
<span>Observability</span>
<small>Prometheus metrics and OpenTelemetry tracing.</small>
</a>

<a href="../sdks/python">
<strong>Reference</strong>
<span>Python SDK</span>
<small>Full API reference.</small>
</a>

<a href="../sdks/typescript">
<strong>Reference</strong>
<span>TypeScript SDK</span>
<small>Full API reference.</small>
</a>

</div>
