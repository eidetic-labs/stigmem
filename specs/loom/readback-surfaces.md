# Readback — Paperclip, OpenClaw, and Peer Landscape
## What Loom Should Align With vs. Diverge From

**Status:** Phase 0 research. Sources: public GitHub repos, docs, blog posts only.  
**Date:** 2026-05-01

---

## Paperclip

**What it is:** Open-source (MIT), self-hosted orchestration platform for running teams of AI agents as a structured business. Org charts, budgets, goal hierarchies, approval gates, task assignment — a control plane for AI-native companies. Runs on Node.js + embedded Postgres. ([github.com/paperclipai/paperclip](https://github.com/paperclipai/paperclip))

**Memory/context model:** Context is task-scoped and hierarchical — not a shared knowledge store. Agents resume the same task context across heartbeats (no cold-start). Context flows upward through parent tasks → projects → company goals so agents know "why." The roadmap explicitly lists "Memory / Knowledge" as a planned but not-yet-shipped feature. No current API for agents to query or write shared facts cross-task.

**Protocol surface:** Tasks + comments are the built-in inter-agent communication primitive. Agents authenticate via bearer API keys. No open wire protocol for knowledge exchange is documented.

**→ Align with Loom:**
- Task-as-context model: Loom's intent envelope should map naturally onto Paperclip task fields (goal, constraint, deference, escalation).
- Adapter pattern: bring-your-own-agent. Loom's Phase 4 Paperclip adapter should be a thin bridge, not a fork.
- Heartbeat/durable-context model: Loom facts should persist across heartbeats by design — same philosophy.

**→ Diverge from Loom:**
- Loom provides the missing shared-memory layer: a queryable, federated fact store that Paperclip-style orchestrators can read/write, rather than context that dies with a task thread.
- Loom is upstream (layer below Paperclip, above open internet). Not competitive; complementary.
- Pre-coordination with Paperclip leadership is non-negotiable before any public spec work.

---

## OpenClaw

**What it is:** Open-source (MIT) personal AI assistant that operates through chat channels users already use (WhatsApp, Telegram, Slack, Discord, 20+ others). Most-starred GitHub repo in history (~355k stars as of April 2026). Executes real-world actions: calendar, inbox, smart home, flight booking. ([github.com/openclaw/openclaw](https://github.com/openclaw/openclaw))

**Memory/context model:** Advertises "persistent memory that becomes uniquely yours." The companion OSS memory backend is [NevaMind-AI/memU](https://github.com/NevaMind-AI/memU) — hierarchical file system with vector-indexed (RAG) + LLM retrieval + knowledge graph (entity extraction + graph traversal, added 2026). No formal open memory protocol is documented in OpenClaw itself.

**Protocol surface:** OpenClaw uses a versioned internal Gateway protocol (additive-first, versioned on breaking changes). No published inter-agent or knowledge-exchange wire spec found publicly.

**→ Align with Loom:**
- Channel-agnostic delivery model: Loom's intent envelope should be channel-neutral.
- Assumption that agents are persistent and proactive, not stateless: Loom's decay model aligns with this.
- memU's knowledge-graph layer is a near-neighbor of Loom's fact shape — worth studying as we finalize relation namespace design.

**→ Diverge from Loom:**
- OpenClaw memory is per-user and siloed. Loom's value is the **shared** substrate across users, agents, and companies.
- memU is a retrieval engine (RAG + graph traversal). Loom is a protocol layer: open, federated, source-of-truth-oriented, not retrieval-optimized.
- Pre-coordination with OpenClaw leadership is non-negotiable before any public spec work.

---

## Peer Landscape

| Project | What it is | Memory shape | Open protocol |
|---------|------------|-------------|---------------|
| **Letta** (ex-MemGPT) | Stateful agent runtime (Apache-2.0, ~letta-ai/letta) | Three-tier OS-inspired: core (in-context), archival (vector), recall (conversation). REST API + multi-agent server. | No federation protocol. |
| **Mem0** | Universal memory layer for AI agents (Apache-2.0, ~mem0ai/mem0, ~48k stars) | Hybrid: vector + graph + key-value, scoped to user/session/agent. REST + Python SDK. | No published federation. |
| **Zep / Graphiti** | Temporal knowledge graph engine (Apache-2.0, ~getzep/graphiti, ~20k stars) | Facts are **edges with `valid_at`/`invalid_at` timestamps**. arXiv paper published Jan 2025. | MCP server shipped. Closest public art to Loom's fact shape. |
| **Cognee** | Knowledge engine via ECL pipeline (Apache-2.0, ~topoteretes/cognee) | 38+ source types → combined vector + graph store. $7.5M seed, 70+ companies in production. | MCP tools exposed. |
| **LangMem** | LangChain long-term memory SDK | Episodic, semantic, procedural (agents update their own system prompt). | No standalone protocol; LangChain-coupled. |

**Key observations:**
1. **Zep/Graphiti is closest to Loom's fact shape.** `valid_at`/`invalid_at` directly addresses Gap 3 (confidence ≠ validity) from our shadow migration. We should study their temporal edge model before finalizing §3.3 of the spec.
2. **MCP is emerging as the de facto tool protocol.** Both Zep and Cognee ship MCP servers. Loom's Phase 4 MCP adapter is the right call — don't build a competing tool protocol.
3. **No project has published an open federation protocol.** This is Loom's specific bet: an ActivityPub/SMTP-style federation handshake for knowledge nodes. None of the peers have shipped or specced this.
4. **All peer memory stores are per-agent or per-user.** Cross-company, cross-agent federation is unoccupied ground.

---

## Design-Partner Candidates (D4)

Three candidates for outreach. All are building in adjacent space, have public profiles, and have expressed interest in open memory/protocol design:

1. **Daniel Chalef** — Founder, Zep AI; builder of Graphiti (temporal knowledge graph, MCP server, Apache-2.0). Most technically aligned: temporal edges, open-source, federated-friendly design. GitHub: [`danielchalef`](https://github.com/danielchalef). Blog: [blog.getzep.com](https://blog.getzep.com).

2. **Charles Packer** — Co-founder, Letta (ex-MemGPT). Actively publishing on stateful agent memory and context management protocols; open to external collaboration via Letta's public community. GitHub: [`cpacker`](https://github.com/cpacker).

3. **topoteretes** (Cognee) — GitHub org behind Cognee; MCP-based memory infra, $7.5M funded, active open-source community. Reach via GitHub Issues or public Discord at [github.com/topoteretes/cognee-community](https://github.com/topoteretes/cognee-community).

**Constraint reminder:** Phase 0 interview scope is reading public surfaces + cold outreach only. No Paperclip or OpenClaw outreach in Phase 0 — that coordination happens at the holdco level before any public spec work.

---

## Summary: Where Loom Stands

| Axis | Loom's position |
|------|-----------------|
| Layer | Above company orchestrators (Paperclip), below open internet |
| vs. Paperclip | Complementary — fills their explicit roadmap gap |
| vs. OpenClaw | Complementary — replaces per-user silo with shared substrate |
| vs. Letta / Mem0 | Adjacent — we share the "persistent agent memory" bet; Loom's diff is federation + open protocol |
| vs. Zep/Graphiti | Closest technical neighbor — their temporal edge model should inform Loom §3.3 |
| vs. Cognee | Less overlap — they're a knowledge extraction engine, we're a protocol layer |
| Unoccupied ground | Open, federated, cross-company knowledge protocol. Nobody has shipped or specced this. |

*Research by CTO, Phase 0 — [ACM-19](/ACM/issues/ACM-19). Sources are public GitHub/docs only.*
