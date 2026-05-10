---
title: OpenClaw
sidebar_label: OpenClaw
audience: Integrator
---

# Stigmem in OpenClaw

Add persistent, federated memory to your OpenClaw agents via the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node). The skill
provides four surfaces: a **boot handshake** that injects prior context into the
system prompt, and write surfaces for **handoffs**, **decisions**, and
**escalations**.

**Audience:** OpenClaw skill developers and node operators deploying Stigmem as a
shared knowledge store across agents.

## Installation

### ClawHub (recommended)

```bash
skill install stigmem-node
```

OpenClaw reads the skill's env-var manifest and prompts for `STIGMEM_URL` on first
use. `adapter.py` is bundled in the skill directory — no separate package install
is needed beyond `stigmem-py` (declared in the install spec).

### pip

For direct package installs outside ClawHub:

```bash
uv add "stigmem-py>=1.0.0,<2.0.0"
# or
pip install "stigmem-py>=1.0.0,<2.0.0"
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STIGMEM_URL` | Yes | Base URL of your Stigmem node (e.g. `https://stigmem.example.com`). |
| `STIGMEM_API_KEY` | No | API key for the node. Omit if the node runs without auth (default for local dev). |
| `STIGMEM_SOURCE_ENTITY` | No | Entity URI identifying this agent in the fact graph. Default: `agent:openclaw`. |

## Usage

`adapter.py` is bundled with the ClawHub skill. Import it directly from the skill
directory, or use the package import if you installed via pip:

```python
from adapter import OpenClawStigmemAdapter   # ClawHub bundled path
# or: from stigmem_openclaw.adapter import OpenClawStigmemAdapter  # pip install

adapter = OpenClawStigmemAdapter.from_env()
```

### Boot handshake

Call `boot()` at session start to pull prior context and inject it into the system
prompt. Pass the user entity and any project entities the agent should consider:

```python
ctx = adapter.boot(
    user_entity="user:alice",
    project_entities=["project:my-roadmap"],
)
system_prompt = base_prompt + ("\n\n" + ctx.summary if ctx else "")
```

`boot()` returns `None` (not a fatal error) when the node is unreachable, so the
agent degrades gracefully rather than crashing.

### Emit a decision

Record a significant architectural decision as a durable `roadmap:decision` fact.
A built-in dedup guard skips the write if an equivalent fact already exists for
the same `(entity, source)` pair:

```python
adapter.emit_decision(
    entity="decision:auth-provider",
    summary="Chose Clerk over Auth0: simpler Next.js integration, lower per-seat cost.",
)
```

### Emit an escalation

Write an `intent:escalation` fact with a 24-hour expiry so stale escalations don't
accumulate:

```python
adapter.emit_escalation(
    to_entity="agent:cto",
    goal="Approve increased Stripe webhook rate limit for the v0.4 design window load.",
    priority="high",
)
```

`priority` accepts `"low"`, `"medium"`, `"high"`, or `"critical"`.

### Emit a handoff

Record a typed handoff cluster when a session ends or delegates to another agent:

```python
adapter.emit_handoff(
    from_entity="agent:openclaw",
    to_entity="agent:assistant",
    summary="Auth provider chosen; Stripe limit escalation pending.",
    fact_refs=["fact-auth-decision", "fact-esc-stripe"],
    continuation="Resume from the Stripe rate-limit discussion.",
)
```

`fact_refs` are persisted as `ref`-typed fact values so the receiving agent can
fetch them directly.

## Security

**Source binding** — `STIGMEM_SOURCE_ENTITY` is bound at construction time and
cannot be overridden per call, so facts are always attributed to the declared agent
identity. Use a per-deployment entity URI, not a shared or generic identifier.

**Untrusted retrieved context** — `boot()` sanitizes fact values (strips control
characters and embedded newlines) before injecting them into the system prompt, but
treat the summary as untrusted input in high-stakes workflows. Use a private,
access-controlled node for sensitive workloads.

**API key scope** — Set `STIGMEM_API_KEY` to a least-privilege key scoped only to
the nodes this agent reads from and writes to. Do not share a key across unrelated
agent deployments. Rotate keys regularly; revoke via the Stigmem node admin API if
compromised.

**Fact persistence** — Facts written via this adapter persist across sessions and
agents. Retract stale facts explicitly rather than relying on expiry for correction,
and use separate scope namespaces (or separate nodes) for experimental workloads.

## Running your own Stigmem node

Stigmem nodes are self-hosted. The quickest way to spin one up:

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_NODE_URL=http://localhost:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

For a production setup with auth, a persistent volume, and TLS, see the
[installation guide](../../get-started/installation).

## Smoke test

With the node running and env vars set:

```python
from adapter import OpenClawStigmemAdapter

adapter = OpenClawStigmemAdapter.from_env()
ctx = adapter.boot(user_entity="user:test", project_entities=[])
print("boot ok:", ctx.summary[:80] if ctx else "(no prior context)")
```

## See also

- [`adapters/openclaw` README](https://github.com/Eidetic-Labs/stigmem/tree/main/adapters/openclaw#readme) — package source, changelog, full security model
- [Federation guide](../../concepts/federation/) — external node onboarding and multi-node topology
- [Paperclip / Claude Code](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/adapter-paperclip) — MCP-based integration for Paperclip agents
- [Authentication](../../security/authentication) — API key setup and OIDC options
