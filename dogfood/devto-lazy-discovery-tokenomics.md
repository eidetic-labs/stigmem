---
title: Stop Preloading Everything: How We Cut AI Agent Context by 87% with Lazy Discovery
published: true
description: We ran a 14-heartbeat shadow audit on our production CEO agent and proved lazy instruction discovery cuts context token use by 87% with zero regressions. Here's the architecture, the data, and the keyword-design lesson we didn't expect.
tags: ai, agents, llm, architecture
---

The problem with eager instruction loading is that your agent burns the same context tokens every heartbeat regardless of what it's actually doing. Here's how we fixed it — and what we learned about keyword design along the way.

---

## The problem we were solving

If you run a long-lived AI agent — the kind that operates in a loop, waking up on events, executing tasks, then sleeping — you're probably loading the same instruction files into context every single time. AGENTS.md, HEARTBEAT.md, SOUL.md, TOOLS.md: it all goes in whether the agent is doing a routine heartbeat check or executing a deep engineering task.

For our CEO agent (running on Claude Code via the Paperclip orchestration platform), that eager preload cost **3,190 tokens per heartbeat**. Every heartbeat. Whether the agent was reviewing a PR, delegating a task, or just confirming there was nothing to do.

That's not a context problem today. But multiply it across agents, across roles, across multiple heartbeats per hour — and you're paying for a lot of tokens that don't contribute to the task.

The eager approach also has a subtler cost: it crowds out working context. The more instruction boilerplate in the window, the less room for the actual task data that matters.

---

## The architecture: manifest + recall

The solution we built into [stigmem](https://docs.stigmem.dev) is lazy instruction discovery. Instead of loading all instructions at boot, the agent loads a small **boot stub** (~391 tokens) that describes the manifest, then calls `recall_instruction` at the start of each heartbeat to fetch only the chunks it actually needs.

Here's how it works:

```
boot stub (~391t)
    ↓
recall_instruction(intent="do the work", max_chunks=4)
    ↓
manifest keyword match → top 4 chunks scored + returned
    ↓
agent loads ~415t of targeted instructions
```

**Three components:**

**1. Instruction chunks.** Your markdown instruction files are parsed into atomic units, one per H1/H2/H3 heading. Each unit gets a URI, a token estimate, and a list of `load_triggers` — the keywords and phrases that should cause this chunk to be recalled.

**2. The manifest.** A lightweight JSON index of all chunks with their load triggers. Our CEO agent has 23 chunks totaling ~3,172 tokens, but the agent doesn't load the whole thing — it just knows it exists and calls `recall_instruction` to retrieve what it needs.

**3. `recall_instruction`.** An MCP tool that takes an intent string, matches it against manifest keywords, and returns the top-N scoring chunks. This is the only call the agent makes at each heartbeat.

The migration CLI converts existing instruction files automatically:

```bash
stigmem instruction migrate ./instructions/ \
  --role cto \
  --agent-id $AGENT_ID \
  --dry-run   # preview first, no writes
```

---

## The shadow audit: 14 heartbeats of real data

We didn't flip our production agent on faith. We ran a 14-heartbeat shadow audit: the CEO agent ran with both eager loading AND lazy discovery in parallel, logging what each would have loaded. No behavior change — pure measurement.

**Pass criteria:**
- **Coverage ≥ 95%:** lazy candidates must include ≥ 95% of the chunks the agent's output actually referenced
- **Token budget < 25%:** lazy candidate set < 25% of the eager baseline (< 798t of the 3,190t baseline)
- **Zero regressions:** no heartbeat where the agent missed information that eager loading would have provided

Here's the complete audit log:

| HB | Intent class | max_chunks | Lazy tokens | Token % | Coverage | Regressions |
|----|-------------|-----------|-------------|---------|----------|-------------|
| 1 | Setup/migration | 3 | 769t | 24.1% | 60% | 0 |
| 2 | Task-execution | 3 | 383t | 12.0% | 67% | 0 |
| 3 | Audit-review | 3 | 548t | 17.2% | 67% | 0 |
| **4** | Progress-review | **4** | **415t** | **13.0%** | **100%** | 0 |
| 5 | Task-execution | 4 | 415t | 13.0% | 100% | 0 |
| 6 | Delegation | 4 | 415t | 13.0% | 100% | 0 |
| 7 | Task-execution | 4 | 415t | 13.0% | 100% | 0 |
| 8–14 | Mixed | 4 | 415t | 13.0% | 100% | 0 |

**Final result:** 415t median, 13.0% of eager baseline, 100% coverage across the final 11 heartbeats, 0 regressions across all 14.

All three pass criteria: **met**.

---

## The unexpected lesson: keyword design is the tuning lever

HB1–3 consistently hit 60–67% coverage. Token budget was fine. Zero regressions. But coverage was stuck below target.

The root cause: a single chunk, `HEARTBEAT-9-exit` (32 tokens — tiny, but critical for the wrap-up phase of every heartbeat).

This chunk's `load_triggers` were: `exit`, `comment`, `before`, `exiting`, `assignments`, `valid`, `mention`.

These keywords describe the chunk's *content*. They don't describe the *intents* that would cause an agent to need it. When the agent's heartbeat intent was "wrap up this task and post a comment," none of those keywords matched closely enough to surface the chunk at recall@3.

**Fix 1:** We added 7 natural-language synonyms to `load_triggers`:

```
wrap, done, complete, finish, final, closing, conclude
```

HB4: first fully green heartbeat. 100% coverage.

**Fix 2:** Even with the keyword fix, recall@3 was exactly consumed by the two primary workflow chunks plus the exit chunk, leaving no budget for the assignments chunk when both were needed simultaneously. We bumped `max_chunks` from 3 to 4. Token cost: 415t vs. 383t — a 32-token delta (< 1% of eager baseline) for fully reliable coverage.

**The lesson:**

> Manifest keyword design is as important as the recall algorithm. Load triggers should describe the *intents and situations* that require a chunk, not the content of the chunk itself.
>
> Completion-phase chunks, safety constraints, and exit procedures are systematically under-served by keyword lists derived from content. Add the natural-language synonyms your agents actually use when they need this information.

This is the finding we're encoding directly into the migration tool: when generating `load_triggers`, it now flags "wrap-up" and "constraint" style sections and suggests completion-phase synonyms automatically.

---

## Results

| Metric | Before (eager) | After (lazy) | Change |
|--------|---------------|--------------|--------|
| Per-heartbeat tokens | 3,190t | 415t | **−87%** |
| Boot stub size | 3,190t | 391t | — |
| Manifest size | — | 3,172t (23 chunks) | indexed, not loaded |
| Coverage (eval HBs 4–14) | 100% (by definition) | 100% | = |
| p95 token load | 3,190t | 415t | −87% |
| Regressions | — | 0 | = |

---

## Running this in production: the dogfood story

This isn't a synthetic benchmark. The CEO agent in question manages task delegation, reviews PRs, coordinates cross-agent work, and runs company governance on the Paperclip platform — in production, today. The shadow audit ran across real heartbeats, real tasks, real agent outputs.

The coverage numbers are from actual references in agent outputs. The regressions count (zero) is from real task execution. We flipped the boot stub only after 14 heartbeats confirmed all criteria.

Running it on yourself first is the only honest way to validate it actually works.

---

## Try it yourself

Stigmem is open source. The instruction migration tooling ships with the `stigmem-node` package:

```bash
pip install stigmem-node

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
curl -X POST http://localhost:8000/v1/agents/$AGENT_ID/recall-instruction \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -d '{"intent": "wrap up this task", "max_chunks": 4}'

# 4. Run your own shadow audit before flipping
```

The migration tool handles idempotency (NOOP on unchanged chunks), tombstoning (removed sections cleaned from manifest, facts preserved in DB for audit history), and CI integration via `--yes` flag.

Full spec: §21 of the stigmem protocol spec, at [docs.stigmem.dev](https://docs.stigmem.dev).

---

## What's next: the CTO rollout confirms the pattern

The CTO agent completed the same 14-heartbeat shadow audit and is now running `migration_mode=lazy, stub_version=2`. Eager baseline: 1,129t — a small instruction set (< 1,500t), so the right calibration target is 50%, not 25%.

One new finding relative to the CEO audit: the CTO's token load is **bimodal**.

| Intent class | Lazy tokens | % baseline | Driver |
|---|---|---|---|
| Bug-fix, CI/CD, refactor | 457t | 40.5% | `work-standards` dominant (4 keyword hits) |
| Architecture, data-model, spec | 565t | 50.0% | `what-you-own` + `technical-lenses` both fire |

Both modes pass the 50% ceiling. The bimodal shape is structural: engineering tasks with clear action verbs (`code`, `commit`, `test`) pull `work-standards` hard; design tasks with structural vocabulary (`architecture`, `framework`, `technical`) pull two scope chunks simultaneously. Neither mode crowds out critical chunks.

The CTO audit also reproduced the keyword-design gap, but for `work-standards` instead of the exit chunk: on a pure code-review intent, `work-standards` had **zero keyword hits** and was missed (HB3 pre-fix, 1 regression). Fix: add `["review", "code", "implement", "test", "bug", "fix"]` to `work-standards.load_triggers.keywords`. Post-fix: 11 consecutive heartbeats at 100% coverage, 0 regressions.

The pattern holds across both production rollouts: write load-trigger keywords in the natural language of the *intents that need a chunk*, not the vocabulary of the chunk itself.

The open question is multi-intent heartbeats — when an agent handles two concurrent task threads requiring different instruction sets. The current single `intent` string works well for single-task heartbeats; we're exploring composite intent scoring for agents that parallelize across work trees.

If you're building or operating long-lived AI agents and running into context budget issues, lazy instruction discovery is worth a look. The implementation is straightforward, the migration tooling handles the mechanical parts, and the tuning lever — keyword design — is well within reach of anyone who authored the instructions in the first place.

---

*Stigmem is an open protocol for federated AI agent memory, built for production agent systems. Docs and source at [docs.stigmem.dev](https://docs.stigmem.dev).*
