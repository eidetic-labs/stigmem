# Stigmem — OpenClaw Adapter

Integrates Stigmem with OpenClaw agents. Provides the standard boot handshake
(pull user prefs + project constraints into context) and write surfaces for
handoffs, decisions, and escalations.

> **Status:** v1.0.1 — published to ClawHub as
> [`stigmem-node`](https://clawhub.ai/skills/stigmem-node). Includes
> security fixes (identity binding, value sanitization) and a bundled
> `adapter.py` for self-contained skill installs.

## ClawHub skill

The recommended way to use this adapter in an OpenClaw deployment is via the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node). The skill
bundles `adapter.py` so no separate package install is required beyond `stigmem-py`,
and documents the environment variables in a format OpenClaw reads automatically.

```bash
# Install via OpenClaw's ClawHub integration
skill install stigmem-node
```

Then set the required env vars (ClawHub will prompt for them on first use):

```bash
STIGMEM_URL=https://stigmem.example.com   # required
STIGMEM_API_KEY=sk-your-key               # required if auth is enabled
STIGMEM_SOURCE_ENTITY=agent:openclaw      # optional; default: agent:openclaw
```

## Security model

**Identity binding** — Each write surface (`emit_decision`, `emit_handoff`,
`emit_escalation`) pins the `source` field to the entity declared in
`STIGMEM_SOURCE_ENTITY`. Facts are attributed to this URI in the fact graph; ensure
it uniquely identifies the agent deployment, not a shared or generic identifier.

**Untrusted retrieved context** — `boot()` returns facts from an external Stigmem
node. The adapter sanitizes fact values before formatting them into the system-prompt
summary, but the summary should be treated as untrusted input in high-stakes
workflows — an attacker who controls the node can craft fact values to influence
agent behaviour. Use a private, access-controlled node for sensitive workloads.

**API key scope** — Set `STIGMEM_API_KEY` to a least-privilege key scoped only to
the nodes this agent reads from and writes to. Do not share a key across unrelated
agent deployments. Rotate keys regularly; revoke via the Stigmem node admin API if
compromised.

## Changelog

### v1.0.1

- Security: `source_entity` is now bound at construction time and cannot be
  overridden per-call, preventing source spoofing.
- Security: fact values in `boot()` summary output are sanitized (control
  characters and embedded newlines stripped) before injection into the system prompt.
- ClawHub: `adapter.py` bundled in the skill directory so ClawHub installs are
  self-contained.

### v1.0.0

Initial release — boot handshake, handoff, decision, and escalation surfaces;
pagination; full respx-mocked test suite.

## Design

OpenClaw agents are persistent and channel-agnostic. The Stigmem adapter hooks into:

1. **Agent boot** — pull user preferences (`preference:*`), active project
   constraints (`roadmap:constraint`), pending handoff facts, and recent
   escalations. All queries are paginated; node unavailability produces an empty
   context with a logged warning instead of crashing the agent.
2. **Handoff** — when a user ends a session or delegates to another channel/agent,
   emit a typed `intent:handoff` fact cluster with validated fact refs, an optional
   continuation note, and a human-readable summary.
3. **Decision** — when the agent makes a meaningful choice, emit a
   `roadmap:decision` fact. A dedup guard skips the write when an equivalent fact
   already exists for the same (entity, source) pair.
4. **Escalation** — emit a priority-typed `intent:escalation` fact cluster with a
   24-hour expiry so stale escalations don't linger.

### OpenClaw surface inventory

Built against OpenClaw's public API surfaces only — no holdco outreach per Phase 0
constraint. The adapter wraps Stigmem's HTTP API via `stigmem-py`; OpenClaw-hosted
agents import it as a standard Python library.

## Files

| File | Purpose |
|---|---|
| `adapter.py` | Python adapter class — boot handshake + write surfaces |
| `tests/conftest.py` | pytest path setup (no package install required) |
| `tests/test_adapter.py` | Unit tests (respx-mocked) + conformance vector smoke tests |
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

## Worked example — full agent boot + session lifecycle

```python
import os
from stigmem.adapters.openclaw.adapter import OpenClawStigmemAdapter

# 1. Construct from environment
adapter = OpenClawStigmemAdapter.from_env()

# 2. Boot at session start — pull all relevant facts and format a system prompt snippet
ctx = adapter.boot(
    user_entity="user:alice",
    session_id="session:2026-05-02-abc",
    project_entities=["project:acme-roadmap"],
)

if ctx:
    system_prompt = base_system_prompt + "\n\n" + ctx.summary
else:
    system_prompt = base_system_prompt  # node was unavailable; continue without stigmem

# ctx.summary looks like:
#
# ## Stigmem context — user:alice
#
# ### preference
# - **preference:theme** on `user:alice`: dark
# - **preference:lang** on `user:alice`: en
#
# ### roadmap
# - **roadmap:constraint** on `project:acme-roadmap`: Must ship Phase 1 before 2026-06-01
#
# ### intent
# - **intent:context_ref** on `handoff:5f3a`: fact-004

# 3. Agent runs its main loop …
# (LLM calls, tool use, etc.)

# 4a. Emit a significant architectural decision
adapter.emit_decision(
    entity="decision:auth-provider",
    summary="Chose Clerk over Auth0: simpler Next.js integration, lower per-seat cost at SMB scale.",
    source="agent:openclaw",
)

# 4b. Escalate to the CTO when the agent hits a scope boundary
adapter.emit_escalation(
    to_entity="agent:cto",
    goal="Approve increased Stripe webhook rate limit for Phase 2 load.",
    priority="high",
)

# 5. Emit a handoff when the session ends or delegates
adapter.emit_handoff(
    from_entity="agent:openclaw",
    to_entity="agent:assistant",
    summary="User asked about Q2 roadmap; auth provider chosen; Stripe limit escalation pending.",
    fact_refs=["fact-auth-decision", "fact-esc-stripe"],   # invalid refs are silently skipped
    continuation="Resume from the Stripe rate-limit discussion.",
)
```

## Running the tests

```bash
# from the repo root
uv run pytest stigmem/adapters/openclaw/tests/ -v
```

No live Stigmem node required — all tests are respx-mocked. Conformance vectors
from `sdks/stigmem-py/tests/conformance_vectors.py` are included as smoke tests.

## Relation namespaces

| Relation | Scope | Written by | Notes |
|---|---|---|---|
| `preference:*` | company | Any agent or user | Pulled on boot; filtered to `preference:` prefix |
| `roadmap:constraint` | company | CTO / planning agents | Pulled per project entity |
| `roadmap:decision` | company | Agent | Dedup guard: skips if fact already exists |
| `intent:handoff_to` | company | Agent on session end | Ref to receiving agent |
| `intent:handoff_summary` | company | Agent on session end | Text summary |
| `intent:context_ref` | company | Agent on session end | Fact refs for receiver |
| `intent:continuation` | company | Agent on session end | Optional continuation note |
| `intent:escalation` | company | Agent on escalation | Priority string; 24h expiry |
| `intent:escalate_to` | company | Agent on escalation | Ref to receiving agent |
| `intent:goal` | company | Agent on escalation | Text goal |
