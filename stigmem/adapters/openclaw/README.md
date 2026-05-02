# Stigmem — OpenClaw Adapter

Integrates Stigmem with OpenClaw agents. Provides the standard boot handshake
(pull user prefs + project constraints into context) and write surfaces for
handoffs, decisions, and escalations.

> **Status:** Scaffold complete (Phase 4 heartbeat 1). Full implementation
> tracked in child issue assigned to SeniorEngineer.

## Design

OpenClaw agents are persistent and channel-agnostic. The Stigmem adapter hooks into:

1. **Agent boot** — pull user preferences, active project constraints, and any pending
   handoff facts for the starting session.
2. **Handoff** — when a user ends a session or delegates to another channel/agent,
   emit a `intent:handoff` fact with a `HandoffPayload` (fact refs, continuation, summary).
3. **Decision** — when the agent makes a meaningful decision (tool choice, escalation,
   scope change), emit a `roadmap:decision` or `intent:escalation` fact.

### What OpenClaw public surfaces are used

Built against OpenClaw's public API surfaces only — no holdco outreach per Phase 0 constraint.
Current surface inventory (from `specs/loom/readback-surfaces.md`):

- OpenClaw uses an internal Gateway protocol (versioned, additive-first).
- No published inter-agent wire spec found publicly as of 2026-05-01.
- The adapter therefore wraps Stigmem's HTTP API and provides a Python helper
  library that OpenClaw-hosted agents can import.

If OpenClaw's public surface exposes a plugin/extension API, the adapter should
be re-implemented against that. Escalate to CEO if a protocol gap requires
holdco outreach.

## Files

| File | Purpose |
|---|---|
| `adapter.py` | Python adapter class — boot handshake + write surfaces |
| `boot_handshake.py` | Standalone boot handshake script (imported by OpenClaw agent entrypoints) |
| `README.md` | This file |

## Setup

### Requirements

- Python ≥ 3.11
- `stigmem-py` installed: `pip install stigmem-py`
- A running Stigmem node

### Environment variables

```bash
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=sk-your-key
STIGMEM_SOURCE_ENTITY=agent:openclaw   # entity URI for this OpenClaw instance
```

### Boot handshake

At agent startup, call:

```python
from stigmem.adapters.openclaw import OpenClawStigmemAdapter

adapter = OpenClawStigmemAdapter.from_env()
context = adapter.boot(user_entity="user:alice", session_id="session:xyz")

# context.facts contains all pulled facts
# context.summary is a markdown string ready to inject into system prompt
```

The boot handshake pulls:
1. User preferences (`preference:*` facts for the user entity)
2. Active project constraints (`roadmap:constraint` facts for active projects)
3. Pending handoff facts targeting this agent
4. Recent escalations (`intent:escalation` facts within the last 24h)

### Write surfaces

```python
# Emit a handoff fact when session ends
adapter.emit_handoff(
    from_entity="agent:openclaw",
    to_entity="agent:assistant",
    summary="User asked about Q2 roadmap; pending decision on DB choice.",
    fact_refs=["fact-001", "fact-002"],
    continuation="Continue from where we left off on the roadmap discussion.",
)

# Emit a decision fact
adapter.emit_decision(
    entity="decision:db-choice",
    summary="Chose PostgreSQL over SQLite for the hosted tier.",
    source="agent:openclaw",
)

# Emit an escalation fact
adapter.emit_escalation(
    to_entity="agent:cto",
    goal="Approve infrastructure cost increase for Phase 3.",
    priority="high",
)
```

## Integration recipe

1. Install `stigmem-py` in your OpenClaw agent environment.
2. Set the three env vars above.
3. Call `adapter.boot()` at the top of your agent's system prompt construction.
4. Append `context.summary` to the system prompt.
5. At session end or on significant events, call the write surface methods.

The adapter is intentionally thin — it does not modify OpenClaw's internal state
or hook into its internal API. It reads and writes facts via Stigmem's HTTP API only.

## Relation namespaces used

| Relation | Scope | Written by |
|---|---|---|
| `preference:*` | company | Any agent or user |
| `roadmap:constraint` | company | CTO / planning agents |
| `intent:handoff` | company | Agent on session end |
| `intent:escalation` | company | Agent on escalation |
| `roadmap:decision` | company | Agent on architectural decision |

## Implementation status

The adapter class (`adapter.py`) is scaffolded with the interface contract.
Full implementation — boot handshake pagination, fact-to-prompt formatting,
write surface tests — is in progress (child issue ACM-40.x, assigned SeniorEngineer).
