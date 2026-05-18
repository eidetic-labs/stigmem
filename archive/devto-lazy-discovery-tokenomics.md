---
title: Stop Preloading Everything: How We Cut AI Agent Context by 50–87% with Lazy Discovery
published: true
description: We ran 28 heartbeats of shadow audits across two production agents and proved lazy instruction discovery cuts context token use by 50–87% with zero regressions. Here's the architecture, both data sets, and the keyword-design lesson we keep learning.
tags: ai, agents, llm, architecture
---

This is the second post in our stigmem production series. If you are new to stigmem, the [first post covers the foundation](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8): what stigmem is, the federated fact model `(entity, relation, value, source, timestamp, confidence, scope)`, how two nodes federate via Ed25519-signed peer handshakes, and MCP integration. This post assumes that foundation and focuses on what we built on top of it.

**TL;DR:** We shadow-audited lazy instruction discovery across two production AI agents and cut per-heartbeat context token use by 50-87% with zero regressions, using a manifest + recall architecture built on stigmem. Read on to find out why seven added keywords unlocked 100% coverage, and what that tells you about designing instruction sets for production agents.

The problem with eager instruction loading is that your agent burns the same context tokens every heartbeat regardless of what it's actually doing. Here's how we fixed it across two production agents, what the data showed, and what we learned about keyword design along the way.

---

## The problem we were solving

If you run a long-lived AI agent that operates in a loop, waking up on events, executing tasks, then sleeping, you're probably loading the same instruction files into context every single time. AGENTS.md, HEARTBEAT.md, SOUL.md, TOOLS.md: it all goes in whether the agent is doing a routine check or executing a deep engineering task.

For our CEO agent, that eager preload cost **3,190 tokens per heartbeat**. For our CTO agent, **1,129 tokens per heartbeat**. Both numbers, every heartbeat, regardless of what either agent was actually doing.

That's not a crisis today. But multiply it across agents, across roles, across dozens of heartbeats per hour, and you're paying for a lot of tokens that contribute nothing to the task. There's also a subtler cost: instruction boilerplate crowds out working context, leaving less room for the actual task data that matters.

---

## The architecture: manifest + recall

The solution we built into [stigmem](https://docs.stigmem.dev) is lazy instruction discovery. This builds directly on stigmem's fact store: instruction chunks are stored as typed facts with relation `instruction:content`, and the manifest is a fact that indexes them. The same federation and MCP infrastructure [we described in the v1.0 post](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8) carries these instruction facts across nodes. Instead of loading all instructions at boot, the agent loads a small **boot stub** (under 400 tokens) that describes the manifest, then calls `recall_instruction` at the start of each heartbeat to fetch only the chunks it actually needs.

Here's how it works:

```
boot stub (<400t)
    |
    v
recall_instruction(intent="...", max_chunks=4)
    |
    v
manifest keyword match -> top 4 chunks scored + returned
    |
    v
agent loads only the targeted instructions for this heartbeat
```

**Three components:**

**1. Instruction chunks.** Your markdown instruction files are parsed into atomic units, one per H1/H2/H3 heading. Each unit gets a URI, a token estimate, and a list of `load_triggers`: the keywords and phrases that should cause this chunk to be recalled.

**2. The manifest.** A lightweight JSON index of all chunks with their load triggers. The CEO agent has 23 chunks totaling ~3,172 tokens; the CTO agent has 11 chunks totaling 1,129 tokens. Neither agent loads the whole manifest at runtime. It just knows it exists and calls `recall_instruction` to retrieve what it needs.

**3. `recall_instruction`.** An MCP tool that takes an intent string, matches it against manifest keywords, and returns the top-N scoring chunks. This is the only instruction-loading call the agent makes each heartbeat. It sits alongside the `assert_fact`, `query_facts`, and `synthesize_scope` tools [described in the v1.0 launch post](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8) and uses the same MCP server configuration.

The migration CLI converts existing instruction files automatically:

```bash
stigmem instruction migrate ./instructions/ \
  --role cto \
  --agent-id $AGENT_ID \
  --dry-run   # preview first, no writes
```

---

## The shadow audit: 14 heartbeats each, two agents

We didn't flip either production agent on faith. We ran a 14-heartbeat shadow audit for each: the agent ran with both eager loading and lazy discovery in parallel, logging what each would have loaded. No behavior change, just measurement.

**Pass criteria (CEO):**
- Coverage >= 95%: lazy candidates must include >= 95% of chunks the agent's output actually referenced
- Token budget < 25% of the 3,190t eager baseline (< 798t)
- Zero regressions

**Pass criteria (CTO):**
- Coverage >= 95% on critical chunks
- Token budget <= 50% of the 1,129t eager baseline (<= 565t), calibrated for the smaller instruction set where a 50% cut is still substantial
- Zero regressions post-fix

### CEO audit results (28 total HBs across both runs, but CEO ran first)

| HB | Intent class | max_chunks | Lazy tokens | Token % | Coverage | Regressions |
|----|-------------|-----------|-------------|---------|----------|-------------|
| 1 | Setup/migration | 3 | 769t | 24.1% | 60% | 0 |
| 2 | Task-execution | 3 | 383t | 12.0% | 67% | 0 |
| 3 | Audit-review | 3 | 548t | 17.2% | 67% | 0 |
| **4** | Progress-review | **4** | **415t** | **13.0%** | **100%** | 0 |
| 5 | Task-execution | 4 | 415t | 13.0% | 100% | 0 |
| 6-14 | Mixed | 4 | 415t | 13.0% | 100% | 0 |

**CEO final result:** 415t median, 13.0% of eager baseline, 100% coverage across HBs 4-14, 0 regressions.

### CTO audit results

| HB | Intent type | Lazy tokens | Budget % | Critical coverage |
|----|-------------|-------------|----------|------------------|
| 1 | Setup/migration | 310t | 27.5% | 100% (sim) |
| 2 | Task-execution | 525t | 46.5% | 100% |
| 3 | Code review | 565t | 50.0% | 100% (post-fix) |
| 4 | Bug fix/incident | 457t | 40.5% | 100% |
| 5 | Architecture decision | 565t | 50.0% | 100% |
| 6 | CI/CD pipeline | 457t | 40.5% | 100% |
| 7 | Security audit | 457t | 40.5% | 100% |
| 8 | Data model | 565t | 50.0% | 100% |
| 9 | Performance | 565t | 50.0% | 100% |
| 10 | Hiring/team | 493t | 43.7% | 100% |
| 11 | Spec/planning | 565t | 50.0% | 100% |
| 12 | Refactoring | 457t | 40.5% | 100% |
| 13 | Documentation | 565t | 50.0% | 100% |
| 14 | Flip HB | 356t | 31.5% | 100% |

**CTO final result:** 356-565t range (bimodal: typically 457t or 565t), 31.5-50.0% of eager baseline, 100% critical coverage HBs 4-14, 0 regressions post-fix.

---

## The keyword-design lesson: it showed up in both runs

This is the finding we didn't fully anticipate, and seeing it replicate across two independent agents made it undeniable.

**In the CEO run:** The `HEARTBEAT-9-exit` chunk (32 tokens, critical for the wrap-up phase of every heartbeat) missed recall@3 on HB1, HB2, and HB3. A quick naming note: `HEARTBEAT-9-exit` is the chunk's identifier, derived from section 9 of the HEARTBEAT.md instruction file. The "9" refers to that file section, not to shadow audit heartbeat number 9. The miss was present from the start; we diagnosed and fixed the root cause during HB3, which is why you will see HB3 referenced as the fix point in the audit log. Its keywords were `exit`, `comment`, `before`, `exiting`, `assignments`, `valid`, `mention`: all content descriptors that describe what the chunk covers, not the intents that require it. None of them matched the agent's actual wrap-up phrasing like "wrap up this task" or "post a comment and finish."

Fix applied in HB3: added 7 natural-language synonyms: `wrap, done, complete, finish, final, closing, conclude`. Coverage jumped to 100% at HB4. We also bumped `max_chunks` from 3 to 4 to handle simultaneous chunk needs, adding only 32 tokens (under 1% of eager baseline).

**In the CTO run (HB3):** The `work-standards` chunk (162 tokens, critical for any engineering task) had zero hits on code-review intents. Its keywords covered commit, bug, done, task. A pure code-review intent produced no matches.

Fix: added `review, code, implement, test, bug, fix` to load triggers. Critical coverage went to 100% at HB4.

Same root cause both times. Same fix pattern both times. Different chunks, different agents, same design error.

**The lesson:**

> Load triggers should describe the *intents and situations* that require a chunk, not the content of the chunk itself.
>
> Completion-phase chunks, safety constraints, and task-execution standards are all systematically under-served by keyword lists derived from their content. The fix is to add the natural-language verbs and phrases your agents actually use when they need this information.

We're encoding this directly into the migration tool. When generating `load_triggers`, it now flags "wrap-up" and "constraint" style sections and suggests completion-phase synonyms as part of the preview output.

The CEO run also let the CTO team apply lessons from day one: CTO started with `max_chunks=4` and exit keywords pre-tuned, which is why the CTO HB1 critical coverage was already 100% on the simulated task-execution intent. Replication made the pattern learnable and transferable.

---

## Results compared

| Metric | CEO (before) | CEO (after) | CTO (before) | CTO (after) |
|--------|-------------|-------------|-------------|-------------|
| Eager load per HB | 3,190t | 415t | 1,129t | 356-565t |
| Reduction | | **87%** | | **50-69%** |
| Token profile | fixed | flat (13%) | fixed | bimodal (40-50%) |
| Coverage (eval phase) | 100% by definition | 100% | 100% by definition | 100% |
| Regressions post-fix | n/a | 0 | n/a | 0 |
| Consecutive green HBs | n/a | 11 (HB4-14) | n/a | 11 (HB4-14) |

The bimodal profile in the CTO run (457t or 565t) is structural: the top-4 recall slots either pull architecture and technical chunks (565t ceiling) or fill with soul and heartbeat (457t floor). Both pass the budget criterion, and neither is a problem.

---

## Running this in production: the dogfood story

These are not benchmarks run against synthetic workloads. Both agents operate in production: the CEO agent manages task delegation, board-level review, and company governance; the CTO agent handles architecture decisions, code review, CI/CD, and engineering hiring. The shadow audits ran across real heartbeats, real tasks, real agent outputs.

Coverage numbers reflect actual references in agent outputs. Regression counts reflect real task execution. Neither agent was flipped until 14 heartbeats confirmed all criteria. The CEO flip informed the CTO setup, which is why the CTO run started in a better position.

Running it on yourself first is the only honest way to know it works.

---

## Try it yourself

Stigmem is open source. The instruction migration CLI ships as part of the reference node. Clone the repo and install from source:

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem

# install the node package (includes the stigmem CLI)
pip install -e node/
# or, if you use uv:
# uv sync
```

Then start a local node and run the migration:

```bash
# start the node (Docker is the easiest path)
docker compose up --build -d

# 1. Preview your instruction set as lazy-loadable chunks
stigmem instruction migrate ./instructions/ \
  --role myagent \
  --agent-id $YOUR_AGENT_ID \
  --dry-run

# 2. Run the migration
stigmem instruction migrate ./instructions/ \
  --role myagent \
  --agent-id $YOUR_AGENT_ID

# 3. Verify recall works for your agent's typical intents
curl -X POST http://localhost:8765/v1/agents/$AGENT_ID/recall-instruction \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -d '{"intent": "wrap up this task", "max_chunks": 4}'

# 4. Run your own shadow audit before flipping
```

The migration tool handles idempotency (NOOP on unchanged chunks), tombstoning (removed sections cleaned from the manifest, underlying facts preserved in DB for audit history), and CI integration via the `--yes` flag.

Full spec: Section 21 of the stigmem protocol spec, at [docs.stigmem.dev](https://docs.stigmem.dev).

---

## What's next: stigmem v2.0 and how you can help

Phase 10 proved that lazy instruction discovery works in production. The [v1.0 launch](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8) established the federated fact substrate: immutable typed facts, HLC timestamps, Ed25519-signed peer replication, and MCP tooling. Lazy discovery is the first major capability we've built on top of that substrate in a production setting. But getting stigmem to a point where any team can run it securely and robustly at scale is larger than what we can finish alone.

Here's what v2.0 needs to solve, and where we're looking for collaborators:

**Multi-organization trust and federation.** The v1.0 federation model [covers two-node peering](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8) with scope-gated replication. Scaling that to organizations that don't already trust each other requires preventing memory poisoning and containing malicious agent behavior. We have design sketches but not a finished protocol.

**Persistent memory across reboots.** The current local SQLite store disappears when the host system reboots. We're evaluating Turso and other durable SQLite-compatible backends for persistence without sacrificing the local-first deployment model.

**Graph-based memory relationships.** Agents should be able to navigate related memories, not just retrieve isolated facts. We want agents to touch a memory and discover connected context through graph traversal rather than pulling the full memory table on every query.

**Composite intent for parallel workloads.** The single `intent` string works well when an agent handles one task per heartbeat. Multi-threaded agents need a way to express composite intent so recall surfaces instruction chunks for all concurrent task threads.

If any of these problems are interesting to you, we want to hear from you. The project is at [docs.stigmem.dev](https://docs.stigmem.dev) and the source is on GitHub. v2.0 is being designed collaboratively, and early contributors will have real influence over the architecture.

---

## What we learned, summarized

1. Eager instruction loading is a hidden tax. Most teams don't notice until they're running many agents or many heartbeats per hour.
2. The manifest and recall architecture is sound. Both audits ran zero regressions post-fix across 11 consecutive heartbeats.
3. Keyword design is the tuning lever, not the recall algorithm. Content-derived keywords systematically miss real usage patterns. Use intent-derived synonyms instead.
4. Lessons transfer across agents. The CEO run directly improved the CTO setup. Multi-agent rollouts get cheaper over time.
5. Shadow auditing before flipping is worth the overhead. It gives you real coverage data and catches manifest gaps before they become production regressions.

---

*Stigmem is an open protocol for federated AI agent memory. Docs and source at [docs.stigmem.dev](https://docs.stigmem.dev). New to stigmem? Start with the [v1.0 launch post](https://dev.to/offbyonce/stigmem-v10-a-federated-knowledge-fabric-for-ai-agents-open-source-lf8).*
