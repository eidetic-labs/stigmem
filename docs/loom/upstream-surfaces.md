# Upstream Surfaces: Paperclip + OpenClaw + MCP

**Purpose:** Input to the Loom v0.1 spec. Covers public API surfaces of the platforms Loom sits between, with concrete spec implications derived from each. Written from first-hand observation of both systems — no outreach to teams.

**Parent issue:** [ACM-18](/ACM/issues/ACM-18) · **This issue:** [ACM-21](/ACM/issues/ACM-21) · **Sibling sprint:** [ACM-19](/ACM/issues/ACM-19)

---

## 1. Paperclip

### 1.1 What Paperclip surfaces

Paperclip is an agent orchestration platform. Its public API surface is a typed REST API around these entity types:

| Entity | Key typed fields |
|--------|-----------------|
| **Issue** | `identifier`, `title`, `description`, `status` (enum), `priority` (enum), `parentId`, `goalId`, `projectId`, `assigneeAgentId`, `assigneeUserId`, `blockedBy[]`, `blocks[]`, `executionState`, `billingCode` |
| **Comment** | `id`, `issueId`, `body` (markdown), `authorAgentId`, `authorUserId`, `createdAt` |
| **Document** | `key` (string), `title`, `format`, `body` (markdown), `revisionId`, `baseRevisionId` — one key-value store per issue |
| **Interaction** | `kind` (suggest_tasks \| ask_user_questions \| request_confirmation), `continuationPolicy`, `idempotencyKey`, `supersedeOnUserComment` |
| **Agent** | `id`, `urlKey`, `companyId`, `chainOfCommand[]`, `budget`, `skills[]`, `instructions-path` |
| **Run** | `id`, linked to checkout + issue, `agentId`, timestamps |
| **Routine** | schedule trigger (cron), `concurrencyPolicy`, `catchUpPolicy` → creates execution issues |
| **Approval** | `type`, `requestedByAgentId`, `issueIds[]`, structured `payload` |
| **Goal / Project** | hierarchical; linked to issues for context and billing |

### 1.2 What's well-typed

- Issue lifecycle: status and priority are enums, transitions are events, checkout links runs to issues
- Graph structure: parent/child hierarchy + first-class blocker graph (`blockedByIssueIds` is an array on the wire, not free text)
- Agent identity and chain-of-command: structured, not implicit
- Execution state machines: staged approval flows, `in_review` handoffs, `request_confirmation` interactions with continuation policies
- Interaction kinds: the three interaction primitives (suggest_tasks, ask_user_questions, request_confirmation) are typed with continuation semantics

### 1.3 What's not typed

- **Content is free-form markdown.** Comment bodies, document bodies, and issue descriptions carry zero structure beyond the fields above. A decision recorded as a comment is indistinguishable from a status update.
- **No semantic fact atoms.** There is no `(entity, relation, value)` primitive. Knowledge lives in markdown blobs.
- **No confidence or decay.** A comment written in 2024 has the same weight as one written yesterday. There is no expiry, confidence score, or freshness signal on any record.
- **No provenance chain on knowledge.** You can see `authorAgentId`, but there is no mechanism to assert "this fact was derived from fact X."
- **Memory is per-agent, not entity-scoped.** Each agent has its own PARA directory. There is no shared fact graph queryable by multiple agents.

### 1.4 Where Paperclip naturally writes Loom-style facts

These events already carry the core fields a Loom fact needs (entity, relation, value, source, timestamp):

| Event | Fact shape |
|-------|-----------|
| Issue status transition | `(issue:ACM-21, status, done, agent:CEO, T)` |
| Checkout | `(issue:ACM-21, claimed_by, agent:CEO, agent:CEO, T)` |
| Blocker resolution | `(issue:ACM-21, unblocked_by, issue:ACM-20, system, T)` |
| Document revision | `(issue:ACM-21, plan_revised_to, revisionId:X, agent:CEO, T)` |
| Assignment | `(issue:ACM-21, assigned_to, agent:CTO, agent:CEO, T)` |

A thin Paperclip adapter can emit these as Loom fact atoms with no Paperclip changes — the data is already there.

### 1.5 Where Paperclip doesn't write Loom-style facts

- Content decisions (markdown in comments and documents)
- Cross-issue semantic relationships beyond parent/blocker
- Agent preference or learning signals
- User trust or feedback patterns
- Company-level strategy (lives in memory files, not issues)

The Loom Paperclip adapter must do NLP/extraction on markdown content to produce richer facts; structural events are the easy path, not the valuable path.

---

## 2. OpenClaw

### 2.1 What the public agent contract looks like

OpenClaw is Claude Code — Anthropic's CLI/agent runtime. Agents are Claude model instances with a system prompt injected at runtime. The public contract is:

**Identity and model:**
- Agent = a Claude model (Opus/Sonnet/Haiku) + injected instructions
- No persistent state between runs beyond the file system and external APIs
- Agent identity is per-instructions-file, not per-instance

**Tool surface:**
- `Read`, `Write`, `Edit` — file I/O
- `Bash` — shell command execution
- `Grep`, `Glob` — search primitives
- `Agent` — spawn typed sub-agents (Explore, general-purpose, Plan, etc.)
- `Skill` — invoke named skill files
- `WebFetch`, `WebSearch` — external content
- `TodoWrite` — in-session task tracking (ephemeral)
- MCP tools (namespaced as `mcp__<server>__<tool>`) — loaded from MCP server configuration

**Sub-agent spawning:**
- The `Agent` tool accepts a typed `subagent_type` that loads a specialized sub-agent
- Available types are listed at runtime via system-reminder
- Agents can spawn agents recursively; depth is unbounded in principle
- No direct agent-to-agent communication channel — all coordination goes through file system or Paperclip issues

**Skills system:**
- `.claude/skills/<skill-name>/` directories with a `SKILL.md` entry point
- Skills are structured knowledge + capability bundles injectable on demand
- Shared across agents in the same environment; versioned as files
- This is the closest current analog to a Loom knowledge fragment

### 2.2 How agents express memory today

OpenClaw agents use a three-layer file-based memory system (PARA):

| Layer | Format | Scope | Limitations |
|-------|--------|-------|-------------|
| Knowledge graph | Atomic YAML facts in markdown files with frontmatter (`type: user/feedback/project/reference`) | Per-agent directory | Not queryable across agents; no runtime federation |
| Daily notes | `YYYY-MM-DD.md` timeline entries | Per-agent | Not shared; no decay or expiry |
| Tacit knowledge | Patterns the agent has learned about the user | Per-agent | Markdown only; no confidence scores |

Memory index lives at `memory/MEMORY.md` — a flat list with one-line hooks per file. Recall is by the agent reading the index and loading relevant files. There is no vector search, no graph traversal, no semantic query.

**Critical gap:** memory is owned by agents, not by the entities the facts are *about*. The CEO's memory file for "project X" and the CTO's memory file for the same project are separate files with no reconciliation mechanism.

### 2.3 Where Loom would slot in

| Today | With Loom |
|-------|-----------|
| Agent reads `memory/MEMORY.md`, loads `.md` files | Agent calls `loom_recall(query, scope)` MCP tool |
| Agent writes `memory/project_foo.md` | Agent calls `loom_assert(fact)` MCP tool |
| Stale facts persist silently | Facts have `expiresAt` and `confidence`; fabric surfaces contradictions |
| CEO memory ≠ CTO memory on same project | Both write to same entity; reconciliation is Loom's job |
| Skills files = static shared knowledge | Loom fragments = live, versioned, queryable shared knowledge |

The PARA flat-file system is not wrong — it's a good fit for a single-agent world. Loom's value unlocks when there are multiple agents who need to reason over shared ground truth.

---

## 3. MCP (Model Context Protocol)

### 3.1 How agent ↔ tool interop is shaped

MCP is Anthropic's open protocol for connecting AI agents to external tools and data. The architecture:

- **Client** (the agent runtime) discovers and calls tools
- **Server** (a separate process) exposes tools, resources, and prompts
- Communication over stdio or SSE

**Tool shape on the wire:**

```json
{
  "name": "tool_name",
  "description": "Human-readable purpose — agents use this for selection",
  "inputSchema": { /* JSON Schema for parameters */ }
}
```

**Namespacing in Claude Code:** `mcp__<server-name>__<tool-name>`. Multiple servers can be loaded simultaneously; namespace prevents collision.

**Three surface types:**
| Surface | Purpose |
|---------|---------|
| Tools | Typed function calls; agent provides args, server returns structured content |
| Resources | Browsable data (files, DB rows, live state); agent fetches by URI |
| Prompts | Reusable prompt templates with slot parameters |

MCP 2.0+ also supports **server-initiated sampling** — a tool server can request the client model to complete text. This enables richer tools that internally reason using the agent's model.

### 3.2 What MCP doesn't provide

- **No state persistence between calls.** Every tool call is stateless; the server must maintain state externally if needed.
- **No semantic memory.** Tools return data; they don't accumulate knowledge about the conversation or the agent.
- **No fact provenance.** A tool result carries no chain of custody — no "this value came from source X at time T with confidence Y."
- **No decay or staleness signals.** A resource browsed yesterday looks identical to one browsed today.
- **No federation.** MCP servers are local or point-to-point; there is no protocol for federated knowledge across multiple MCP nodes.

### 3.3 Where Loom complements vs overlaps MCP

**Complements:**
- Loom's retrieval and assertion interface is a natural MCP tool surface. A `loom` MCP server giving agents `loom_recall`, `loom_assert`, `loom_retract` requires zero framework coupling — any agent that speaks MCP gets Loom memory.
- MCP Resources map cleanly onto browsing Loom fact nodes by entity URI.
- MCP Prompts can be used to inject relevant Loom context into agent system prompts on demand.
- MCP server-initiated sampling enables a Loom server to do semantic similarity search using the agent's own model (no separate embedding service needed for Phase 0).

**Overlaps (non-competing):**
- Both are transport-layer concerns. MCP is the wire; Loom is the fabric. They operate at different layers and don't substitute for each other.
- If Loom ships as an MCP server, MCP becomes Loom's most important distribution channel — not a competitor.

---

## 4. Synthesis: Spec Implications for Loom v0.1

### 4.1 Paperclip issues are the cheapest first facts source

Every Paperclip issue event (status transition, checkout, blocker resolution, document revision) already carries `(entity, relation, value, source, timestamp)`. A thin Paperclip adapter can stream these as Loom fact atoms with no changes to Paperclip. Ship this in Phase 4 as the reference adapter — it will cover the "CEO running on Loom by end of Phase 4" milestone from the board's framing.

**Spec implication:** define a `StructuralEventFact` primitive that maps directly to Paperclip's event stream. Make it the simplest possible Loom fact type — no NLP, no inference. Save semantic extraction from markdown for Phase 5.

### 4.2 Loom's type lattice must go beyond Paperclip's schema

Paperclip already types status, priority, hierarchy, and blockers well. Loom's value is in the content layer Paperclip doesn't reach: semantic facts extracted from markdown comments and documents. The spec should not mirror Paperclip's structural schema — it should extend it into the semantic layer: typed claims, preferences, constraints, decisions, and their provenance chains.

**Spec implication:** distinguish clearly between `StructuralFacts` (directly extractable from Paperclip's API — cheap) and `SemanticFacts` (extracted via NLP or agent reasoning — expensive). Both are first-class Loom types; they have different ingestion costs and confidence profiles.

### 4.3 OpenClaw's PARA memory is the migration target — and the v0.1 dogfood

The Phase 0 milestone says "shadow-migrate CEO `MEMORY.md`." This is the right test bed. The four PARA memory types (`user`, `feedback`, `project`, `reference`) must each have a canonical mapping to Loom fact atoms in the spec. If the spec can't express a `feedback` memory file as typed facts, it's not ready.

**Spec implication:** write explicit mapping tables in the v0.1 spec for each PARA memory type → Loom fact type. Treat these tables as acceptance criteria for Phase 0 — if the prototype can round-trip a PARA memory file through Loom and back without losing semantics, Phase 0 exits green.

### 4.4 MCP is the correct wire protocol — ship the MCP server before custom adapters

Building Loom as an MCP server gives universal distribution: any Claude Code agent, any Paperclip agent, any future framework that speaks MCP gets Loom memory with no custom integration. The minimum viable surface is three tools: `loom_assert(fact)`, `loom_recall(query, scope)`, `loom_retract(factId, reason)`.

**Spec implication:** the Phase 2 reference node must include a functioning MCP server as the primary client interface, not a custom SDK. Custom adapters (OpenClaw native, Paperclip native) come later and are built on top of this MCP foundation.

### 4.5 Intent layer is separate from the fact layer — spec them separately

Paperclip's interactions (suggest_tasks, ask_user_questions, request_confirmation) are stateful, mutable, directed handoffs between agents and humans. Loom's typed intent primitives (`goal`, `constraint`, `preference`, `deference`, `handoff`) carry different semantics: they can be satisfied, superseded, escalated, and inherited across agent boundaries. Do not model intents as facts with a special `type` field — they need their own schema and lifecycle.

**Spec implication:** the v0.1 spec needs two top-level sections: *Knowledge Fabric* (facts, provenance, decay) and *Intent Protocol* (goals, constraints, preferences, handoffs, confidence). Define the boundary between them explicitly. A fact is immutable and append-only. An intent is stateful and has a resolution lifecycle.

### 4.6 Entity-scoped over agent-scoped — the single most important architectural divergence

Paperclip memory is agent-scoped (each agent's PARA directory). OpenClaw memory is agent-scoped (per-agent `memory/` folder). Every agent today owns its facts about the world. Loom must be entity-scoped: facts about `project:loom` belong to the project entity, not to whichever agent wrote them first. Any authorized agent should query and contribute to the same entity's fact set.

**Spec implication:** entity URIs must be first-class in the v0.1 spec. Every fact asserted must carry an `entityId` that is stable across agents and time. The spec should define a minimal entity URI scheme (e.g., `loom://entity/<type>/<id>`) before any storage or API design decisions are made.

### 4.7 Confidence and decay are required fields from day one — no retrofitting

Both Paperclip and OpenClaw demonstrate the cost of deferred freshness signals: stale comments carry the same weight as fresh ones; PARA files that haven't been updated in months look identical to ones updated today. Adding confidence and decay as a later extension means every Phase 0–3 implementation will have to be revisited.

**Spec implication:** `confidence: float [0,1]` and `expiresAt: ISO8601 | null` are required fields on every Loom fact atom in v0.1, even if the Phase 0 prototype hardcodes `confidence: 1.0` and `expiresAt: null` everywhere. The schema cost is zero. The retrofit cost is not.

### 4.8 Skills files are the UX reference for Loom knowledge fragments

OpenClaw's `.claude/skills/` CLAUDE.md files are already structured, versioned, shared, and injectable — they're the closest existing analog to a Loom knowledge fragment. Developers who've written or used skills will immediately recognize the mental model. Use skills files as the reference example in the spec and developer docs: "a Loom fragment is like a skill file, but live, federated, and queryable."

**Spec implication:** when writing v0.1 developer-facing docs, show the migration path from a `skills/` CLAUDE.md file to a Loom knowledge fragment. This lowers the adoption barrier for the existing Claude Code developer base, which is the most likely early-adopter cohort.

---

## 5. Quick Reference: Capability Matrix

| Capability | Paperclip | OpenClaw PARA | MCP | Loom (target) |
|-----------|-----------|---------------|-----|---------------|
| Typed schema | Yes (structural) | No (markdown) | Yes (JSON Schema tools) | Yes (facts + intents) |
| Persistent memory | Issues / docs | PARA flat files | No | Yes (federated fabric) |
| Cross-agent sharing | No (agent-scoped) | No (agent-scoped) | No (stateless) | Yes (entity-scoped) |
| Confidence signals | No | No | No | Yes (required field) |
| Decay / expiry | No | No | No | Yes (required field) |
| Provenance chain | Partial (authorId) | No | No | Yes (full chain) |
| Federation | No | No | No | Yes (SMTP-style) |
| Semantic query | No | No | No | Yes (recall API) |
| Intent lifecycle | Yes (interactions) | No | No | Yes (intent layer) |

---

*Authored: 2026-05-01 · Source: first-hand observation of Paperclip skill API, OpenClaw (Claude Code) agent runtime, and MCP protocol specification.*
*Referenced by: [ACM-19](/ACM/issues/ACM-19) go/no-go memo.*
