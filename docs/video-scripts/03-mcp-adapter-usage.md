# Script 3 — MCP Adapter Usage

**Target duration:** ~9 min 50 s  
**Audience:** Developer wiring the stigmem MCP adapter into Claude Code or another MCP host  
**Format:** Screen-recording, terminal + editor + Claude Code, narrated  

---

## YouTube / channel description block

```
stigmem — MCP Adapter Usage (v1.0)

Wire the stigmem MCP adapter into Claude Code and use all five tools:
assert_fact, query_facts, subscribe_scope, resolve_contradiction, lint_scope.

Timestamps:
0:00 — What the MCP adapter does
1:00 — Prerequisites and architecture
2:00 — Build the adapter
3:00 — Configure in Claude Code
4:15 — Demo: assert_fact and query_facts
5:45 — Demo: subscribe_scope
6:45 — Demo: lint_scope
7:30 — Demo: resolve_contradiction
8:45 — STIGMEM_POLL_LIMIT and tuning
9:20 — What's next

GitHub: https://github.com/Eidetic-Labs/stigmem
Docs: https://stigmem.dev/docs/guides/connectors
```

---

## Production notes

- Resolution: 1920×1080
- Show terminal and editor side-by-side during the configure step (section [3:00])
- Mask `STIGMEM_API_KEY` values with `sk-xxxx` before recording
- Claude Code interaction segments: zoom to 130 % so tool calls are readable
- Keep Claude Code prompts short and literal — do not ad-lib; the demo prompts below are designed to show specific tool behaviors

---

## Script

### [0:00] What the MCP adapter does

**[Screen: architecture diagram]**

```
Claude Code / MCP host
      │  MCP (stdio)
      ▼
stigmem-mcp  (adapters/mcp)
      │  HTTP
      ▼
Stigmem node  (localhost:8765)
      │
      ▼
 SQLite store
```

> "The stigmem MCP server is a thin translation layer. It accepts MCP tool calls over stdio, translates them to HTTP requests against your running stigmem node, and returns the results. The server itself is stateless — all persistence lives in the node's SQLite store."

> "This means any MCP-aware agent — Claude Code, Codex, a custom host — can read and write structured facts without installing any SDK or knowing the HTTP API."

---

### [1:00] Prerequisites and architecture

**[Screen: terminal — show node running]**

> "You'll need Node.js 18 or later, and a running stigmem node. If you don't have one running, the self-hosted setup video covers that in under 10 minutes."

```bash
curl -s http://localhost:8765/healthz | jq .
```

> "Good — node is up."

> "The MCP adapter exposes five tools."

**[Screen: show tools table from README or docs]**

> "`assert_fact` — write a typed fact. `query_facts` — query by entity, relation, or scope. `subscribe_scope` — cursor-based poll for recent facts in a scope. `resolve_contradiction` — resolve a conflict between two competing facts. And `lint_scope` — a read-only health check that detects contradictions, stale facts, orphaned references, and broken links in a scope."

---

### [2:00] Build the adapter

**[Screen: terminal]**

> "The adapter is a TypeScript package. Build it with pnpm."

```bash
cd adapters/mcp
pnpm install
pnpm build
```

> "That produces `dist/server.js`. The build takes about 10 seconds on first run — subsequent builds are faster."

```bash
ls dist/server.js
```

> "That's the entry point you'll point your MCP host at."

---

### [3:00] Configure in Claude Code

**[Screen: editor — open or create .claude/mcp_servers.json]**

> "Add the adapter to Claude Code's MCP server config."

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

> "The path in `args` must be absolute. `STIGMEM_URL` points to your running node, and `STIGMEM_API_KEY` is the node's API key — `dev-key` works for the default Docker Compose setup."

> "Reload Claude Code to pick up the config. You'll see `stigmem` appear in the MCP servers panel."

**[Screen: Claude Code MCP panel showing stigmem connected]**

> "Green status — the adapter is connected and all five tools are available."

---

### [4:15] Demo: assert_fact and query_facts

**[Screen: Claude Code — new conversation]**

> "Let's try it. I'll ask Claude to record a fact."

**[Type the following prompt in Claude Code]**

```
Use assert_fact to record:
  entity: decision:use-postgres
  relation: roadmap:status
  value: {"type": "string", "v": "approved"}
  source: agent:cto
  scope: company
```

> "Notice the typed value — `{\"type\": \"string\", \"v\": \"approved\"}`. The MCP tool requires this format. If you give Claude a natural-language request like 'record that we approved postgres', it will format the value object correctly for you. But in tool calls, use the typed format directly to avoid a validation error."

**[Show Claude's response with the tool call and fact ID]**

> "The fact is written. Now query it back."

```
Query facts for entity decision:use-postgres, relation roadmap:status
```

**[Show Claude's query_facts response]**

> "The fact comes back with its `id`, `hlc` timestamp, and `source_node` — that last field will be non-null for facts that arrived via federation."

---

### [5:45] Demo: subscribe_scope

**[Screen: Claude Code]**

> "`subscribe_scope` is a single-shot cursor-based poll. It returns recent facts in a scope and a cursor you can pass on the next call to get only new facts since the last check."

```
Use subscribe_scope to get the 5 most recent facts in scope company
```

**[Show response with facts and cursor]**

> "The response includes a `cursor` value. Pass it back on the next call to get only facts written after this point — it's how you build an efficient polling loop."

```
subscribe_scope again with that cursor
```

> "Empty — no new facts since the last call. This is the pattern: poll on a schedule, process the delta, advance the cursor. `STIGMEM_POLL_LIMIT` controls the max facts per call — more on that in a moment."

---

### [6:45] Demo: lint_scope

**[Screen: Claude Code]**

> "`lint_scope` is a read-only health sweep. It scans a scope for contradictions — same entity–relation–scope with different values — stale facts that haven't been updated in a long time, orphaned references, and broken links. It writes nothing; it only reports."

```
Run lint_scope on scope company
```

**[Show linter output — ideally clean, or with a synthetic contradiction]**

> "Clean — no contradictions, no stale facts, no broken references. If the linter finds issues, each finding includes the entity, relation, and affected fact IDs so you can investigate or resolve."

---

### [7:30] Demo: resolve_contradiction

**[Screen: Claude Code]**

> "If the linter or ingest detection surfaces a conflict, you resolve it with `resolve_contradiction`. Let me first list any open conflicts via curl so we have a real conflict ID to work with."

**[Screen: split — terminal + Claude Code]**

```bash
curl -s http://localhost:8765/v1/conflicts \
  -H 'X-API-Key: dev-key' | jq '.[0] | {conflict_id, entity, relation}'
```

> "There's the conflict endpoint — `GET /v1/conflicts`. If there are open conflicts, you'll see them here. Let's resolve one through the MCP tool."

**[Screen: Claude Code — if a conflict exists from earlier demo, use it; otherwise note it]**

```
Use resolve_contradiction to resolve conflict <conflict_id>
Choose the fact from source agent:cto as the winner
Resolution note: CTO decision confirmed
```

**[Show tool call and response]**

> "`resolve_contradiction` calls `POST /v1/conflicts/{conflict_id}/resolve` under the hood, passing the `winning_fact_id` and your resolution note. The conflict is marked settled and a resolution fact is written with a `stigmem:resolves` relation."

---

### [8:45] STIGMEM_POLL_LIMIT and tuning

**[Screen: terminal — show env var docs or README]**

> "Two env vars worth knowing for production use."

> "`STIGMEM_POLL_LIMIT` controls the maximum facts returned per `subscribe_scope` call. Default is 50. If your node has high write rate, increase this to reduce the number of calls needed to drain the queue. Set it in the `env` block of your MCP server config."

```json
"env": {
  "STIGMEM_URL": "http://localhost:8765",
  "STIGMEM_API_KEY": "sk-your-key",
  "STIGMEM_POLL_LIMIT": "200"
}
```

> "`STIGMEM_FEDERATION_PULL_INTERVAL_S` on the node side controls how often peers are polled for new facts — default 30 seconds. Lower it in dev for faster iteration, leave it at 30 in production."

---

### [9:20] What's next

**[Screen: docs site]**

> "That covers the full MCP adapter workflow: build, configure, and all five tools — `assert_fact`, `query_facts`, `subscribe_scope`, `lint_scope`, and `resolve_contradiction`."

> "The MCP adapter works with any MCP-capable host. The connector guides in the docs cover Cursor, Zed, Continue, and the Paperclip agent platform."

> "For federation between nodes, watch the federation walkthrough. For setting up the node itself, watch the self-hosted node setup video."

> "Full documentation at stigmem.dev. Thanks for watching."

---

*End of Script 3*
