# Script: MCP Adapter Usage
<!-- Video 3 of 3 | Target length: ≤ 10 min | Audience: AI/agent developers, Claude Code users -->

## Video description (YouTube / project channel copy)

> Wire the stigmem MCP adapter into Claude Code (or any MCP-compatible agent) in under ten minutes. We build the adapter, configure it, and demo all five tools: assert_fact, query_facts, resolve_contradiction, subscribe_scope, and lint_scope.
>
> **Timestamps**
> [0:00] Introduction
> [0:45] Architecture overview (30 seconds)
> [1:30] Prerequisites and build
> [3:00] Configure in Claude Code
> [4:15] assert_fact — write a decision fact
> [5:30] query_facts — retrieve project constraints
> [6:45] subscribe_scope — cursor-based polling
> [7:45] resolve_contradiction — CTO confirms a decision
> [8:45] lint_scope — health-check sweep
> [9:30] Wrap-up and next steps

---

## Production notes

- **Recording environment:** VS Code on the left (`.claude/mcp_servers.json` open), Claude Code chat pane on the right, terminal at the bottom. 1920×1080.
- The stigmem node should be running before the demo starts (use `make up` from video 1).
- **Do not** show real API keys — use `sk-demo-key` or `dev-key` in all configs and responses.
- Each `[PAUSE]` marker = ~2 s silence for edits.

---

## [0:00] Introduction

**[SCREEN: title card — "Stigmem: MCP Adapter Usage"]**

> The Model Context Protocol — MCP — lets AI agents call tools over a standard stdio interface. Stigmem ships an MCP server that wraps its full HTTP API as five typed tools. Any MCP-aware host — Claude Code, Codex, or a custom agent framework — can read and write stigmem facts without touching HTTP.
>
> In this video you'll build the adapter, wire it into Claude Code, and demo every tool.

---

## [0:45] Architecture overview

**[SCREEN: diagram — Claude Code → MCP (stdio) → stigmem-mcp → HTTP → Stigmem node → SQLite]**

> The adapter is stateless. It sits between your agent and a running stigmem node, translating MCP tool calls to HTTP requests. No local state is held in the adapter process — all persistence lives in the node's SQLite database.
>
> You need: Node.js 18 or later, and a running stigmem node. The node can be local or remote — the adapter just needs its URL.

---

## [1:30] Prerequisites and build

**[SCREEN: terminal]**

> First, make sure a stigmem node is running. If you followed video 1 you already have one on port 8765:

```bash
curl -s http://localhost:8765/healthz | jq .
# {"status": "ok"}
```

**[PAUSE]**

> Now build the MCP adapter:

```bash
cd stigmem/adapters/mcp
pnpm install
pnpm build
```

> The build compiles the TypeScript source to `dist/server.js`. The entire adapter is a single Node.js entry point — no daemon, no extra services.

**[SCREEN: terminal — verify build output]**

```bash
ls dist/
# server.js
```

> Note the absolute path to `server.js` — you'll need it in the next step.

```bash
pwd
# /path/to/stigmem/adapters/mcp
# → full path is /path/to/stigmem/adapters/mcp/dist/server.js
```

---

## [3:00] Configure in Claude Code

**[SCREEN: VS Code — `.claude/mcp_servers.json`]**

> Open `.claude/mcp_servers.json` in your project root (create it if it doesn't exist) and add the stigmem entry:

```json
{
  "stigmem": {
    "command": "node",
    "args": ["/absolute/path/to/stigmem/adapters/mcp/dist/server.js"],
    "env": {
      "STIGMEM_URL": "http://localhost:8765",
      "STIGMEM_API_KEY": "dev-key"
    }
  }
}
```

> Use the absolute path from the previous step. The adapter uses two environment variables: `STIGMEM_URL` points to your running node, and `STIGMEM_API_KEY` is forwarded on every HTTP request as `X-API-Key`. An optional `STIGMEM_POLL_LIMIT` caps how many facts `subscribe_scope` returns per call — default is 50.

**[SCREEN: Claude Code — restart or open a new session]**

> Save the file and restart Claude Code (or reload the window). In the next session the `stigmem` server will appear in the MCP tools list. You can verify by typing `/mcp` in Claude Code — you should see five stigmem tools.

**[PAUSE]**

> For other MCP hosts (Codex CLI, Continue.dev, Cursor) the config syntax differs but the adapter command and env vars are identical. Check the connectors guide at `docs.stigmem.dev/docs/guides/connectors` for host-specific snippets.

---

## [4:15] assert_fact — write a decision fact

**[SCREEN: Claude Code chat pane]**

> Let's ask Claude Code to record a technical decision using the adapter:

> **User prompt (show in chat):**
> ```
> Use assert_fact to record that we decided to use SQLite for local storage.
> Entity: decision:use-sqlite, relation: roadmap:status, value: approved,
> source: agent:cto, scope: company.
> ```

**[SCREEN: Claude Code — tool call expanding in UI]**

> Claude Code calls `assert_fact` with the parameters we described. Watch the tool call appear in the sidebar.

**[SCREEN: Claude Code — tool response]**

> The response comes back with the new fact's `id` and `hlc`. Claude acknowledges the write.

**[PAUSE]**

> Notice we used `scope: company` — this fact will replicate to any federation peer. If you were recording a user's personal preference that should stay private, use `scope: local`.
>
> Facts are **immutable** once written. To supersede this decision later, call `assert_fact` again for the same entity and relation. To retract it, assert with `confidence: 0.0`.

---

## [5:30] query_facts — retrieve project constraints

**[SCREEN: Claude Code chat pane]**

> Now query all constraints on the `project:acme-platform` entity:

> **User prompt:**
> ```
> Use query_facts to show me all facts about project:acme-platform
> with relation roadmap:constraint.
> ```

**[SCREEN: Claude Code — tool call + response]**

> The `query_facts` tool accepts `entity`, `relation`, `scope`, and an optional `since` cursor. It returns a `facts` array. Claude summarizes the constraints it found.

**[PAUSE]**

> You can also query directly from the terminal for scripting:

```bash
curl -s 'http://localhost:8765/v1/facts?entity=project:acme-platform&relation=roadmap:constraint' \
  -H 'X-API-Key: dev-key' | jq '.facts[] | {value, confidence, source}'
```

> The HTTP API and the MCP tool return the same data — the adapter is just a thin translation layer.

---

## [6:45] subscribe_scope — cursor-based polling

**[SCREEN: Claude Code chat pane]**

> `subscribe_scope` is a single-shot poll — call it repeatedly with the returned cursor to follow new facts over time. It's designed for agent loops that need to stay in sync with a scope.

> **User prompt:**
> ```
> Use subscribe_scope to get the latest public facts. Then use the
> returned cursor to poll again for anything newer.
> ```

**[SCREEN: Claude Code — two tool calls in sequence]**

> First call returns up to 50 facts and a `cursor` value — an HLC timestamp. The second call passes that cursor back, returning only facts newer than that point. Zero facts in the second call means the scope is caught up.

**[PAUSE]**

> This cursor pattern is how an agent maintains a live view of a stigmem scope across a long session without re-reading everything from the beginning.

---

## [7:45] resolve_contradiction — CTO confirms a decision

**[SCREEN: Claude Code chat pane]**

> If two facts conflict — same entity, relation, and scope but different values — stigmem records a `ConflictRecord`. Let's resolve one.

> First, look up open conflicts:

```bash
curl -s http://localhost:8765/v1/facts/conflicts \
  -H 'X-API-Key: dev-key' | jq '.[0] | {conflict_id, facts}'
```

**[SCREEN: Claude Code — show conflict ID]**

> **User prompt:**
> ```
> Use resolve_contradiction with conflict_id "stigmem:conflict:abc123",
> picking fact-001 as the winner. Note: CTO confirmed during board review.
> ```

**[SCREEN: Claude Code — tool call + response]**

> `resolve_contradiction` posts the winning fact ID and a free-text `resolution_note` for audit. The conflict record is closed and the winning fact becomes the canonical value for that entity/relation/scope.

**[PAUSE]**

> The resolution is itself recorded as a `stigmem:resolves` provenance fact so you have a durable audit trail of who resolved what and why.

---

## [8:45] lint_scope — health-check sweep

**[SCREEN: Claude Code chat pane]**

> The last tool is `lint_scope`. It's a read-only health check that scans for contradictions, stale facts, orphaned references, and broken entity links — equivalent to running spec §14's conformance checks on demand.

> **User prompt:**
> ```
> Run lint_scope on the company scope and tell me if there are any issues.
> ```

**[SCREEN: Claude Code — tool call + response showing lint report]**

> The lint report returns a structured list of issues by category. Zero findings means your scope is clean. Findings include the relevant fact IDs so you can resolve them programmatically with `resolve_contradiction`.

**[PAUSE]**

> Run `lint_scope` in your CI pipeline or as a scheduled agent task to catch drift before it accumulates.

---

## [9:30] Wrap-up and next steps

**[SCREEN: title card with links]**

> You've wired stigmem into Claude Code and used all five MCP tools:
>
> - `assert_fact` — write immutable, scoped facts with provenance
> - `query_facts` — retrieve facts by entity, relation, or scope
> - `subscribe_scope` — cursor-based polling for agent sync loops
> - `resolve_contradiction` — close conflict records with an audit note
> - `lint_scope` — read-only health sweep across a scope
>
> **Next steps:**
> - **Connectors guide** — `docs.stigmem.dev/docs/guides/connectors` — config snippets for Zed, Cursor, Codex CLI, Continue.dev, and others
> - **Full API reference** — `docs.stigmem.dev/docs/api-reference`
> - **Federation** — if you want facts to flow between multiple stigmem nodes, watch video 2

**[SCREEN: GitHub link]**

> Questions or feedback? Open a discussion at `github.com/Eidetic-Labs/stigmem`. Thanks for watching.

---

*End of script — estimated runtime: ~9 min 50 s*
