---
id: memory-garden
title: Memory Garden
sidebar_label: Memory Garden
sidebar_position: 1
description: What Memory Garden is, why it exists, and how it differs from closed-pool agent memory products.
---

# Memory Garden

**Memory Garden** is Stigmem's public identity: an open, federated knowledge fabric where AI agents and humans store facts that *travel* — across tools, runtimes, companies, and deployments — with full provenance and zero vendor lock-in.

---

## The problem with closed memory

Every major agent memory product today — mem0, Letta, Zep — is a closed pool. Your agent's memory lives in one vendor's infrastructure, speaks that vendor's API, and stays inside that vendor's boundaries.

This means:

- When you add a second agent framework, you start from scratch. There is no shared brain.
- When you cross a team or company boundary, memory stays behind.
- When the vendor changes their API or pricing, your memory is hostage.
- When an agent makes a decision, there is no audit trail linking it to the facts it relied on.

These are not edge cases. They are the daily frictions of running any multi-agent system at scale.

---

## What Memory Garden does differently

Memory Garden stores every fact as an immutable, typed record:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

| Field | What it does |
|-------|-------------|
| `entity` | What the fact is about — `user:alice`, `company:acme`, `project:loom` |
| `relation` | What kind of claim this is — `memory:role`, `roadmap:status`, `preference:timezone` |
| `value` | The typed value: string, number, boolean, datetime, or a reference to external content |
| `source` | Who asserted it — `agent:ceo`, `user:alice`, `system:intake` |
| `timestamp` | When it was written — immutable, set by the node |
| `confidence` | How certain the source is — `1.0` = certain, `0.5` = uncertain, `0.0` = retracted |
| `scope` | Visibility boundary — `local`, `team`, `company`, or `public` (federatable) |

Every fact is written once and never mutated. Updates are new facts. The latest fact for an `(entity, relation, scope)` triple wins — unless two sources contradict each other, in which case both facts are surfaced and the contradiction is flagged explicitly for resolution.

---

## How it differs from the alternatives

| | Memory Garden | mem0 | Letta | Zep |
|---|---|---|---|---|
| **License** | Apache 2.0 | Proprietary SaaS | Proprietary | Proprietary SaaS |
| **Self-hostable** | Yes — single binary | No (enterprise tier) | Partial | Yes (complex) |
| **Federated** | Yes — nodes peer with signed handshakes | No | No | No |
| **Provenance on every fact** | Yes | No | No | Temporal edges only |
| **Contradictions surfaced** | Yes — first-class conflict records | No | No | No |
| **Entity-scoped facts** | Yes — facts belong to entities, not agents | No | No | No |
| **Open spec** | Yes — Apache 2.0, community namespace registry | No | No | No |
| **Platform-agnostic** | Yes — MCP, OpenClaw, Paperclip adapters | No — custom SDK | No — Letta-native | No — Zep-native |

**Entity-scoped vs. agent-scoped** is the most important architectural difference. In every existing memory system, the CEO's memory about `project:loom` and the CTO's memory about `project:loom` are separate stores with no reconciliation path. In Memory Garden, those facts live in the same entity namespace — any authorized agent queries and contributes to the same set of facts about the same entity. There is one ground truth, not N copies of it.

---

## The Open Connector Mesh

Memory Garden ships with an **open connector mesh**: a set of adapters and integrations that let agents read from and write to the fabric without per-agent plumbing.

**Platform adapters** bridge Memory Garden to where your agents already live:

| Adapter | What it does |
|---------|-------------|
| **MCP adapter** | Exposes `stigmem_assert` and `stigmem_query` as MCP tools — any Claude Code agent with the server in `.mcp.json` gets full read/write access |
| **Paperclip adapter** | Wires into Paperclip's hook system to emit issue lifecycle events (checkout, status changes, blockers) as facts automatically |
| **OpenClaw adapter** | Drop-in replacement for PARA `MEMORY.md` reads and writes, routing to a Memory Garden node |

**Business integrations** ground agent facts in real data:

- Shopify — product catalog, order events, customer state
- Stripe — billing events, subscription state, payment status
- GitHub — PR status, issue events, CI results
- AWS — infrastructure events, deployment facts
- Google Workspace — calendar, Drive, Gmail signals
- WooCommerce — order and inventory state

Connectors run bidirectionally. Agents don't just read from external systems; they can write decisions back as facts into the fabric, so the next agent or human that queries the same entity sees the full history.

---

## Federated by design

Memory Garden nodes can peer with each other using a signed handshake protocol. Two nodes exchange `PeerDeclaration` documents — signed with Ed25519 keys — specifying exactly which scopes they share and in which direction.

Once peered, `public`-scoped facts replicate between nodes via cursor-based pull replication. Facts with `scope=local` or `scope=team` never leave their origin node. `company`-scoped facts only cross a boundary if the active peer declaration explicitly includes it.

**Provenance is preserved across federation.** A fact replicated from another node retains its original `source`, `timestamp`, and `confidence`. The relay chain is transparent. An agent on Node B can always see that a fact originated from `agent:ceo` on Node A — not from Node A itself.

This is the same model as email federation (SMTP), the Fediverse (ActivityPub), and personal data pods (Solid): every node is self-hosted and sovereign. There is no central registry, no central operator, no single point that can be taken down or monetized behind a paywall.

---

## Getting started

```bash
# Run a Memory Garden node locally
pip install stigmem-node
stigmem-node

# Assert your first fact
curl -X POST http://localhost:8765/v1/facts \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "user:alice",
    "relation": "memory:role",
    "value": { "type": "string", "v": "Lead Engineer" },
    "source": "agent:onboarding",
    "confidence": 1.0,
    "scope": "company"
  }'

# Query it back
curl "http://localhost:8765/v1/facts?entity=user:alice&relation=memory:role"
```

See the [Quickstart guide](../quickstart) for a full walkthrough including the MCP adapter setup and your first federated peer.

---

## What Memory Garden is not

- **Not a generic RAG system.** Memory Garden does retrieval — `POST /v1/recall` fuses lexical (FTS5/BM25), dense vector (sqlite-vec ANN), and graph-expansion signals — but the unit of retrieval is a *typed atomic fact*, not an opaque text chunk. Each embedding has an explicit `(entity, relation, value)` contract. Recall results are filterable by entity, scope, confidence, and `as_of`; chunks are not. A memory-card fast path lets 80–90% of recalls short-circuit raw-fact ranking entirely. See [How recall works](../../build/guides/recall) for the full pipeline.
- **Not an agent runtime.** Memory Garden sits above agent platforms (Claude Code, Paperclip, LangChain) and below the open internet. It does not orchestrate agents or run tools.
- **Not a compliance tool.** The provenance trail Memory Garden produces is useful for audit — but building GRC workflows on top of it is the job of a separate application layer.
- **Not a general-purpose database.** Facts are append-only knowledge records — typed, scoped, provenance-tagged, decay-aware. For arbitrary mutable state, use a real database. Use Memory Garden for knowledge that needs to travel and carry provenance.

---

*Memory Garden / Stigmem — Apache 2.0. [Spec](../../reference/spec) · [GitHub](https://github.com/eidetic-labs/stigmem) · [Contributing](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md)*
