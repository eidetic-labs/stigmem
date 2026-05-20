---
title: OpenClaw
sidebar_label: OpenClaw
audience: Integrator
---

# Stigmem in OpenClaw

<p className="stigmem-meta"><span>5 min read</span><span>OpenClaw developer · Node operator</span><span>Alpha connector</span></p>

<div className="stigmem-lead">

**What this guide covers**

Evaluate persistent, federated memory for OpenClaw agents via the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node).
The skill provides four surfaces: a **boot handshake** that injects
prior context into the system prompt, plus write surfaces for
**handoffs**, **decisions**, and **escalations**.

</div>

**Audience:** OpenClaw skill developers and node operators deploying Stigmem as a shared knowledge store across agents.

:::caution Alpha connector

The OpenClaw connector is available in the v0.9.0aN alpha line for evaluation, not as a recommended production integration. The adapter now separates retrieved content from instruction-channel recall output and exports a required system prompt directive, with audit-mapped C1-C4/H1-H5 regression coverage. See [LIMITATIONS.md §9](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md#9-running-the-openclaw-bundled-adapter-as-is).

:::

## Installation

### ClawHub (alpha evaluation)

```bash
skill install stigmem-node
```

OpenClaw reads the skill's env-var manifest and prompts for `STIGMEM_URL` on first use. `adapter.py` is bundled in the skill directory.

### pip

```bash
uv add "stigmem-py>=0.9.0a2,<1.0.0"
# or
pip install --pre "stigmem-py>=0.9.0a2,<1.0.0"
```

## Environment variables

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_URL</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Base URL of your Stigmem node.</dd>
</div>

<div>
<dt><code>STIGMEM_API_KEY</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Least-privilege API key. <code>OpenClawStigmemAdapter.from_env()</code> fails closed when missing.</dd>
</div>

<div>
<dt><code>STIGMEM_SOURCE_ENTITY</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Entity URI identifying this agent. Default: <code>agent:openclaw</code>.</dd>
</div>

<div>
<dt><code>STIGMEM_OPENCLAW_ALLOWED_HANDOFF_TARGETS</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Comma-separated <code>agent:</code> entity URI allowlist for handoff and escalation targets. The source entity is always allowed.</dd>
</div>

</div>

## Usage

```python
from adapter import OpenClawStigmemAdapter, SYSTEM_PROMPT_DIRECTIVE   # ClawHub bundled path
# or: from stigmem_openclaw.adapter import OpenClawStigmemAdapter  # pip install

adapter = OpenClawStigmemAdapter.from_env()
```

### Boot handshake

```python
ctx = adapter.boot(
    user_entity="user:alice",
    project_entities=["project:my-roadmap"],
)
system_prompt = base_prompt + (
    "\n\n" + SYSTEM_PROMPT_DIRECTIVE + "\n\n" + ctx.summary if ctx else ""
)
```

<div className="stigmem-keypoint">

**`boot()` raises `OpenClawBootError` when the node is unreachable.**

Treat that as a failed boot, not as a healthy empty context. A
successful query with no matching facts still returns an empty
`BootContext`.

</div>

### Emit a decision

```python
adapter.emit_decision(
    entity="decision:auth-provider",
    summary="Chose Clerk over Auth0: simpler Next.js integration, lower per-seat cost.",
)
```

Decisions are append-only; dedupe externally before calling if your workflow needs at-most-once semantics.

### Emit an escalation

```python
adapter.emit_escalation(
    to_entity="agent:cto",
    goal="Approve increased Stripe webhook rate limit for the pre-reset design work load.",
    priority="high",
)
```

`priority` accepts `"low"`, `"medium"`, `"high"`, or `"critical"`. Escalations carry a 24-hour expiry.

### Emit a handoff

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

`fact_refs` are persisted as `ref`-typed fact values. If you pass a non-empty `fact_refs` list and none validate, the adapter raises before writing a provenance-free handoff. Use `idempotency_key` for retries.

## Security

<div className="stigmem-fields">

<div>
<dt>Property</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Source binding</dt>
<dt><span className="stigmem-fields__type">construction-time</span></dt>
<dd><code>STIGMEM_SOURCE_ENTITY</code> cannot be overridden per call. Use a per-deployment entity URI.</dd>
</div>

<div>
<dt>Untrusted retrieved context</dt>
<dt><span className="stigmem-fields__type">channel-separated</span></dt>
<dd><code>boot()</code> wraps retrieved facts in <code>UNTRUSTED STIGMEM CONTENT</code> delimiters. Put <code>SYSTEM_PROMPT_DIRECTIVE</code> above <code>ctx.summary</code> so the model treats retrieved memory as data.</dd>
</div>

<div>
<dt>API key scope</dt>
<dt><span className="stigmem-fields__type">least privilege</span></dt>
<dd>Scope to the nodes this agent reads/writes. Do not share across unrelated deployments. Rotate regularly.</dd>
</div>

<div>
<dt>Fact persistence</dt>
<dt><span className="stigmem-fields__type">across sessions</span></dt>
<dd>Facts persist across sessions and agents. Retract stale facts explicitly rather than relying on expiry.</dd>
</div>

</div>

## Running your own Stigmem node

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_NODE_URL=http://localhost:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

`:latest` is fine for trying things out; for production swap to a pinned version tag or a digest pin — see the [tag-selection guide](../../operators/deployment/install#image-tags).

## Smoke test

```python
from adapter import OpenClawStigmemAdapter

adapter = OpenClawStigmemAdapter.from_env()
ctx = adapter.boot(user_entity="user:test", project_entities=[])
print("boot ok:", ctx.summary[:80] if ctx else "(no prior context)")
```

## See also

<div className="stigmem-grid">

<div><h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/adapters/openclaw#readme">adapters/openclaw README</a></h4><p>Package source, changelog, full security model.</p></div>
<div><h4><a href="../../concepts/federation/">Federation guide</a></h4><p>External node onboarding and multi-node topology.</p></div>
<div><h4><a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/adapter-paperclip">Paperclip / Claude Code</a></h4><p>MCP-based integration.</p></div>
<div><h4><a href="../../security/authentication">Authentication</a></h4><p>API key setup and OIDC options.</p></div>

</div>
