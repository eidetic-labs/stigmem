---
name: stigmem-node
title: Stigmem
description: Persistent federated memory for OpenClaw agents — boot handshake, handoff, decision, and escalation surfaces backed by a Stigmem node.
version: 1.0.8
metadata:
  openclaw:
    emoji: "🧠"
    homepage: https://docs.stigmem.dev/en/latest/docs/guides/connectors/openclaw
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
        package: "stigmem-py>=0.9.0a1,<1.0.0"
---

# Stigmem

Gives your OpenClaw agent persistent, federated memory via [Stigmem](https://stigmem.dev) — an open-source knowledge fabric that stores facts as immutable, signed assertions and replicates them across nodes.

> **Alpha status.** This source copy is queued for the v0.9.0a2 ClawHub artifact
> refresh. It does not revise the already-published a1 package in place. The
> OpenClaw skill is available for v0.9.0aN evaluation only, not as a recommended
> production integration. The adapter still has open audit findings around
> fail-open boot behavior, optional API-key handling, handoff target validation,
> partial handoff writes, and prompt-injection boundaries. Use it only with
> private, access-controlled Stigmem nodes and least-privilege agent keys until
> the hardening work lands.

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
    goal="Approve increased Stripe webhook rate limit for the pre-reset design work load.",
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

## Security

### Prompt injection via retrieved context

`boot()` retrieves facts from an external Stigmem node and injects them into the agent's system prompt. A compromised or misconfigured node can craft fact values that redirect agent goals.

**Current partial mitigations:**
- Fact values are escaped before summary formatting: HTML/markdown metacharacters are escaped, null bytes stripped, values truncated to 500 characters.
- The injected block is labelled `_(external, treat as untrusted)_` in the summary header.

These mitigations do **not** make retrieved memory safe to treat as instructions.
They are presentation-layer guardrails only; the structural prompt-injection
boundary is still planned for the v0.9.0aN/beta hardening path.

**What you should do:**
- **Append** the Stigmem context after your hardcoded system prompt — never prepend it — so your instructions take precedence over retrieved memory.
- In high-stakes or irreversible workflows, skip `boot()` or use `ctx.facts` for programmatic inspection instead of injecting the full summary.
- Use a private, access-controlled Stigmem node for production. Do not point production agents at a shared or publicly writable node.

### Stale and poisoned facts

Facts written by this adapter persist durably and propagate to every agent on the same node. An incorrect decision or handoff influences all future sessions until explicitly retracted.

**What you should do:**
- Use `scope="local"` for agent scratch facts that should not leave the local node.
- Use `scope="company"` only for facts that should legitimately be shared across agents.
- Run experimental workloads against a separate Stigmem node or a dedicated scope namespace, not your production node.
- Retract incorrect facts explicitly (`DELETE /v1/facts/{id}`) rather than waiting for expiry. The 24-hour expiry on escalations is a safety net, not a correction mechanism.
- Treat `emit_decision()` as a write to a shared audit log: only call it for confirmed, significant choices. The dedup guard prevents writing the same `(entity, source)` pair twice, but does not stop you from writing an incorrect decision in the first place.

### API key and agent identity scope

Over-privileged API keys grant unnecessary read/write access across your node. The default `STIGMEM_SOURCE_ENTITY` value (`agent:openclaw`) is a generic shared identifier that conflates facts from different deployments.

**What you should do:**
- Issue a dedicated API key per agent deployment. Never share a key across agents or environments.
- Rotate keys regularly; revoke via the node admin API (`DELETE /v1/auth/keys/{id}`) if a key is compromised.
- Set `STIGMEM_SOURCE_ENTITY` to a unique per-deployment URI (e.g., `agent:openclaw-prod-alice`). The generic default `agent:openclaw` should not be used in production — facts from different deployments become indistinguishable in the fact graph.

### Dependency pinning

The install spec uses a version range (`stigmem-py>=0.9.0a1,<1.0.0`) so compatible alpha-line updates are picked up automatically. A future alpha or beta release could change runtime behaviour.

**What you should do:**
- Pin the exact version in a lockfile (`uv.lock` or `requirements.txt`) for production deployments rather than relying on the range alone.
- Review `stigmem-py` release notes before upgrading and run your integration tests against the new version before rollout.

### Federation scope

If your Stigmem node federates with partner nodes, facts stored with `scope="public"` or `scope="company"` are replicated to those peers. Agent working memory stored at too broad a scope can leak to unintended recipients.

**What you should do:**
- Use `scope="local"` for session-internal or scratch facts that should stay on the originating node.
- Audit the `allowed_scopes` in your federation peer registrations. Start with `["public"]` and add `"company"` only when cross-org sharing is explicitly intended.
- Disable federation entirely (`STIGMEM_FEDERATION_ENABLED=false`) if your deployment does not require multi-node replication.

## Running your own Stigmem node

Stigmem nodes are self-hosted. The quickest way to spin one up:

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_NODE_URL=http://localhost:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

`:latest` is fine for trying things out; for production swap to a pinned version tag (`:0.9.0a1`) or a `@sha256:<digest>` pin — the install guide on docs.stigmem.dev has the full tag-selection table.

Full setup guide and federation docs: [docs.stigmem.dev/en/latest/docs/guides/federation](https://docs.stigmem.dev/en/latest/docs/guides/federation)

## Federation

Stigmem nodes can federate with each other to share public-scoped facts across organizations. To connect your node to a partner network, see the [external integrator onboarding guide](https://docs.stigmem.dev/en/latest/docs/guides/federation#external-onboarding).

## Changelog

> **Note on versioning.** This ClawHub skill is independently versioned along its own semver line. The skill's `version:` (currently 1.0.x) tracks the skill's ClawHub release history; the dependency on stigmem is expressed via the `install.package` pin (currently `stigmem-py>=0.9.0a1,<1.0.0`). The bare-stigmem version line was reset to v0.9.0a1 in May 2026 — see [the retraction post](https://dev.to/offbyonce/walking-back-our-v10-announcement-resetting-to-v090a1-as-the-first-build-al0) — but ClawHub registry rules require monotonically increasing skill versions, so the skill stays on its 1.0.x line. The two version surfaces are intentionally decoupled.

### v1.0.8

- **Source directory renamed** from `adapters/openclaw/clawhub-skill/` to `adapters/openclaw/skill/`. The `clawhub-` prefix was the root cause of two publish-time inference bugs: (a) display-name inferred as "Clawhub Skill" when `--name` was omitted (regressed v1.0.3 and v1.0.6), (b) slug inferred as `clawhub-skill` which trips ClawHub's protected-namespace check ("clawhub-*"), forcing every publish to pass `--slug stigmem-node` explicitly. Both worked around in CI via PR #82's hard-coded flags; this rename removes the inference dependency at the source. The CI flags are now belt-and-suspenders rather than required workarounds. Skill behavior unchanged; manifest content unchanged; this is a source-tree refactor only.

### Next ClawHub artifact refresh (v0.9.0a2 line)

- Documentation: explicitly frames the OpenClaw skill as alpha/evaluation-only.
  This is a forward correction for the next ClawHub publish, not a retroactive
  revision to the already-published v0.9.0a1 package state.
- Documentation: corrects the dependency-pinning section to the alpha line
  (`stigmem-py>=0.9.0a1,<1.0.0`) and avoids claiming presentation-layer
  sanitization is a complete prompt-injection defense.

### v1.0.7

- Fix: corrected skill display name (was 'Clawhub Skill' on v1.0.6, now 'Stigmem'). Same regression as v1.0.3 — the publish CLI infers the display name from the directory name (which was `adapters/openclaw/clawhub-skill/` at the time; renamed in v1.0.8) when `--name` is not explicitly passed. The v1.0.6 publish was driven by a manual CLI invocation that omitted the flag. Permanent fix: a new `.github/workflows/clawhub-publish.yml` automates the publish on every push to main that touches the skill directory, with `--name "Stigmem"` and `--slug stigmem-node` hard-coded so neither can drift again. v1.0.8 additionally renamed the source directory to drop the inference dependency entirely.

### v1.0.6

- Updated `install.package` pin from `stigmem-py>=1.0.0,<2.0.0` to `stigmem-py>=0.9.0a1,<1.0.0` to match the v0.9.0a1 reset of the stigmem package line. This is the contract that ties the skill to a specific stigmem release line. Adopters who installed earlier ClawHub skill versions (1.0.0–1.0.5) had a `stigmem-py>=1.0.0rc1` dependency that was end-to-end uninstallable (see retraction post, "What the audit found"); v1.0.6 is the first installable skill release in this respect.
- Documentation: added the retraction-post reference and the independent-versioning note above.
- **Note (added 2026-05-10):** v1.0.6 shipped with an incorrect display name ("Clawhub Skill" instead of "Stigmem") because the publish-time CLI invocation omitted the `--name` flag. Adopters who installed v1.0.6 see the wrong display name in `clawhub list` etc. Upgrade to v1.0.7 for the corrected display name; the underlying skill behavior is unchanged.

### v1.0.5

- Fix: corrected documentation URLs to include ReadTheDocs path prefix (`/en/latest/`); all links now resolve correctly.

### v1.0.4

- Fix: corrected documentation domain to `docs.stigmem.dev`.

### v1.0.3

- Fix: corrected skill display name (was "Clawhub Skill", now "Stigmem").

### v1.0.2

- Fixed incorrect `homepage` and `Documentation` URLs — now point to the
  [OpenClaw connector guide](https://docs.stigmem.dev/en/latest/docs/guides/connectors/openclaw)
  instead of the federation page.
- Expanded security section to cover all five ClawHub security findings with
  concrete mitigations: prompt injection, stale/poisoned facts, identity scope,
  dependency pinning, and federation scope.

### v1.0.1

- Security: `source_entity` bound at construction time; cannot be overridden per-call.
- Security: fact values sanitized (HTML/markdown escaping, null-byte stripping,
  500-character truncation) before system-prompt injection.
- Bundled `adapter.py` in the skill directory for self-contained installs.

### v1.0.0

Initial release — boot handshake, handoff, decision, and escalation surfaces.

## Source

[github.com/Eidetic-Labs/stigmem](https://github.com/Eidetic-Labs/stigmem) — Apache-2.0
