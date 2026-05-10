# Stigmem — Paperclip Adapter

Bridges Paperclip agent heartbeats with the Stigmem knowledge node. Paperclip agents
read shared context from Stigmem on startup and write lifecycle facts (checkout,
decisions, blockers, completions) back into the fabric.

## Architecture

```
Paperclip agent (heartbeat)
       │
       ├── startup  → query Stigmem for constraints / preferences / handoff context
       ├── checkout → assert paperclip:checkout fact
       ├── decide   → assert roadmap:decision fact
       ├── block    → assert paperclip:issue_status="blocked"
       └── done     → assert paperclip:issue_status="done"
             │
             ▼  HTTP
       Stigmem node  (shared, all agents point to the same node)
```

## Files

| File | Purpose |
|---|---|
| `skill.md` | Paperclip skill — load as a company skill to give agents the usage instructions |
| `emit-fact.js` | CLI helper — assert / retract / query via the Stigmem HTTP API |
| `hook.sh` | Paperclip hook script — emit lifecycle facts on checkout / complete / blocked |

## Setup

### 1. Start the Stigmem node

```bash
cd stigmem/node
uv run uvicorn stigmem_node.main:app --port 8765
```

### 2. Set environment variables

In your agent's adapter config or `.env`:

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key          # omit if auth=none
STIGMEM_SOURCE_ENTITY=agent:cto      # your agent's entity URI
```

### 3. Install the Paperclip skill (optional)

Install `skill.md` as a company skill in Paperclip. This gives all agents the
instructions to use Stigmem without per-agent configuration.

### 4. Wire up hooks (optional, for automated fact emission)

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "bash stigmem/adapters/paperclip/hook.sh post_tool_use"
      }]
    }]
  }
}
```

For checkout / complete / blocked events, call `hook.sh` explicitly in your agent
logic or in a wrapper around the Paperclip checkout API call.

## Relation namespaces used

| Relation | Scope | Written by |
|---|---|---|
| `paperclip:checkout` | company | Agent on task checkout |
| `paperclip:issue_status` | company | Agent on status change |
| `paperclip:blocked_by` | company | Agent on blocked transition |
| `paperclip:last_active` | local | hook.sh PostToolUse |
| `roadmap:decision` | company | Agent on architectural decision |
| `intent:handoff_to` | company | Agent on delegation |
| `intent:context_ref` | company | Agent on delegation |

## Context pull pattern

Recommended startup sequence for a Paperclip agent:

```python
# 1. Pull company-wide context
company_facts = client.query(entity="company:acme", scope="company", min_confidence=0.7)

# 2. Pull project-specific facts
project_facts = client.query(entity=f"project:{project_id}", scope="company")

# 3. Pull handoff facts if this is a delegated task
handoff_facts = client.query(entity=f"handoff:{task_id}", scope="company")

# 4. Assert checkout
client.assert_fact(
    entity=f"issue:{task_id}",
    relation="paperclip:checkout",
    value=string_value("in_progress"),
    source=source_entity,
    scope="company",
)
```

## CEO dogfood configuration

For the pre-reset design work 7-day dogfood window, the CEO agent should set:

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_SOURCE_ENTITY=agent:ceo
```

And at each heartbeat start, query for the full active context:

```bash
node stigmem/adapters/paperclip/emit-fact.js query \
  --entity "company:acme" --scope company --min_confidence 0.7
```

The daily snapshot cron (`stigmem/dogfood/snapshot.sh`) writes the current Stigmem
state to `MEMORY.md` as a read-only backup — not the inverse.
