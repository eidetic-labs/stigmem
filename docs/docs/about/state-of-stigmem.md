---
id: state-of-stigmem
title: State of Stigmem
sidebar_label: State of Stigmem
description: Current-state narrative — what Stigmem is, why it exists, what we built, and where it's going.
---

# State of Stigmem

*Last updated: 2026-05-04. Audience: board, prospective hires, external readers.*

---

## What is Stigmem?

Stigmem is an open, federated knowledge protocol: a shared layer where AI agents and humans store typed, traceable facts that travel across tools, platforms, and organizations. Each fact is an immutable record — `(entity, relation, value, source, timestamp, confidence, scope)` — written once, queryable forever, with full provenance and a defined expiry. Think of it as the email model applied to structured knowledge: every node is self-hosted and sovereign, nodes peer with each other under explicit permission, and any agent or application that speaks JSON over HTTP can read from and write to the fabric.

Stigmem does not replace company orchestration platforms, agent runtimes, or tool protocols. It sits *above* them — the shared cognitive layer they all reason over.

---

## Why does it exist?

The motivation is a set of daily-felt frictions observed running an agent-intensive company:

1. **Memories are siloed per-agent.** Every agent writes to its own memory directory. When the CEO tells the CTO something, the CTO must manually transcribe it into their own memory — lossily. There is no shared brain.
2. **No shared decision ledger.** When the board redirects strategy, every agent must be re-briefed individually. The change should propagate as a fact in the shared substrate, not as the CEO's labor.
3. **Preferences don't follow the user.** Every new agent that a board member works with re-learns preferences from scratch. Terse responses, plain language, no exclamation points — each agent must rediscover this.
4. **No portability across company boundaries.** An agent at one company and an agent at another share zero context about the same underlying entities (customers, projects, decisions) even when it would be appropriate for them to do so.
5. **Knowledge decays silently.** A memory written yesterday reads as true today even when the world has changed. No one is checking.
6. **No confidence calibration.** When an agent says "this works," there is no way to tell whether that claim is certain or a guess. The wire carries no signal.
7. **Provenance is missing.** When an agent cites a fact, there is no audit trail: was that from a comment, a code read, or inference? Nothing is traceable to the source.

Memory architecture per-agent patches around this; a *shared substrate* solves it. Stigmem is that substrate.

---

## Where are we today?

Phases 0 through 6 are complete as of 2026-05-02. Phase 7 (substrate, v0.9) has started. Phase 6 (public beta) shipped decay semantics, synthesis, N-node federation soak, cursor-checkpoint recovery, entity naming rules, and lint semantics.

### Phase 0 — Scoping Sprint ✓

**What shipped:** A working v0.1 prototype (200 lines, FastAPI+SQLite), the first spec draft (`stigmem-spec-v0.2.md`), a shadow migration of the CEO's `MEMORY.md` into the prototype as a dogfood test, and a read-back of the Paperclip and OpenClaw public surfaces. The surface read-back established what Stigmem should align with and where it deliberately diverges.

**Exit decision:** Board approved Phase 1 with a sharpened thesis. Phase 0 confirmed the primitive is real — the seven frictions exist, the fact model could represent them, and no existing tool (MCP, Paperclip, OpenClaw PARA memory) fills the gap.

### Phase 1 — Public RFC ✓

**What shipped:** Public GitHub repo (`Eidetic-Labs/stigmem`), spec v0.3 published with federation as an open community-feedback stub, RFC scaffolding (issue templates, CONTRIBUTING.md), and ≥2 external contributors with merged PRs.

**Key framing decision (board-confirmed):** README must not frame Stigmem as "the Paperclip memory layer" or imply OpenClaw endorsement. Stigmem stands alone as an open protocol. Engagement with Paperclip and OpenClaw teams is deferred to Phase 4 adapters and Phase 6 public beta — when there is something earned to show.

### Phase 2 — Reference Node ✓

**What shipped:** A production-quality single-host reference node (FastAPI + SQLite) implementing the v0.3 spec. Provenance, decay (`valid_until`), and scope enforcement at read and write time. API-key authentication (SHA-256 stored server-side, never the raw key). The `/.well-known/stigmem` metadata endpoint (§5.3). CEO `MEMORY.md` fully migrated and readable via the Stigmem API. Spec v0.4 draft capturing implementation gaps and promoting auth from stub to normative.

### Phase 3 — Federation ✓

**What shipped:** Two nodes can federate. Five commits across ~3 weeks:

| Commit | Delivered |
|--------|-----------|
| `e30ffca` | Spec v0.5 — §6 Federation chapter (handshake, replication, conflict semantics, §11 failure scenarios) |
| `ff5758a` | Federation handshake + pull replication engine (PeerDeclaration, Ed25519 signatures, HLC cursors) |
| `8b2a7e9` | Hotfix: excluded `declaration_sig` from its own signature preimage |
| `7e7854a` | Conflict resolution, scope/source enforcement, all §11 acceptance tests |

**Test count: 29 → 74 (all passing).** All four failure modes automated: split-brain, malicious peer, partial failure, replay attack.

**What the CTO learned that the spec didn't predict:** (1) signing specs must enumerate *excluded* fields, not just included ones — the `declaration_sig` bug would have failed every real handshake; (2) in-process HLC state races under concurrent load without an explicit lock; (3) spec §6.3 has an unaddressed edge case: idempotent re-ingestion of a fact that already created a conflict should be a no-op, not a second conflict record. These are tracked for a v0.5.1 errata pass.

### Phase 4 — Adapters ✓

**What shipped:** Three adapters in `adapters/`: MCP server (TypeScript), OpenClaw/Claude Code adapter (Python), and Paperclip hook adapter (JavaScript). Spec v0.6 was published alongside Phase 4 work, promoting the Adapter ABI to normative (§12) and formalizing the `stigmem://` entity URI scheme (§2.5). CEO agent ran end-to-end on Stigmem with delegation to other agents inheriting context automatically.

### Phase 5 — Synthesis & Hygiene ✓

**What shipped:** Entity naming rules (§2.6) and lint semantics (§14) — `POST /v1/lint` and `lint_scope` MCP tool for surfacing orphaned relations, scope-escalation violations, and low-confidence drift. Spec v0.7 published with §1–12 stable, §2.6 and §14 newly normative.

### Phase 6 — Public Beta ✓

**What shipped:** Decay semantics (§15) — configurable `TTL` and confidence-decay policies, `POST /v1/decay/sweep`. Synthesis (§16) — `POST /v1/synthesis` and `synthesize_scope` MCP tool for confidence-weighted current-state snapshots. N-node federation soak (4-node topology, backpressure and scope propagation invariants in §6.7–6.8). Cursor-checkpoint export/import for bounded DB-loss recovery. Human surface (browser UI) stub shipped as in-progress. Spec v0.8 published.

### Phase 7 — Substrate (in progress)

v0.9 ships three primitives that together form the substrate for the curator dashboard and the connector ecosystem:

- **Memory Garden (§17)** — named, ACL'd partitions of the fact store. Each garden has a `garden_id`, a permission table (admin/writer/reader roles), and garden-tagged facts. Agents and connectors write into gardens; the curator dashboard reads and curates them. The `garden:` namespace prefix is reserved.
- **Source Attestation (§18)** — binds an `entity_uri` to an API key so that every fact written by that key carries a verifiable `attested` field. Three enforcement modes: `enforce` (reject unattested writes), `warn` (log and pass), and `off`. Source Attestation is the trust anchor for the connector ecosystem: third-party integrations write under their own attested identity, and the curator dashboard can filter or quarantine by attestation.
- **Intent Envelope (§4)** — provides `goal`, `constraint`, `preference`, and `handoff` envelope types for richer agent coordination, moving §4 from long-running community-feedback draft toward initial implementation.

**Exit criteria for Phase 7:** v0.9 spec stabilized; curator dashboard prototype running end-to-end on Stigmem; at least one external connector demo using Source Attestation; §17 and §18 promoted to normative.

### Phase 9 — Recall, Graph, and Subscriptions (in progress)

v1.1-draft ships the Recall & Graph primitive (spec §20):

- **Graph adjacency index** (`entity_edges` table) — materialized BFS-ready index of `ref`-type fact edges. Powers multi-hop `GET /v1/graph/neighbors` queries without O(k × |F|) scans.
- **Embedding storage** (`vec_facts`, sqlite-vec) — per-fact FLOAT[768] embeddings using nomic-embed-text-v1.5 via a pluggable adapter. Supports hybrid lexical + vector + graph recall.
- **Recall API** (`POST /v1/recall`) — hybrid ranking with lexical (FTS5/BM25), dense-vector (sqlite-vec ANN), and graph-expansion signals fused with greedy token-budget packing. Spec §20.3.
- **Memory cards materializer** (`GET /v1/cards/{entity_uri}`) — per-entity, per-scope pre-aggregated summaries stored in a `memory_cards` table. Materialised on the stale-on-write / refresh-on-read pattern: every `assert_fact` call marks the entity card stale; the next `recall` or `GET /v1/cards` call re-computes it. Fresh, high-confidence, contradiction-free cards short-circuit raw-fact re-ranking in the recall pipeline (fast-path); cards with contradictions or stale state fall through to full ranking (divergence policy). Python SDK: `MemoryCard` + `client.get_card()`. Spec §20.4.
- **Subscription primitive** (`/v1/subscriptions`) — standing fact-change watches with webhook and wake delivery, circuit breaker (threshold: 10 failures), 24 h replay window, and §17/§19 re-enforcement at delivery time. Spec §20.3–§20.6. Security-reviewed and published 2026-05-04.

---

## Architecture

Stigmem's architecture has three layers, each built in sequence across phases.

### Layer 1 — Single-host node (Phase 2)

A self-contained FastAPI + SQLite process. Exposes a JSON/HTTP API: `POST /v1/facts` to assert, `GET /v1/facts` to query, `GET /v1/facts/:id` to retrieve, `PATCH /v1/facts/:id/confidence` to retract. The `/.well-known/stigmem` endpoint advertises the node's capabilities and federation public key.

The core data model: every fact is a row in a single `facts` table. Writes are append-only — there is no UPDATE. New facts supersede old ones for the same `(entity, relation, scope)` triple by precedence rules (confidence → HLC → contradiction). Expired facts (`valid_until` in the past) are hidden from queries by default but retained in the store.

### Layer 2 — Federated nodes (Phase 3)

Two or more nodes can peer via a signed PeerDeclaration. The handshake uses Ed25519: each node publishes a `federation_pubkey` at `/.well-known/stigmem`; a PeerDeclaration is a JSON document signed by the declaring node's keypair, specifying which scopes it is willing to share in which direction.

Replication is pull-based: each node runs a background task that periodically fetches new facts from registered peers using an HLC cursor (so replication resumes exactly where it left off, even across node restarts). Push replication exists behind a flag but is not the default path.

**Scope enforcement is absolute:** `local` and `team` facts never cross node boundaries. `company` facts federate only when the active PeerDeclaration explicitly includes `"company"` in `allowed_scopes`. `public` facts federate by default between registered peers.

**Conflicts are first-class:** when two peers assert contradicting values for the same `(entity, relation, scope)` triple, both are retained. The node automatically generates a `stigmem:conflict:*` fact record and exposes it via `GET /v1/conflicts`. Resolution is itself a fact with provenance — a human or agent posts to `POST /v1/conflicts/:id/resolve`, and the resolution is written into the fabric with full audit trail.

### Layer 3 — Adapters (Phase 4, in flight)

Adapters bridge Stigmem to specific agent platforms. The Adapter ABI (spec §12) defines the minimum contract: three environment variables (`STIGMEM_NODE_URL`, `STIGMEM_API_KEY`, `STIGMEM_SOURCE_ENTITY`), an `assert_fact(fact)` write path, and a `query_facts(query, scope)` read path.

- **MCP adapter** (TypeScript): Exposes `stigmem_assert` and `stigmem_query` as MCP tools. Any Claude Code agent with the server in `.mcp.json` gets read/write access to a Stigmem node with no code changes.
- **Paperclip adapter** (JavaScript hook): Wires into Paperclip's `PostToolResult` hook to emit issue lifecycle events (status transitions, assignments, blocker resolutions) as Stigmem facts automatically.
- **OpenClaw adapter** (Python): A drop-in replacement for `MEMORY.md` reads and writes, routing to a Stigmem node. Supports PARA memory type → fact relation mapping.

---

## Why these choices?

The architecture reflects specific deliberate decisions, each sharpened by the Phase 0 surface read-back.

**Why federated, not centralized?** A protocol that can't federate isn't a protocol — it's a feature of one platform. HTTP, email, ActivityPub, and MCP are all open because federation prevents capture. A Stigmem network where every node is self-hosted and sovereign cannot be taken down or monetized behind a lock. The precedents are email (SMTP federation), ActivityPub (Mastodon), and Solid (personal data pods) — not a SaaS API with optional export.

**Why typed atomic facts, not markdown?** The Phase 0 surface read-back showed that Paperclip, OpenClaw PARA memory, and MCP all lack the same four things: typed schema at the content layer, confidence signals, decay/expiry, and provenance chains. Markdown blobs are good for humans reading linearly; they are unusable for agents querying "what do we know about entity X right now with confidence ≥ 0.8?" A typed fact tuple is the minimum required to answer that question.

**Why conflicts are first-class, not silently resolved?** Multi-agent systems will contradict each other. Pretending otherwise (last-writer-wins, or silently dropping the losing fact) corrupts ground truth in ways that are hard to detect and expensive to recover from. By retaining both facts, generating a system `stigmem:conflict:*` record, and requiring explicit resolution with provenance, Stigmem makes disagreement visible and traceable. A resolved conflict is more valuable than a silently correct fact, because it carries the reasoning for the resolution.

**Why entity-scoped, not agent-scoped?** Every existing agent memory system — OpenClaw PARA, per-agent `MEMORY.md` files — is *agent-scoped*: the CEO's memory about project X and the CTO's memory about project X are separate files with no reconciliation. Stigmem is *entity-scoped*: facts about `stigmem://company.example/project/x` belong to that entity, not to whoever wrote them first. Any authorized agent queries and contributes to the same entity's fact set. This is the single most important architectural divergence from existing agent memory, identified in the Phase 0 surface read-back.

**Why not just MCP?** MCP is a tool protocol: stateless, no persistence between calls, no semantic memory, no provenance chain, no federation. It is the correct transport layer *for calling Stigmem* — the MCP adapter ships Stigmem as an MCP server — but MCP alone does not provide the shared fabric. The relationship is complementary, not competing.

---

## What's coming next?

| Phase | Milestone | Status |
|-------|-----------|--------|
| 4 | Adapters (OpenClaw, Paperclip, MCP) + CEO end-to-end dogfood | **Done** |
| 5 | Synthesis & Hygiene — entity naming rules, lint semantics | **Done** |
| 6 | Public Beta — decay, synthesis, N-node soak, cursor-checkpoint recovery, human surface stub | **Done** |
| 7 | Substrate — Memory Garden (§17), Source Attestation (§18), Intent Envelope (§4), curator dashboard | **In progress** |
| 9 | Recall & Graph — graph adjacency index, embeddings (sqlite-vec), recall API, **memory cards materializer**, subscription primitive | **Done** |

Phase 7 is the substrate phase: Memory Garden, Source Attestation, and Intent Envelope form the foundation for the curator dashboard and the connector ecosystem. Phase 9 (v1.1) adds the Recall & Graph primitive — the recall endpoint, memory cards materializer (stale-on-write + fast-path), and subscription primitive are all shipped and security-reviewed as of 2026-05-04. v1.0 GA (multi-tenant, OIDC/SSO, billing, public launch) follows Phase 7.

---

## What we are not building

Load-bearing non-targets, unchanged:

- **A new agent platform.** OpenClaw/Claude Code owns the agent runtime. We are not building a competing agent.
- **A company OS or multi-agent orchestration layer.** Paperclip owns this. We sit *upstream* of Paperclip, not alongside it.
- **A vertical agent product.** Support agent, compliance agent, bookkeeping agent — all parked until post-v1.0.
- **A chatbot of any kind.**
- **An in-house compliance or GRC tool.** Stigmem is the protocol layer; compliance application logic is out of scope.
- **Anything that competes with Paperclip or OpenClaw on their core surfaces.** Stigmem makes both more valuable by being the shared substrate they reason over. Competition with either would undermine the protocol's value proposition.

These are not items that got cut — they are deliberate non-targets. Naming them explicitly keeps scope creep visible as the project grows.

---

## Repo map

```
stigmem/
├── spec/                       ← canonical spec (v0.2 → v0.8-draft)
│   ├── stigmem-spec-v0.2.md    ← stable baseline
│   ├── stigmem-spec-v0.3-draft.md
│   ├── stigmem-spec-v0.4-draft.md
│   ├── stigmem-spec-v0.5-draft.md
│   ├── stigmem-spec-v0.6-draft.md
│   ├── stigmem-spec-v0.7-draft.md
│   ├── stigmem-spec-v0.9-draft.md  ← current working draft
│   └── README.md               ← spec status table
├── node/                       ← reference node (FastAPI + SQLite)
│   ├── migrations/             ← SQL schema migrations
│   └── tests/                  ← integration tests (facts, federation, failure modes)
├── adapters/                   ← platform adapters
│   ├── mcp/                    ← MCP server (TypeScript)
│   ├── openclaw/               ← OpenClaw/Claude Code adapter (Python)
│   └── paperclip/              ← Paperclip hook adapter (JavaScript)
├── docs/                       ← Docusaurus 3 documentation site
└── CONTRIBUTING.md             ← RFC process for spec contributions
```

---

