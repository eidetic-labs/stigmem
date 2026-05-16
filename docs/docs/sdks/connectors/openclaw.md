---
title: OpenClaw
sidebar_label: OpenClaw
audience: Integrator
---

# Stigmem in OpenClaw

Evaluate persistent, federated memory for OpenClaw agents via the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node). The skill
provides four surfaces: a **boot handshake** that injects prior context into the
system prompt, and write surfaces for **handoffs**, **decisions**, and
**escalations**.

**Audience:** OpenClaw skill developers and node operators deploying Stigmem as a
shared knowledge store across agents.

:::caution Alpha connector

The OpenClaw connector is available in the v0.9.0aN alpha line for evaluation, not
as a recommended production integration. This wording is queued for the
v0.9.0a2 artifact refresh; it does not revise the already-published a1 ClawHub
package in place. The adapter still has the ADR-003-dependent C1/H5 audit gap:
retrieved facts are rendered into a prompt summary with presentation-layer
escaping rather than a structural instruction/content channel boundary. Use only
private, access-controlled Stigmem nodes and least-privilege agent keys until the
channel-separated OpenClaw integration lands in
[issue #357](https://github.com/Eidetic-Labs/stigmem/issues/357). See
[LIMITATIONS.md §9](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md#9-running-the-openclaw-bundled-adapter-as-is).

:::

## Installation

### ClawHub (alpha evaluation)

```bash
skill install stigmem-node
```

OpenClaw reads the skill's env-var manifest and prompts for `STIGMEM_URL` on first
use. `adapter.py` is bundled in the skill directory — no separate package install
is needed beyond `stigmem-py` (declared in the install spec).

### pip

For direct package installs outside ClawHub:

```bash
uv add "stigmem-py>=0.9.0a1,<1.0.0"
# or
pip install --pre "stigmem-py>=0.9.0a1,<1.0.0"
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STIGMEM_URL` | Yes | Base URL of your Stigmem node (e.g. `https://stigmem.example.com`). |
| `STIGMEM_API_KEY` | Yes | Least-privilege API key for the node. `OpenClawStigmemAdapter.from_env()` fails closed when this is missing. |
| `STIGMEM_SOURCE_ENTITY` | No | Entity URI identifying this agent in the fact graph. Default: `agent:openclaw`. |
| `STIGMEM_OPENCLAW_ALLOWED_HANDOFF_TARGETS` | No | Comma-separated `agent:` entity URI allowlist for handoff and escalation targets. The source entity is always allowed. |

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

`boot()` raises `OpenClawBootError` when the node is unreachable or returns an
error. Treat that as a failed boot, not as a healthy empty context. A successful
query with no matching facts still returns an empty `BootContext`.

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
    goal="Approve increased Stripe webhook rate limit for the pre-reset design work load.",
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
    idempotency_key="session-2026-05-02-abc",
)
```

`fact_refs` are persisted as `ref`-typed fact values so the receiving agent can
fetch them directly. Use `idempotency_key` for retries; a complete previous write
is a no-op, while a partial previous write raises an explicit error.

## Security

**Source binding** — `STIGMEM_SOURCE_ENTITY` is bound at construction time and
cannot be overridden per call, so facts are always attributed to the declared agent
identity. Use a per-deployment entity URI, not a shared or generic identifier.

**Untrusted retrieved context** — `boot()` applies presentation-layer escaping
before injecting fact values into the system prompt, but that is not a security
boundary and does not close C1/H5. Treat the summary and raw facts as untrusted
input. Use a private, access-controlled node for evaluation and avoid high-stakes
workflows until OpenClaw consumes channel-separated recall output
([#357](https://github.com/Eidetic-Labs/stigmem/issues/357)).

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

`:latest` is fine for trying things out; for production swap to a pinned
version tag or a digest pin — see the [tag-selection guide](../../operators/deployment/install#image-tags).
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
