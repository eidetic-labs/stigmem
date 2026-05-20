---
title: Memory Garden
sidebar_label: Memory Garden
sidebar_position: 1
description: What Memory Garden is, why it exists, and how it differs from closed-pool agent memory products.
---

# Memory Garden

<p className="stigmem-meta"><span>4 min read</span><span>Evaluator · Integrator · Curator</span><span>Public identity</span></p>

<div className="stigmem-lead">

**Memory Garden** is Stigmem's public identity: an open, federated
knowledge fabric where AI agents and humans store facts that
*travel* — across tools, runtimes, companies, and deployments — with
full provenance and zero vendor lock-in.

</div>

## The problem with closed memory

Every major agent memory product today — mem0, Letta, Zep — is a
closed pool. Your agent's memory lives in one vendor's
infrastructure, speaks that vendor's API, and stays inside that
vendor's boundaries.

<div className="stigmem-grid">

<div><h4>No shared brain across frameworks</h4><p>When you add a second agent framework, you start from scratch.</p></div>
<div><h4>Memory stays behind at boundaries</h4><p>When you cross a team or company boundary, memory stays behind.</p></div>
<div><h4>Vendor hostage</h4><p>When the vendor changes their API or pricing, your memory is hostage.</p></div>
<div><h4>No audit trail</h4><p>When an agent makes a decision, there is no audit trail linking it to the facts it relied on.</p></div>

</div>

These are not edge cases. They are the daily frictions of running any
multi-agent system at scale.

## What Memory Garden does differently

Memory Garden stores every fact as an immutable, typed record:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Carries</span></dt>
<dd>What it does</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">subject</span></dt>
<dd>What the fact is about — <code>user:alice</code>, <code>company:acme</code>, <code>project:loom</code>.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">predicate</span></dt>
<dd>What kind of claim this is — <code>memory:role</code>, <code>roadmap:status</code>, <code>preference:timezone</code>.</dd>
</div>

<div>
<dt><code>value</code></dt>
<dt><span className="stigmem-fields__type">object</span></dt>
<dd>The typed value: string, number, boolean, datetime, or a reference to external content.</dd>
</div>

<div>
<dt><code>source</code></dt>
<dt><span className="stigmem-fields__type">provenance</span></dt>
<dd>Who asserted it — <code>agent:ceo</code>, <code>user:alice</code>, <code>system:intake</code>.</dd>
</div>

<div>
<dt><code>timestamp</code></dt>
<dt><span className="stigmem-fields__type">when</span></dt>
<dd>Immutable, set by the node.</dd>
</div>

<div>
<dt><code>confidence</code></dt>
<dt><span className="stigmem-fields__type">certainty</span></dt>
<dd><code>1.0</code> = certain, <code>0.5</code> = uncertain, <code>0.0</code> = retracted.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">visibility</span></dt>
<dd><code>local</code>, <code>team</code>, <code>company</code>, or <code>public</code> (federatable).</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Every fact is written once and never mutated.**

Updates are new facts. The latest fact for an
<code>(entity, relation, scope)</code> triple wins — unless two
sources contradict each other, in which case both facts are surfaced
and the contradiction is flagged explicitly for resolution.

</div>

## How it differs from the alternatives

<div className="stigmem-fields">

<div>
<dt>Capability</dt>
<dt><span className="stigmem-fields__type">Memory Garden</span></dt>
<dd>mem0 · Letta · Zep</dd>
</div>

<div>
<dt>License</dt>
<dt><span className="stigmem-fields__type">Apache 2.0</span></dt>
<dd>Proprietary SaaS · Proprietary · Proprietary SaaS</dd>
</div>

<div>
<dt>Self-hostable</dt>
<dt><span className="stigmem-fields__type">Yes — single binary</span></dt>
<dd>No (enterprise tier) · Partial · Yes (complex)</dd>
</div>

<div>
<dt>Federated</dt>
<dt><span className="stigmem-fields__type">Yes — signed handshakes</span></dt>
<dd>No · No · No</dd>
</div>

<div>
<dt>Provenance on every fact</dt>
<dt><span className="stigmem-fields__type">Yes</span></dt>
<dd>No · No · Temporal edges only</dd>
</div>

<div>
<dt>Contradictions surfaced</dt>
<dt><span className="stigmem-fields__type">Yes — first-class conflict records</span></dt>
<dd>No · No · No</dd>
</div>

<div>
<dt>Entity-scoped facts</dt>
<dt><span className="stigmem-fields__type">Yes — facts belong to entities, not agents</span></dt>
<dd>No · No · No</dd>
</div>

<div>
<dt>Open spec</dt>
<dt><span className="stigmem-fields__type">Yes — Apache 2.0, community namespace registry</span></dt>
<dd>No · No · No</dd>
</div>

<div>
<dt>Platform-agnostic</dt>
<dt><span className="stigmem-fields__type">Yes — MCP, OpenClaw, Paperclip adapters</span></dt>
<dd>Custom SDK · Letta-native · Zep-native</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Entity-scoped vs. agent-scoped is the most important architectural difference.**

In every existing memory system, the CEO's memory about
<code>project:loom</code> and the CTO's memory about
<code>project:loom</code> are separate stores with no reconciliation
path. In Memory Garden, those facts live in the same entity namespace
— any authorized agent queries and contributes to the same set of
facts about the same entity. There is one ground truth, not N copies
of it.

</div>

## The Open Connector Mesh

Memory Garden ships with an **open connector mesh**: a set of
adapters and integrations that let agents read from and write to the
fabric without per-agent plumbing.

### Platform adapters

<div className="stigmem-fields">

<div>
<dt>Adapter</dt>
<dt><span className="stigmem-fields__type">Connects to</span></dt>
<dd>What it does</dd>
</div>

<div>
<dt><strong>MCP adapter</strong></dt>
<dt><span className="stigmem-fields__type">Claude Code agents</span></dt>
<dd>Exposes <code>stigmem_assert</code> and <code>stigmem_query</code> as MCP tools — any Claude Code agent with the server in <code>.mcp.json</code> gets full read/write access.</dd>
</div>

<div>
<dt><strong>Paperclip adapter</strong></dt>
<dt><span className="stigmem-fields__type">Paperclip workflow</span></dt>
<dd>Wires into Paperclip's hook system to emit issue lifecycle events (checkout, status changes, blockers) as facts automatically.</dd>
</div>

<div>
<dt><strong>OpenClaw adapter</strong></dt>
<dt><span className="stigmem-fields__type">PARA <code>MEMORY.md</code></span></dt>
<dd>Drop-in replacement for PARA <code>MEMORY.md</code> reads and writes, routing to a Memory Garden node.</dd>
</div>

</div>

### Business integrations

Connectors run bidirectionally. Agents don't just read from external
systems; they can write decisions back as facts into the fabric, so
the next agent or human that queries the same entity sees the full
history.

<div className="stigmem-grid">

<div><h4>Shopify</h4><p>Product catalog, order events, customer state.</p></div>
<div><h4>Stripe</h4><p>Billing events, subscription state, payment status.</p></div>
<div><h4>GitHub</h4><p>PR status, issue events, CI results.</p></div>
<div><h4>AWS</h4><p>Infrastructure events, deployment facts.</p></div>
<div><h4>Google Workspace</h4><p>Calendar, Drive, Gmail signals.</p></div>
<div><h4>WooCommerce</h4><p>Order and inventory state.</p></div>

</div>

## Federated by design

Memory Garden nodes can peer with each other using a signed handshake
protocol. Two nodes exchange `PeerDeclaration` documents — signed
with Ed25519 keys — specifying exactly which scopes they share and
in which direction.

<div className="stigmem-fields">

<div>
<dt>Scope</dt>
<dt><span className="stigmem-fields__type">Federation behavior</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>local</code> · <code>team</code></dt>
<dt><span className="stigmem-fields__type">never leave origin node</span></dt>
<dd>No federation under any circumstances.</dd>
</div>

<div>
<dt><code>company</code></dt>
<dt><span className="stigmem-fields__type">cross only via explicit peer declaration</span></dt>
<dd>The active peer declaration must include it.</dd>
</div>

<div>
<dt><code>public</code></dt>
<dt><span className="stigmem-fields__type">replicates by default</span></dt>
<dd>Via cursor-based pull replication.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Provenance is preserved across federation.**

A fact replicated from another node retains its original
<code>source</code>, <code>timestamp</code>, and
<code>confidence</code>. The relay chain is transparent. An agent on
Node B can always see that a fact originated from
<code>agent:ceo</code> on Node A — not from Node A itself.

</div>

This is the same model as email federation (SMTP), the Fediverse
(ActivityPub), and personal data pods (Solid): every node is
self-hosted and sovereign. There is no central registry, no central
operator, no single point that can be taken down or monetized behind
a paywall.

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

See the [Quickstart guide](../get-started) for a full walkthrough
including the MCP adapter setup and your first federated peer.

## What Memory Garden is not

<div className="stigmem-grid">

<div><h4>Not a generic RAG system</h4><p>Memory Garden does retrieval — <code>POST /v1/recall</code> fuses lexical (FTS5/BM25), dense vector (sqlite-vec ANN), and graph-expansion signals — but the unit of retrieval is a <em>typed atomic fact</em>, not an opaque text chunk. Each embedding has an explicit <code>(entity, relation, value)</code> contract.</p></div>
<div><h4>Not an agent runtime</h4><p>Memory Garden sits above agent platforms (Claude Code, Paperclip, LangChain) and below the open internet. It does not orchestrate agents or run tools.</p></div>
<div><h4>Not a compliance tool</h4><p>The provenance trail Memory Garden produces is useful for audit — but building GRC workflows on top of it is the job of a separate application layer.</p></div>
<div><h4>Not a general-purpose database</h4><p>Facts are append-only knowledge records — typed, scoped, provenance-tagged, decay-aware. For arbitrary mutable state, use a real database.</p></div>

</div>

---

*Memory Garden / Stigmem — Apache 2.0. [Spec](../spec/) ·
[GitHub](https://github.com/eidetic-labs/stigmem) ·
[Contributing](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md)*
