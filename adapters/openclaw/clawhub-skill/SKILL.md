---
name: stigmem-node
title: Stigmem
description: Persistent federated memory for OpenClaw agents — boot handshake, handoff, decision, and escalation surfaces backed by a Stigmem node.
version: 1.0.1
metadata:
  openclaw:
    emoji: "🧠"
    homepage: https://stigmem.dev/docs/guides/federation#external-onboarding
    clawhub: https://clawhub.ai/skills/stigmem-node
    primaryEnv: STIGMEM_URL
    requires:
      env:
        - STIGMEM_URL
    envVars:
      - name: STIGMEM_URL
        required: true
        description: "Base URL of your Stigmem node (e.g. https://stigmem.example.com)."
      - name: STIGMEM_API_KEY
        required: false
        description: "API key for the Stigmem node. Omit if the node runs with auth disabled. Use a least-privilege key scoped to the intended node only; rotate regularly."
      - name: STIGMEM_SOURCE_ENTITY
        required: false
        description: "Entity URI that identifies this agent in the fact graph (default: agent:openclaw)."
    install:
      - kind: uv
        package: "stigmem-py>=1.0.0,<2.0.0"
---

# Stigmem

Gives your OpenClaw agent persistent, federated memory via [Stigmem](https://stigmem.dev) — an open-source knowledge fabric that stores facts as immutable, signed assertions and replicates them across nodes.

## What this skill provides

- **Boot handshake** — on agent start, pull user preferences, project constraints, and pending handoffs from the Stigmem node and inject them into your system prompt.
- **Handoff** — when a session ends or delegates, record a typed handoff cluster so the next agent or channel resumes with full context.
- **Decision** — emit durable `roadmap:decision` facts for significant architectural choices; built-in dedup guard prevents repeated writes.
- **Escalation** — write `intent:escalation` facts with priority and a 24-hour expiry so stale escalations don't accumulate.

## Setup

1. Set `STIGMEM_URL` to your Stigmem node URL.
2. Optionally set `STIGMEM_API_KEY` (required if the node has auth enabled).
3. Optionally set `STIGMEM_SOURCE_ENTITY` to the entity URI that represents this agent instance (default: `agent:openclaw`).

## Usage

`adapter.py` is bundled with this skill. Import it directly from the skill directory — no separate package install needed beyond `stigmem-py` (declared in the install spec above).

```python
from adapter import OpenClawStigmemAdapter

adapter = OpenClawStigmemAdapter.from_env()

# At session start — inject ctx.summary into the system prompt
ctx = adapter.boot(
    user_entity="user:alice",
    project_entities=["project:my-roadmap"],
)
system_prompt = base_prompt + ("\n\n" + ctx.summary if ctx else "")

# Record a significant decision
adapter.emit_decision(
    entity="decision:auth-provider",
    summary="Chose Clerk over Auth0: simpler Next.js integration, lower per-seat cost.",
)

# Escalate to another agent
adapter.emit_escalation(
    to_entity="agent:cto",
    goal="Approve increased Stripe webhook rate limit for Phase 2 load.",
    priority="high",
)

# Emit a handoff when the session ends
adapter.emit_handoff(
    from_entity="agent:openclaw",
    to_entity="agent:assistant",
    summary="Auth provider chosen; Stripe limit escalation pending.",
    fact_refs=["fact-auth-decision", "fact-esc-stripe"],
    continuation="Resume from the Stripe rate-limit discussion.",
)
```

## Security notes

**Memory isolation** — Facts written via this skill persist across sessions and agents. An incorrect decision, handoff, or escalation propagates to future agent runs. Use separate Stigmem nodes (or separate scope namespaces) for experimental and production workloads. Retract stale facts explicitly rather than relying on expiry.

**Retrieved facts are untrusted** — `boot()` returns facts from an external node. The adapter sanitizes values before formatting them into a summary, but you should still review the injected context before acting on it in high-stakes workflows.

**API key scope** — Set `STIGMEM_API_KEY` to a key scoped only to the nodes this agent needs to read from and write to. Rotate keys regularly. Never share a key across multiple unrelated agent deployments.

## Running your own Stigmem node

Stigmem nodes are self-hosted. The quickest way to spin one up:

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_NODE_URL=http://localhost:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

Full setup guide and federation docs: [stigmem.dev/docs/guides/federation](https://stigmem.dev/docs/guides/federation#external-onboarding)

## Federation

Stigmem nodes can federate with each other to share public-scoped facts across organizations. To connect your node to a partner network, see the [external integrator onboarding guide](https://stigmem.dev/docs/guides/federation#external-onboarding).

## Source

[github.com/Eidetic-Labs/stigmem](https://github.com/Eidetic-Labs/stigmem) — Apache-2.0
